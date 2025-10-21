"""
Unit tests for ProfileManager
"""

import pytest
from pathlib import Path
from datetime import datetime
import shutil
import time

from core.profile_manager import ProfileManager
from core.config_manager import ConfigManager
from models.profile import Profile
from models.server import MCPServer
from models.preferences import Preferences


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def config_manager(temp_config_dir, monkeypatch):
    """Create a ConfigManager with temp directory."""
    # Patch constants before creating ConfigManager
    from utils import constants
    monkeypatch.setattr(constants, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(constants, "CONFIG_FILE", temp_config_dir / "cc-launch.json")
    return ConfigManager()


@pytest.fixture
def profile_manager(config_manager):
    """Create a ProfileManager with test ConfigManager."""
    return ProfileManager(config_manager)


@pytest.fixture
def sample_servers():
    """Create sample servers for testing."""
    return {
        "filesystem": MCPServer(
            id="filesystem",
            type="stdio",
            enabled=True,
            is_template=False,
            order=0,
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem"]
        ),
        "ref": MCPServer(
            id="ref",
            type="stdio",
            enabled=False,
            is_template=False,
            order=1,
            command="npx",
            args=["-y", "@ref-mcp/server"]
        ),
        "supabase": MCPServer(
            id="supabase",
            type="stdio",
            enabled=False,
            is_template=False,
            order=2,
            command="npx",
            args=["-y", "@supabase/mcp-server"]
        )
    }


@pytest.fixture
def setup_config(config_manager, sample_servers):
    """Set up initial config with servers."""
    preferences = Preferences()
    profiles = {}
    config_manager.save(preferences, sample_servers, profiles)
    return preferences, sample_servers, profiles


class TestCreateProfile:
    """Test profile creation."""

    def test_create_profile_success(self, profile_manager, setup_config):
        """Test creating a new profile."""
        success, error, profile = profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem", "ref"],
            description="Dev profile"
        )

        assert success is True
        assert error is None
        assert profile is not None
        assert profile.id == "dev"
        assert profile.name == "Development"
        assert profile.servers == ["filesystem", "ref"]
        assert profile.description == "Dev profile"
        assert profile.created is not None
        assert profile.modified is not None
        assert profile.last_used is None

    def test_create_profile_duplicate_id(self, profile_manager, setup_config):
        """Test creating profile with duplicate ID fails."""
        # Create first profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Try to create duplicate
        success, error, profile = profile_manager.create_profile(
            profile_id="dev",
            name="Another Dev",
            server_ids=["ref"]
        )

        assert success is False
        assert "already exists" in error
        assert profile is None

    def test_create_profile_invalid_server_id(self, profile_manager, setup_config):
        """Test creating profile with non-existent server fails."""
        success, error, profile = profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem", "nonexistent"]
        )

        assert success is False
        assert "does not exist" in error
        assert profile is None

    def test_create_profile_persists(self, profile_manager, setup_config):
        """Test created profile is saved to config."""
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem", "ref"]
        )

        # Reload config
        preferences, servers, profiles = profile_manager.config_manager.load()

        assert "dev" in profiles
        assert profiles["dev"].name == "Development"
        assert profiles["dev"].servers == ["filesystem", "ref"]


class TestUpdateProfile:
    """Test profile updates."""

    def test_update_profile_name(self, profile_manager, setup_config):
        """Test updating profile name."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Update name
        success, error, profile = profile_manager.update_profile(
            profile_id="dev",
            name="Dev Environment"
        )

        assert success is True
        assert error is None
        assert profile.name == "Dev Environment"
        assert profile.servers == ["filesystem"]  # Unchanged

    def test_update_profile_servers(self, profile_manager, setup_config):
        """Test updating profile server list."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Update servers
        success, error, profile = profile_manager.update_profile(
            profile_id="dev",
            server_ids=["filesystem", "ref", "supabase"]
        )

        assert success is True
        assert error is None
        assert profile.servers == ["filesystem", "ref", "supabase"]

    def test_update_profile_description(self, profile_manager, setup_config):
        """Test updating profile description."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Update description
        success, error, profile = profile_manager.update_profile(
            profile_id="dev",
            description="Updated description"
        )

        assert success is True
        assert profile.description == "Updated description"

    def test_update_profile_not_found(self, profile_manager, setup_config):
        """Test updating non-existent profile fails."""
        success, error, profile = profile_manager.update_profile(
            profile_id="nonexistent",
            name="New Name"
        )

        assert success is False
        assert "not found" in error
        assert profile is None

    def test_update_profile_invalid_server(self, profile_manager, setup_config):
        """Test updating with invalid server ID fails."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Try to update with invalid server
        success, error, profile = profile_manager.update_profile(
            profile_id="dev",
            server_ids=["nonexistent"]
        )

        assert success is False
        assert "does not exist" in error

    def test_update_profile_updates_modified(self, profile_manager, setup_config):
        """Test that update changes modified timestamp."""
        # Create profile
        _, _, profile1 = profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        time.sleep(0.01)  # Ensure time difference

        # Update profile
        _, _, profile2 = profile_manager.update_profile(
            profile_id="dev",
            name="Dev Environment"
        )

        assert profile2.modified > profile1.modified


class TestDeleteProfile:
    """Test profile deletion."""

    def test_delete_profile_success(self, profile_manager, setup_config):
        """Test deleting a profile."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Delete it
        success, error = profile_manager.delete_profile("dev")

        assert success is True
        assert error is None

        # Verify it's gone
        profiles = profile_manager.list_profiles()
        assert "dev" not in profiles

    def test_delete_profile_not_found(self, profile_manager, setup_config):
        """Test deleting non-existent profile fails."""
        success, error = profile_manager.delete_profile("nonexistent")

        assert success is False
        assert "not found" in error

    def test_delete_last_used_profile_clears_preference(self, profile_manager, setup_config):
        """Test deleting last used profile updates preference."""
        # Create and switch to profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )
        profile_manager.switch_profile("dev")

        # Delete it
        profile_manager.delete_profile("dev")

        # Check preference was reset
        preferences, _, _ = profile_manager.config_manager.load()
        assert preferences.last_profile == "default"


class TestGetProfile:
    """Test getting a single profile."""

    def test_get_profile_success(self, profile_manager, setup_config):
        """Test getting an existing profile."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Get it
        profile = profile_manager.get_profile("dev")

        assert profile is not None
        assert profile.id == "dev"
        assert profile.name == "Development"

    def test_get_profile_not_found(self, profile_manager, setup_config):
        """Test getting non-existent profile returns None."""
        profile = profile_manager.get_profile("nonexistent")
        assert profile is None


class TestListProfiles:
    """Test listing all profiles."""

    def test_list_profiles_empty(self, profile_manager, setup_config):
        """Test listing profiles when none exist."""
        profiles = profile_manager.list_profiles()
        assert profiles == {}

    def test_list_profiles_multiple(self, profile_manager, setup_config):
        """Test listing multiple profiles."""
        # Create profiles
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )
        profile_manager.create_profile(
            profile_id="prod",
            name="Production",
            server_ids=["filesystem", "ref"]
        )

        # List them
        profiles = profile_manager.list_profiles()

        assert len(profiles) == 2
        assert "dev" in profiles
        assert "prod" in profiles


class TestSwitchProfile:
    """Test switching profiles."""

    def test_switch_profile_success(self, profile_manager, setup_config):
        """Test switching to a profile."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem", "ref"]
        )

        # Switch to it
        success, error, profile, servers = profile_manager.switch_profile("dev")

        assert success is True
        assert error is None
        assert profile.id == "dev"
        assert profile.last_used is not None
        assert servers is not None

        # Check server enabled states
        assert servers["filesystem"].enabled is True
        assert servers["ref"].enabled is True
        assert servers["supabase"].enabled is False

    def test_switch_profile_updates_preference(self, profile_manager, setup_config):
        """Test switching updates last_profile preference."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Switch to it
        profile_manager.switch_profile("dev")

        # Check preference
        preferences, _, _ = profile_manager.config_manager.load()
        assert preferences.last_profile == "dev"

    def test_switch_profile_not_found(self, profile_manager, setup_config):
        """Test switching to non-existent profile fails."""
        success, error, profile, servers = profile_manager.switch_profile("nonexistent")

        assert success is False
        assert "not found" in error
        assert profile is None
        assert servers is None

    def test_switch_profile_updates_last_used(self, profile_manager, setup_config):
        """Test switching updates profile last_used timestamp."""
        # Create profile
        _, _, profile1 = profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        assert profile1.last_used is None

        time.sleep(0.01)

        # Switch to it
        _, _, profile2, _ = profile_manager.switch_profile("dev")

        assert profile2.last_used is not None
        assert profile2.last_used > profile1.created


class TestGetEnabledServers:
    """Test getting currently enabled servers."""

    def test_get_enabled_servers(self, profile_manager, setup_config):
        """Test getting list of enabled servers."""
        enabled = profile_manager.get_enabled_servers()

        # From setup_config, only filesystem is enabled
        assert enabled == ["filesystem"]

    def test_get_enabled_servers_after_switch(self, profile_manager, setup_config):
        """Test getting enabled servers after profile switch."""
        # Create and switch to profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["ref", "supabase"]
        )
        profile_manager.switch_profile("dev")

        # Check enabled servers
        enabled = profile_manager.get_enabled_servers()
        assert set(enabled) == {"ref", "supabase"}


class TestSaveCurrentState:
    """Test saving current state to profile."""

    def test_save_current_state_to_profile(self, profile_manager, setup_config):
        """Test saving current server states to existing profile."""
        # Create profile
        profile_manager.create_profile(
            profile_id="dev",
            name="Development",
            server_ids=["filesystem"]
        )

        # Manually enable different servers
        preferences, servers, profiles = profile_manager.config_manager.load()
        servers["ref"].enabled = True
        servers["supabase"].enabled = True
        servers["filesystem"].enabled = False
        profile_manager.config_manager.save(preferences, servers, profiles)

        # Save current state to profile
        success, error = profile_manager.save_current_state_to_profile("dev")

        assert success is True
        assert error is None

        # Check profile was updated
        profile = profile_manager.get_profile("dev")
        assert set(profile.servers) == {"ref", "supabase"}

    def test_save_current_state_to_nonexistent_profile(self, profile_manager, setup_config):
        """Test saving to non-existent profile fails."""
        success, error = profile_manager.save_current_state_to_profile("nonexistent")

        assert success is False
        assert "not found" in error