"""Unit tests for ProfileManager with global-only profiles."""

import json
from datetime import datetime

import pytest

from core.config_manager import ConfigManager
from core.profile_manager import ProfileManager
from models.profile import Profile
from models.server import MCPServer


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """Set up ConfigManager bound to a temporary directory."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)

    from utils import constants
    monkeypatch.setattr(constants, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(constants, "CONFIG_FILE", config_dir / "cc-launch.json")
    monkeypatch.setattr(constants, "BACKUP_FILE", config_dir / "cc-launch.backup")
    monkeypatch.setattr(constants, "LOCK_FILE", config_dir / "cc-launch.lock")

    import core.config_manager as cm_module
    monkeypatch.setattr(cm_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cm_module, "CONFIG_FILE", config_dir / "cc-launch.json")
    monkeypatch.setattr(cm_module, "BACKUP_FILE", config_dir / "cc-launch.backup")
    monkeypatch.setattr(cm_module, "LOCK_FILE", config_dir / "cc-launch.lock")

    manager = ConfigManager()
    return manager, config_dir


@pytest.fixture
def profile_manager(config_env):
    manager, _ = config_env
    return ProfileManager(manager)


@pytest.fixture
def setup_servers(config_env):
    from models.preferences import Preferences

    manager, _ = config_env
    servers = {
        "filesystem": MCPServer(
            id="filesystem",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "fs"],
            enabled=False
        ),
        "ref": MCPServer(
            id="ref",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "ref"],
            enabled=False
        )
    }

    manager.save(Preferences(), servers, {})
    return servers


class TestProfileManager:
    def test_create_profile_global(self, profile_manager, setup_servers):
        success, error, profile = profile_manager.create_profile(
            profile_id="test-profile",
            name="Test Profile",
            server_ids=["filesystem"],
            description="Demo"
        )

        assert success is True
        assert error is None
        assert profile is not None
        assert profile.scope == "global"
        assert profile.project_path is None

        _, _, profiles = profile_manager.config_manager.load()
        assert "test-profile" in profiles

    def test_create_profile_duplicate(self, profile_manager, setup_servers):
        profile_manager.create_profile("dup", "Duplicate", ["filesystem"])
        success, error, _ = profile_manager.create_profile("dup", "Duplicate", ["filesystem"])

        assert success is False
        assert "already exists" in (error or "")

    def test_update_profile_servers(self, profile_manager, setup_servers):
        profile_manager.create_profile("update", "Update", ["filesystem"])

        success, error, updated = profile_manager.update_profile(
            "update",
            server_ids=["filesystem", "ref"],
            description="Updated"
        )

        assert success is True
        assert error is None
        assert updated is not None
        assert set(updated.servers) == {"filesystem", "ref"}

    def test_switch_profile_updates_enabled_servers(self, profile_manager, setup_servers):
        profile_manager.create_profile("default", "Default", ["filesystem"])
        profile_manager.create_profile("alt", "Alt", ["ref"])

        success, error, profile, servers = profile_manager.switch_profile("alt")

        assert success is True
        assert error is None
        assert profile.id == "alt"
        assert servers["ref"].enabled is True
        assert servers["filesystem"].enabled is False

    def test_save_current_state_to_profile(self, profile_manager, setup_servers):
        profile_manager.create_profile("state", "State", ["filesystem"])

        prefs, servers, profiles = profile_manager.config_manager.load()
        servers["filesystem"].enabled = False
        servers["ref"].enabled = True
        profile_manager.config_manager.save(prefs, servers, profiles)

        success, error = profile_manager.save_current_state_to_profile("state")

        assert success is True
        assert error is None
        _, _, updated_profiles = profile_manager.config_manager.load()
        assert set(updated_profiles["state"].servers) == {"ref"}

    def test_set_current_project_imports_legacy_profiles(self, profile_manager, setup_servers, tmp_path):
        manager = profile_manager.config_manager

        project_dir = tmp_path / "demo"
        project_dir.mkdir()

        legacy_profile = Profile(
            id="legacy",
            name="Legacy",
            servers=["filesystem"],
            created=datetime.now(),
            modified=datetime.now(),
            description="Legacy profile",
        )

        legacy_dir = project_dir / ".cc-launcher"
        legacy_dir.mkdir()
        (legacy_dir / "profiles.json").write_text(
            json.dumps({"legacy": legacy_profile.to_dict()}),
            encoding="utf-8"
        )

        imported = manager.import_legacy_project_profiles(str(project_dir))

        assert imported == 1
        _, _, profiles = manager.load()
        assert any(p.name == "Legacy" for p in profiles.values())
        assert all(p.scope == "global" for p in profiles.values())

    def test_get_all_profiles_returns_globals(self, profile_manager, setup_servers):
        profile_manager.create_profile("one", "One", ["filesystem"])
        all_profiles = profile_manager.get_all_profiles()
        assert set(all_profiles.keys()) == {"one"}
