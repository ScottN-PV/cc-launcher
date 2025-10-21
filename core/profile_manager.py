"""
Profile Manager - Business logic for profile operations.

Handles create, update, delete, get, list, and switch operations for profiles.
Integrates with ConfigManager for persistence.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from models.profile import Profile
from models.server import MCPServer
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manages profile operations with persistence."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.current_project_path: Optional[str] = None

    def _normalize_project_path(self, project_path: Optional[str]) -> Optional[str]:
        return self.config_manager.normalize_project_path(project_path)

    def create_profile(
        self,
        profile_id: str,
        name: str,
        server_ids: List[str],
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Profile]]:
        """
        Create a new profile.

        Args:
            profile_id: Unique profile identifier
            name: Display name for profile
            server_ids: List of server IDs to include
            description: Optional description

        Returns:
            Tuple of (success, error_message, profile)
        """
        try:
            # Load current config
            preferences, servers, profiles = self.config_manager.load()

            # Check for duplicate ID
            if profile_id in profiles:
                return False, f"Profile '{profile_id}' already exists", None

            # Validate server IDs exist
            for server_id in server_ids:
                if server_id not in servers:
                    return False, f"Server '{server_id}' does not exist", None

            # Create new profile
            now = datetime.now()
            profile = Profile(
                id=profile_id,
                name=name,
                servers=server_ids,
                created=now,
                modified=now,
                last_used=None,
                description=description
            )

            # Add to profiles dict
            profiles[profile_id] = profile

            # Save to config
            self.config_manager.save(preferences, servers, profiles)

            logger.info(f"Profile created: {profile_id} with {len(server_ids)} servers")
            return True, None, profile

        except Exception as e:
            error_msg = f"Failed to create profile: {e}"
            logger.error(error_msg)
            return False, error_msg, None

    def update_profile(
        self,
        profile_id: str,
        name: Optional[str] = None,
        server_ids: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Profile]]:
        """
        Update an existing profile.

        Args:
            profile_id: Profile to update
            name: New name (if provided)
            server_ids: New server list (if provided)
            description: New description (if provided)

        Returns:
            Tuple of (success, error_message, profile)
        """
        try:
            # Load current config
            preferences, servers, profiles = self.config_manager.load()

            target_profile = profiles.get(profile_id)
            if target_profile is None:
                return False, f"Profile '{profile_id}' not found", None

            # Validate server IDs if provided
            if server_ids is not None:
                for server_id in server_ids:
                    if server_id not in servers:
                        return False, f"Server '{server_id}' does not exist", None

            # Update fields
            if name is not None:
                target_profile.name = name
            if server_ids is not None:
                target_profile.servers = server_ids
            if description is not None:
                target_profile.description = description

            # Update modified timestamp
            target_profile.modified = datetime.now()

            target_profile.scope = "global"
            target_profile.project_path = None

            profiles[profile_id] = target_profile
            self.config_manager.save(preferences, servers, profiles)
            logger.info(f"Profile updated: {profile_id}")

            return True, None, target_profile

        except Exception as e:
            error_msg = f"Failed to update profile: {e}"
            logger.error(error_msg)
            return False, error_msg, None

    def delete_profile(self, profile_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a profile.

        Args:
            profile_id: Profile to delete

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Load current config
            preferences, servers, profiles = self.config_manager.load()

            # Check profile exists
            if profile_id not in profiles:
                return False, f"Profile '{profile_id}' not found"

            # Remove profile
            del profiles[profile_id]

            # If this was the last used profile, clear preference
            if preferences.last_profile == profile_id:
                preferences.last_profile = "default"

            # Save to config
            self.config_manager.save(preferences, servers, profiles)

            logger.info(f"Profile deleted: {profile_id}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to delete profile: {e}"
            logger.error(error_msg)
            return False, error_msg

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        """
        Get a profile by ID.

        Args:
            profile_id: Profile to retrieve

        Returns:
            Profile object or None if not found
        """
        try:
            _, _, profiles = self.config_manager.load()
            return profiles.get(profile_id)
        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            return None

    def list_profiles(self) -> Dict[str, Profile]:
        """
        Get all profiles.

        Returns:
            Dictionary of profile_id -> Profile
        """
        try:
            _, _, profiles = self.config_manager.load()
            return profiles
        except Exception as e:
            logger.error(f"Failed to list profiles: {e}")
            return {}

    def switch_profile(
        self,
        profile_id: str
    ) -> Tuple[bool, Optional[str], Optional[Profile], Optional[Dict[str, MCPServer]]]:
        """Switch to a different profile.

        Updates the profile's last_used timestamp and preferences.last_profile.
        Returns the profile and updated server states.

        Args:
            profile_id: Profile to switch to

        Returns:
            Tuple of (success, error_message, profile, servers_dict)
        """
        try:
            # Load current config
            preferences, servers, profiles = self.config_manager.load()

            profile = profiles.get(profile_id)
            if profile is None:
                return False, f"Profile '{profile_id}' not found", None, None

            now = datetime.now()
            preferences.last_profile = profile_id

            normalized_project = self._normalize_project_path(self.current_project_path)
            if normalized_project:
                preferences.project_last_profiles[normalized_project] = profile_id

            for server_id, server in servers.items():
                server.enabled = server_id in profile.servers

            profile.last_used = now
            profile.modified = now
            profile.scope = "global"
            profile.project_path = None
            profiles[profile_id] = profile

            self.config_manager.save(preferences, servers, profiles)

            logger.info(f"Switched to profile: {profile_id} ({len(profile.servers)} servers)")
            return True, None, profile, servers

        except Exception as e:
            error_msg = f"Failed to switch profile: {e}"
            logger.error(error_msg)
            return False, error_msg, None, None

    def get_enabled_servers(self) -> List[str]:
        """
        Get list of currently enabled server IDs.

        Returns:
            List of server IDs that are enabled
        """
        try:
            _, servers, _ = self.config_manager.load()
            return [sid for sid, server in servers.items() if server.enabled]
        except Exception as e:
            logger.error(f"Failed to get enabled servers: {e}")
            return []

    def save_current_state_to_profile(
        self,
        profile_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Save currently enabled servers to an existing profile.

        Args:
            profile_id: Profile to update with current server states

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get currently enabled servers
            enabled_servers = self.get_enabled_servers()

            # Update profile
            success, error, _ = self.update_profile(
                profile_id=profile_id,
                server_ids=enabled_servers
            )

            if success:
                logger.info(f"Saved current state to profile: {profile_id}")

            return success, error

        except Exception as e:
            error_msg = f"Failed to save state to profile: {e}"
            logger.error(error_msg)
            return False, error_msg

    def set_current_project(self, project_path: Optional[str]):
        """
        Set the current project path for filtering project-specific profiles.

        Args:
            project_path: Path to current project directory
        """
        self.current_project_path = self._normalize_project_path(project_path)
        logger.debug(f"Current project path set to: {project_path}")

        if self.current_project_path:
            imported = self.config_manager.import_legacy_project_profiles(self.current_project_path)
            if imported:
                logger.info("Imported %s legacy project profiles for %s", imported, self.current_project_path)

    def get_all_profiles(self, project_path: Optional[str] = None) -> Dict[str, Profile]:
        """
        Get combined list of global and project-specific profiles.

        Args:
            project_path: Optional project path to load project profiles from.
                         If None, uses self.current_project_path

        Returns:
            Dictionary of profile_id -> Profile (global + project-specific)
        """
        try:
            _, _, profiles = self.config_manager.load()
            logger.debug(f"Loaded {len(profiles)} profiles")
            return profiles

        except Exception as e:
            logger.error(f"Failed to get all profiles: {e}")
            return {}

    def create_profile_with_scope(
        self,
        profile_id: str,
        name: str,
        server_ids: List[str],
        scope: str = "global",
        project_path: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[Profile]]:
        """
        Create a new profile with specified scope (global or project).

        Args:
            profile_id: Unique profile identifier
            name: Display name for profile
            server_ids: List of server IDs to include
            scope: "global" or "project"
            project_path: Required if scope is "project"
            description: Optional description

        Returns:
            Tuple of (success, error_message, profile)
        """
        if scope not in ["global", "project"]:
            logger.debug("create_profile_with_scope received scope '%s', defaulting to global", scope)

        return self.create_profile(
            profile_id=profile_id,
            name=name,
            server_ids=server_ids,
            description=description
        )

    def delete_profile_by_scope(self, profile_id: str, profile: Profile) -> Tuple[bool, Optional[str]]:
        """Delete a profile from appropriate storage based on its scope."""
        return self.delete_profile(profile_id)
