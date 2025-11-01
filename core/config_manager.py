"""Configuration Manager for Claude Code MCP Manager.

Handles loading, saving, and validation of configuration files with:
- Atomic writes with backup
- Transaction-like saves with rollback
- Error handling for corrupted/missing/locked files
- Version migration support
"""

import json
import logging
import shutil
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from models.preferences import Preferences
from models.server import MCPServer
from models.profile import Profile
from utils.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    MCP_SERVER_TEMPLATES,
    CONFIG_VERSION,
    ERROR_MESSAGES,
    BACKUP_FILE,
    LOCK_FILE
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration with robust error handling."""

    def __init__(self):
        """Initialize configuration manager with paths."""
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self.backup_file = BACKUP_FILE
        self.lock_file = LOCK_FILE
        self.project_profiles: Dict[str, Dict[str, Profile]] = {}
        self._legacy_cleanup_paths: Set[Path] = set()

        self.config_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ConfigManager initialized: {self.config_file}")

    @staticmethod
    def _normalize_path(path: Optional[str]) -> Optional[str]:
        """Normalize filesystem paths for consistent storage."""
        if not path:
            return None
        try:
            return str(Path(path).resolve())
        except Exception:
            try:
                return str(Path(path))
            except Exception:
                return None

    def normalize_project_path(self, path: Optional[str]) -> Optional[str]:
        """Public helper for normalizing project paths."""
        return self._normalize_path(path)

    def _acquire_lock(self, timeout: float = 5.0) -> bool:
        """
        Acquire file lock for safe concurrent access.

        Args:
            timeout: Maximum time to wait for lock in seconds

        Returns:
            True if lock acquired, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if not self.lock_file.exists():
                    self.lock_file.touch()
                    logger.debug("Lock acquired")
                    return True
                time.sleep(0.1)
            except OSError as e:
                logger.warning(f"Error acquiring lock: {e}")
                time.sleep(0.1)

        logger.error("Failed to acquire lock within timeout")
        return False

    def _release_lock(self):
        """Release file lock."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                logger.debug("Lock released")
        except OSError as e:
            logger.warning(f"Error releasing lock: {e}")

    def _create_default_config(self) -> Dict:
        """
        Create default configuration with pre-loaded templates.

        Returns:
            Dictionary containing default configuration
        """
        logger.info("Creating default configuration with pre-loaded templates")

        config = {
            "version": CONFIG_VERSION,
            "preferences": Preferences().to_dict(),
            "servers": {
                server_id: server.to_dict()
                for server_id, server in MCP_SERVER_TEMPLATES.items()
            },
            "profiles": {
                "default": Profile(
                    id="default",
                    name="Default Profile",
                    servers=list(MCP_SERVER_TEMPLATES.keys()),
                    created=datetime.now(),
                    modified=datetime.now(),
                    description="Default profile with all pre-loaded servers"
                ).to_dict()
            },
            "project_profiles": {}
        }

        # Ensure HTTP templates keep type "http"
        for server_id, server_data in config["servers"].items():
            template = MCP_SERVER_TEMPLATES.get(server_id)
            if template:
                server_data["type"] = template.type

        return config

    def load(self) -> Tuple[Preferences, Dict[str, MCPServer], Dict[str, Profile]]:
        """
        Load configuration from file with comprehensive error handling.

        Handles:
        - Missing file: Creates default config with templates
        - Corrupted JSON: Restores from backup
        - Locked file: Retry logic with timeout

        Returns:
            Tuple of (Preferences, servers_dict, profiles_dict)
        """
        if not self._acquire_lock():
            logger.error(ERROR_MESSAGES["CONFIG_LOCKED"])
            raise RuntimeError(ERROR_MESSAGES["CONFIG_LOCKED"])

        try:
            if not self.config_file.exists():
                logger.info(ERROR_MESSAGES["CONFIG_NOT_FOUND"])
                config_data = self._create_default_config()
                self._save_raw(config_data)
                return self._parse_config(config_data)

            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                logger.info("Configuration loaded successfully")

            except json.JSONDecodeError as e:
                logger.error(f"Corrupted config file: {e}")

                if self.backup_file.exists():
                    logger.info("Attempting to restore from backup")
                    try:
                        with open(self.backup_file, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        logger.info(ERROR_MESSAGES["BACKUP_RESTORED"])
                        config_data = self.migrate(config_data)
                        self._save_raw(config_data)

                    except json.JSONDecodeError:
                        logger.error("Backup is also corrupted, creating default")
                        config_data = self._create_default_config()
                        self._save_raw(config_data)
                else:
                    logger.warning("No backup found, creating default")
                    config_data = self._create_default_config()
                    self._save_raw(config_data)

            config_data = self.migrate(config_data)

            return self._parse_config(config_data)

        finally:
            self._release_lock()

    def _parse_config(self, config_data: Dict) -> Tuple[Preferences, Dict[str, MCPServer], Dict[str, Profile]]:
        """
        Parse configuration dictionary into data models.

        Args:
            config_data: Raw configuration dictionary

        Returns:
            Tuple of (Preferences, servers_dict, profiles_dict)
        """
        prefs = Preferences.from_dict(config_data.get("preferences", {}))
        prefs = self._sanitize_preferences(prefs)

        servers: Dict[str, MCPServer] = {}
        raw_servers = config_data.get("servers", {}) or {}
        for server_id, server_data in raw_servers.items():
            try:
                if not isinstance(server_data, dict):
                    raise ValueError("Server entry is not a mapping")

                server_data = dict(server_data)
                server_data.setdefault("id", server_id)
                server_data.setdefault("type", "stdio")

                server = MCPServer.from_dict(server_data)

                explicit_type = server_data.get("type")
                if explicit_type:
                    server.type = explicit_type

                # Auto-correct servers that have URL but were incorrectly marked as stdio
                if server.type == "stdio" and not server.command and server.url:
                    logger.debug(
                        "Correcting server '%s' type to 'http' based on stored URL", server_id
                    )
                    server.type = "http"
                    server.command = None
                    server.args = None

                servers[server_id] = server
            except Exception as e:
                logger.error(f"Failed to parse server {server_id}: {e}")

        profiles: Dict[str, Profile] = {}
        raw_profiles = config_data.get("profiles", {}) or {}
        for profile_id, profile_data in raw_profiles.items():
            try:
                if not isinstance(profile_data, dict):
                    raise ValueError("Profile entry is not a mapping")

                profile = Profile.from_dict(profile_data)
                profile.scope = "global"
                profile.project_path = None
                if profile.servers:
                    profile.servers = [sid for sid in profile.servers if sid in servers]
                profiles[profile_id] = profile
            except Exception as e:
                logger.error(f"Failed to parse profile {profile_id}: {e}")

        promoted_count = 0
        project_profiles_raw = config_data.get("project_profiles", {}) or {}
        for raw_path, project_data in project_profiles_raw.items():
            if not isinstance(project_data, dict):
                logger.warning("Ignoring malformed project profile collection for %s", raw_path)
                continue
            for profile_id, profile_dict in project_data.items():
                try:
                    if not isinstance(profile_dict, dict):
                        raise ValueError("Project profile entry is not a mapping")
                    profile = Profile.from_dict(profile_dict)
                    promoted_id = self._promote_project_profile(
                        profile=profile,
                        servers=servers,
                        profiles=profiles
                    )
                    promoted_count += 1
                    if promoted_id != profile_id:
                        logger.info(
                            "Renamed project profile '%s' to '%s' during migration",
                            profile_id,
                            promoted_id
                        )
                except Exception as exc:
                    logger.error(
                        "Failed to promote project profile %s from '%s': %s",
                        profile_id,
                        raw_path,
                        exc
                    )

        self.project_profiles = {}
        if promoted_count:
            logger.info("Promoted %s project-scoped profiles to global scope", promoted_count)

        # Ensure default templates are present even if missing from config
        restored_templates: List[str] = []
        for template_id, template in MCP_SERVER_TEMPLATES.items():
            if template_id not in servers:
                template_copy = deepcopy(template)
                template_copy.enabled = False
                template_copy.is_template = True
                servers[template_id] = template_copy
                restored_templates.append(template_id)

        if restored_templates:
            logger.info(
                "Restored %s missing template servers: %s",
                len(restored_templates),
                ", ".join(restored_templates)
            )

        return prefs, servers, profiles

    def _sanitize_preferences(self, prefs: Preferences) -> Preferences:
        """Normalize preference paths for consistency."""
        normalized_last = self._normalize_path(prefs.last_path) if prefs.last_path else None
        prefs.last_path = normalized_last or ""

        sanitized_recent: List[str] = []
        seen = set()
        for raw_path in prefs.recent_projects or []:
            normalized = self._normalize_path(raw_path)
            if normalized and normalized not in seen:
                sanitized_recent.append(normalized)
                seen.add(normalized)
        prefs.recent_projects = sanitized_recent

        sanitized_map: Dict[str, str] = {}
        for raw_path, profile_id in (prefs.project_last_profiles or {}).items():
            normalized = self._normalize_path(raw_path)
            if normalized:
                sanitized_map[normalized] = profile_id
        prefs.project_last_profiles = sanitized_map

        return prefs

    def _save_raw(self, config_data: Dict):
        """
        Save raw configuration data to file (internal use).

        Args:
            config_data: Configuration dictionary to save
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, default=str)

    def save(
        self,
        preferences: Preferences,
        servers: Dict[str, MCPServer],
        profiles: Dict[str, Profile],
        project_profiles: Optional[Dict[str, Dict[str, Profile]]] = None
    ):
        """
        Save configuration with atomic write and backup.

        Uses temp file + atomic rename pattern to prevent corruption if interrupted.

        Args:
            preferences: User preferences
            servers: Dictionary of MCP servers
            profiles: Dictionary of profiles
            project_profiles: Optional project-specific profiles
        """
        if not self._acquire_lock():
            raise RuntimeError(ERROR_MESSAGES["CONFIG_LOCKED"])

        try:
            if self.config_file.exists():
                shutil.copy2(self.config_file, self.backup_file)
                logger.debug("Backup created")

            if project_profiles is not None:
                normalized_map: Dict[str, Dict[str, Profile]] = {}
                for raw_path, profile_map in project_profiles.items():
                    normalized_path = self._normalize_path(raw_path)
                    if not normalized_path:
                        continue
                    normalized_map[normalized_path] = deepcopy(profile_map)
                self.project_profiles = normalized_map

            config_data = {
                "version": CONFIG_VERSION,
                "preferences": preferences.to_dict(),
                "servers": {
                    server_id: server.to_dict()
                    for server_id, server in servers.items()
                },
                "profiles": {
                    profile_id: profile.to_dict()
                    for profile_id, profile in profiles.items()
                },
                "project_profiles": self._serialize_project_profiles(self.project_profiles)
            }

            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)

            temp_file.replace(self.config_file)
            logger.info("Configuration saved successfully")
            self._cleanup_legacy_files()

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

        finally:
            self._release_lock()

    def save_with_rollback(
        self,
        preferences: Preferences,
        servers: Dict[str, MCPServer],
        profiles: Dict[str, Profile],
        project_profiles: Optional[Dict[str, Dict[str, Profile]]] = None
    ) -> bool:
        """
        Save configuration with rollback capability.

        If save fails, automatically restores from backup.

        Args:
            preferences: User preferences
            servers: Dictionary of MCP servers
            profiles: Dictionary of profiles

        Returns:
            True if save succeeded, False if rolled back
        """
        # Create snapshot before save
        snapshot = None
        if self.config_file.exists():
            snapshot = self.config_file.read_bytes()

        try:
            self.save(preferences, servers, profiles, project_profiles=project_profiles)
            return True

        except Exception as e:
            logger.error(f"Save failed, rolling back: {e}")

            # Restore snapshot
            if snapshot:
                self.config_file.write_bytes(snapshot)
                logger.info("Configuration rolled back successfully")

            return False

    def load_presets(self) -> Dict[str, MCPServer]:
        """
        Load pre-configured MCP server templates.

        Returns:
            Dictionary of pre-loaded MCP server templates (deep copy)
        """
        logger.info(f"Loading {len(MCP_SERVER_TEMPLATES)} pre-loaded templates")
        # Deep copy to prevent mutations affecting the template
        return deepcopy(MCP_SERVER_TEMPLATES)

    def migrate(self, config_data: Dict) -> Dict:
        """
        Migrate configuration to current version.

        Args:
            config_data: Configuration data to migrate

        Returns:
            Migrated configuration data
        """
        current_version = config_data.get("version", "1.0.0")

        if "project_profiles" not in config_data:
            config_data["project_profiles"] = {}

        if current_version == CONFIG_VERSION:
            return config_data

        logger.info(f"Migrating config from {current_version} to {CONFIG_VERSION}")

        # Migration logic for future versions
        # if current_version < "1.1.0":
        #     config_data = self._migrate_to_1_1_0(config_data)

        config_data["version"] = CONFIG_VERSION
        return config_data

    def validate_config(self, config_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate configuration data structure.

        Args:
            config_data: Configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required keys
        required_keys = ["version", "preferences", "servers", "profiles", "project_profiles"]
        for key in required_keys:
            if key not in config_data:
                errors.append(f"Missing required key: {key}")

        # Validate version
        if "version" in config_data:
            if not isinstance(config_data["version"], str):
                errors.append("Version must be a string")

        # Validate preferences
        if "preferences" in config_data:
            if not isinstance(config_data["preferences"], dict):
                errors.append("Preferences must be a dictionary")

        # Validate servers
        if "servers" in config_data:
            if not isinstance(config_data["servers"], dict):
                errors.append("Servers must be a dictionary")
            else:
                for server_id, server_data in config_data["servers"].items():
                    if not isinstance(server_data, dict):
                        errors.append(f"Server {server_id} must be a dictionary")

        # Validate profiles
        if "profiles" in config_data:
            if not isinstance(config_data["profiles"], dict):
                errors.append("Profiles must be a dictionary")
            else:
                for profile_id, profile_data in config_data["profiles"].items():
                    if not isinstance(profile_data, dict):
                        errors.append(f"Profile {profile_id} must be a dictionary")

        if "project_profiles" in config_data:
            if not isinstance(config_data["project_profiles"], dict):
                errors.append("Project profiles must be a dictionary")
            else:
                for project_path, project_collection in config_data["project_profiles"].items():
                    if not isinstance(project_collection, dict):
                        errors.append(f"Project profiles for {project_path} must be a dictionary")
                        continue
                    for profile_id, profile_data in project_collection.items():
                        if not isinstance(profile_data, dict):
                            errors.append(
                                f"Project profile {profile_id} in {project_path} must be a dictionary"
                            )

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_project_profiles(self, project_path: Optional[str]) -> Dict[str, Profile]:
        """Return an empty mapping (project profiles deprecated)."""
        return {}

    def set_project_profiles_for_path(self, project_path: Optional[str], profiles: Dict[str, Profile]):
        """No-op retained for compatibility with legacy callers."""
        logger.debug(
            "set_project_profiles_for_path called for %s with %d profiles (ignored)",
            project_path,
            len(profiles) if profiles else 0
        )

    def remove_project_profile(self, project_path: Optional[str], profile_id: str):
        """No-op retained for compatibility with legacy callers."""
        logger.debug(
            "remove_project_profile called for %s/%s (ignored)",
            project_path,
            profile_id
        )

    def _serialize_project_profiles(
        self,
        project_profiles: Optional[Dict[str, Dict[str, Profile]]]
    ) -> Dict[str, Dict[str, dict]]:
        """Always return an empty mapping when saving configuration."""
        return {}

    def _cleanup_legacy_files(self):
        """Remove legacy per-project profile files once data is centralized."""
        for legacy_path in list(self._legacy_cleanup_paths):
            try:
                if legacy_path.exists():
                    legacy_path.unlink()
                    parent = legacy_path.parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
            except Exception as exc:
                logger.warning(f"Failed to clean up legacy project profiles file {legacy_path}: {exc}")
            finally:
                self._legacy_cleanup_paths.discard(legacy_path)

    def _promote_project_profile(
        self,
        profile: Profile,
        servers: Dict[str, MCPServer],
        profiles: Dict[str, Profile]
    ) -> str:
        """Convert a project-scoped profile to global scope and insert into profiles dict."""
        profile.scope = "global"
        profile.project_path = None
        if profile.servers:
            profile.servers = [sid for sid in profile.servers if sid in servers]

        base_id = profile.id or "profile"
        unique_id = base_id
        counter = 1
        while unique_id in profiles:
            unique_id = f"{base_id}-{counter}"
            counter += 1

        if unique_id != profile.id:
            profile.id = unique_id

        profiles[unique_id] = profile
        return unique_id

    def import_legacy_project_profiles(self, project_path: Optional[str]) -> int:
        """Import profiles from legacy per-project storage into the global config."""
        normalized_path = self._normalize_path(project_path)
        if not normalized_path:
            return 0

        profiles_file = Path(normalized_path) / ".cc-launcher" / "profiles.json"
        if not profiles_file.exists():
            return 0

        try:
            with open(profiles_file, 'r', encoding='utf-8') as handle:
                data = json.load(handle) or {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read legacy project profiles from %s: %s", profiles_file, exc)
            return 0

        preferences, servers, profiles = self.load()

        promoted = 0
        for profile_id, profile_dict in data.items():
            try:
                profile = Profile.from_dict(profile_dict)
                self._promote_project_profile(profile, servers, profiles)
                promoted += 1
            except Exception as exc:
                logger.error("Failed to import legacy profile %s from %s: %s", profile_id, profiles_file, exc)

        if promoted:
            self._legacy_cleanup_paths.add(profiles_file)
            self.save(preferences, servers, profiles)
            self._cleanup_legacy_files()
            logger.info("Imported %s legacy project profiles from %s", promoted, normalized_path)

        return promoted