"""
Project-Specific Profile Manager - Handles loading/saving project-local profiles.

This module manages profiles stored in <project_dir>/.cc-launcher/profiles.json
alongside the global profiles stored in ~/.claude/cc-launch.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from models.profile import Profile

logger = logging.getLogger(__name__)


class ProjectProfileManager:
    """Manages project-specific profile storage."""

    PROJECT_CONFIG_DIR = ".cc-launcher"
    PROJECT_PROFILES_FILE = "profiles.json"

    @staticmethod
    def get_project_config_path(project_path: str) -> Optional[Path]:
        """
        Get the path to project-specific config directory.

        Args:
            project_path: Path to the project directory

        Returns:
            Path to .cc-launcher directory or None if project_path invalid
        """
        if not project_path:
            return None

        try:
            proj_path = Path(project_path)
            if not proj_path.exists() or not proj_path.is_dir():
                return None

            config_dir = proj_path / ProjectProfileManager.PROJECT_CONFIG_DIR
            return config_dir

        except Exception as e:
            logger.error(f"Error getting project config path: {e}")
            return None

    @staticmethod
    def get_project_profiles_file(project_path: str) -> Optional[Path]:
        """
        Get the path to project-specific profiles.json file.

        Args:
            project_path: Path to the project directory

        Returns:
            Path to profiles.json or None if project_path invalid
        """
        config_dir = ProjectProfileManager.get_project_config_path(project_path)
        if not config_dir:
            return None

        return config_dir / ProjectProfileManager.PROJECT_PROFILES_FILE

    @staticmethod
    def load_project_profiles(project_path: str) -> Dict[str, Profile]:
        """
        Load profiles from project-specific storage.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary of profile_id -> Profile, empty dict if file doesn't exist
        """
        profiles_file = ProjectProfileManager.get_project_profiles_file(project_path)
        if not profiles_file or not profiles_file.exists():
            logger.debug(f"No project profiles found at {project_path}")
            return {}

        try:
            with open(profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            profiles = {}
            for profile_id, profile_data in data.items():
                try:
                    profile = Profile.from_dict(profile_data)
                    # Ensure scope is set to project
                    profile.scope = "project"
                    profile.project_path = project_path
                    profiles[profile_id] = profile
                except Exception as e:
                    logger.error(f"Error loading project profile {profile_id}: {e}")

            logger.info(f"Loaded {len(profiles)} project profiles from {project_path}")
            return profiles

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing project profiles JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading project profiles: {e}")
            return {}

    @staticmethod
    def save_project_profiles(project_path: str, profiles: Dict[str, Profile]) -> Tuple[bool, Optional[str]]:
        """
        Save profiles to project-specific storage.

        Args:
            project_path: Path to the project directory
            profiles: Dictionary of profile_id -> Profile to save

        Returns:
            Tuple of (success, error_message)
        """
        try:
            config_dir = ProjectProfileManager.get_project_config_path(project_path)
            if not config_dir:
                return False, "Invalid project path"

            # Create config directory if it doesn't exist
            config_dir.mkdir(parents=True, exist_ok=True)

            profiles_file = config_dir / ProjectProfileManager.PROJECT_PROFILES_FILE

            # Convert profiles to dict format
            data = {}
            for profile_id, profile in profiles.items():
                # Only save project-scoped profiles
                if profile.scope == "project":
                    data[profile_id] = profile.to_dict()

            # Atomic write: temp file -> rename
            temp_file = profiles_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Rename temp file to actual file (atomic on Windows)
            temp_file.replace(profiles_file)

            logger.info(f"Saved {len(data)} project profiles to {project_path}")
            return True, None

        except Exception as e:
            error_msg = f"Error saving project profiles: {e}"
            logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def delete_project_profile(project_path: str, profile_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a single profile from project-specific storage.

        Args:
            project_path: Path to the project directory
            profile_id: ID of profile to delete

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Load all project profiles
            profiles = ProjectProfileManager.load_project_profiles(project_path)

            if profile_id not in profiles:
                return False, f"Profile '{profile_id}' not found in project profiles"

            # Remove the profile
            del profiles[profile_id]

            # Save updated profiles
            return ProjectProfileManager.save_project_profiles(project_path, profiles)

        except Exception as e:
            error_msg = f"Error deleting project profile: {e}"
            logger.error(error_msg)
            return False, error_msg
