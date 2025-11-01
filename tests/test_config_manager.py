"""Unit tests for ConfigManager."""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime

from core.config_manager import ConfigManager
from models.preferences import Preferences
from models.server import MCPServer
from models.profile import Profile
from utils.constants import CONFIG_VERSION, MCP_SERVER_TEMPLATES


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def config_manager(temp_config_dir, monkeypatch):
    """Create ConfigManager with temporary directory."""
    # Patch constants module before importing ConfigManager
    from utils import constants
    monkeypatch.setattr(constants, "CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr(constants, "CONFIG_FILE", temp_config_dir / "config.json")
    monkeypatch.setattr(constants, "BACKUP_FILE", temp_config_dir / "config.backup")
    monkeypatch.setattr(constants, "LOCK_FILE", temp_config_dir / "config.lock")

    # Reload the config_manager module to pick up new constants
    from importlib import reload
    import core.config_manager
    reload(core.config_manager)

    manager = core.config_manager.ConfigManager()
    return manager


class TestConfigManagerInit:
    """Tests for ConfigManager initialization."""

    def test_init_creates_directory(self, tmp_path, monkeypatch):
        """Test that initialization creates config directory."""
        from utils import constants
        new_dir = tmp_path / "new_config"
        monkeypatch.setattr(constants, "CONFIG_DIR", new_dir)
        monkeypatch.setattr(constants, "CONFIG_FILE", new_dir / "config.json")
        monkeypatch.setattr(constants, "BACKUP_FILE", new_dir / "config.backup")
        monkeypatch.setattr(constants, "LOCK_FILE", new_dir / "config.lock")

        # Reload ConfigManager to use new constants
        from importlib import reload
        import core.config_manager
        reload(core.config_manager)

        manager = core.config_manager.ConfigManager()
        assert new_dir.exists()

    def test_init_sets_paths(self, tmp_path, monkeypatch):
        """Test that initialization sets correct paths."""
        from utils import constants
        config_dir = tmp_path / ".claude"
        monkeypatch.setattr(constants, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(constants, "CONFIG_FILE", config_dir / "config.json")
        monkeypatch.setattr(constants, "BACKUP_FILE", config_dir / "config.backup")
        monkeypatch.setattr(constants, "LOCK_FILE", config_dir / "config.lock")

        # Reload to pick up new constants
        from importlib import reload
        import core.config_manager
        reload(core.config_manager)

        manager = core.config_manager.ConfigManager()
        assert manager.config_file.parent == config_dir
        assert manager.backup_file.parent == config_dir
        assert manager.lock_file.parent == config_dir


class TestConfigManagerLock:
    """Tests for file locking mechanism."""

    def test_acquire_lock_success(self, config_manager):
        """Test successful lock acquisition."""
        assert config_manager._acquire_lock()
        assert config_manager.lock_file.exists()
        config_manager._release_lock()

    def test_release_lock(self, config_manager):
        """Test lock release."""
        config_manager._acquire_lock()
        config_manager._release_lock()
        assert not config_manager.lock_file.exists()

    def test_lock_timeout(self, config_manager):
        """Test lock timeout when file is locked."""
        # Create lock file manually
        config_manager.lock_file.touch()

        # Try to acquire with short timeout
        assert not config_manager._acquire_lock(timeout=0.2)

        # Cleanup
        config_manager.lock_file.unlink()


class TestConfigManagerLoad:
    """Tests for configuration loading."""

    def test_load_missing_file_creates_default(self, config_manager):
        """Test loading when config file doesn't exist."""
        prefs, servers, profiles = config_manager.load()

        # Check defaults
        assert isinstance(prefs, Preferences)
        assert prefs.theme == "dark"
        assert prefs.default_path == ""

        # Check templates loaded
        assert len(servers) == len(MCP_SERVER_TEMPLATES)
        assert "filesystem" in servers
        assert "ref" in servers

        # Check default profile
        assert "default" in profiles
        assert profiles["default"].name == "Default Profile"

    def test_load_valid_config(self, config_manager):
        """Test loading valid configuration file."""
        # Create valid config
        config_data = {
            "version": CONFIG_VERSION,
            "preferences": Preferences(theme="light").to_dict(),
            "servers": {
                "test": MCPServer(
                    id="test",
                    type="stdio",
                    command="cmd",
                    args=["/c", "echo", "test"]
                ).to_dict()
            },
            "profiles": {
                "custom": Profile(
                    id="custom",
                    name="Custom Profile",
                    servers=["test"],
                    created=datetime.now(),
                    modified=datetime.now()
                ).to_dict()
            }
        }

        with open(config_manager.config_file, 'w') as f:
            json.dump(config_data, f, default=str)

        prefs, servers, profiles = config_manager.load()

        assert prefs.theme == "light"
        assert "test" in servers
        assert "custom" in profiles

    def test_load_corrupted_json_restores_backup(self, config_manager):
        """Test loading corrupted config restores from backup."""
        # Create valid backup
        backup_data = {
            "version": CONFIG_VERSION,
            "preferences": Preferences(theme="light").to_dict(),
            "servers": {},
            "profiles": {}
        }

        with open(config_manager.backup_file, 'w') as f:
            json.dump(backup_data, f)

        # Create corrupted config
        with open(config_manager.config_file, 'w') as f:
            f.write("{ invalid json }")

        prefs, servers, profiles = config_manager.load()

        # Should restore from backup
        assert prefs.theme == "light"

    def test_load_corrupted_no_backup_creates_default(self, config_manager):
        """Test loading corrupted config with no backup creates default."""
        # Create corrupted config, no backup
        with open(config_manager.config_file, 'w') as f:
            f.write("{ invalid json }")

        prefs, servers, profiles = config_manager.load()

        # Should create default with templates
        assert isinstance(prefs, Preferences)
        # Check we got templates loaded (at least some servers)
        assert len(servers) > 0
        assert "filesystem" in servers or "default" in profiles

    def test_load_restores_missing_templates(self, config_manager):
        """Missing default templates should be restored on load."""
        custom_server = MCPServer(
            id="custom",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "custom"],
            enabled=True
        ).to_dict()

        config_data = {
            "version": CONFIG_VERSION,
            "preferences": Preferences().to_dict(),
            "servers": {
                "custom": custom_server
            },
            "profiles": {}
        }

        with open(config_manager.config_file, 'w') as f:
            json.dump(config_data, f, default=str)

        _, servers, _ = config_manager.load()

        # Custom server should remain
        assert "custom" in servers

        # All templates should be present
        for template_id in MCP_SERVER_TEMPLATES.keys():
            assert template_id in servers


class TestConfigManagerSave:
    """Tests for configuration saving."""

    def test_save_creates_file(self, config_manager):
        """Test save creates config file."""
        prefs = Preferences()
        servers = {}
        profiles = {}

        config_manager.save(prefs, servers, profiles)

        assert config_manager.config_file.exists()

    def test_save_creates_backup(self, config_manager):
        """Test save creates backup of existing config."""
        # Create initial config
        prefs = Preferences(theme="light")
        config_manager.save(prefs, {}, {})

        # Save again
        prefs.theme = "dark"
        config_manager.save(prefs, {}, {})

        assert config_manager.backup_file.exists()

    def test_save_atomic_write(self, config_manager):
        """Test save uses atomic write with temp file."""
        prefs = Preferences()
        servers = {
            "test": MCPServer(
                id="test",
                type="stdio",
                command="cmd",
                args=["/c", "echo"]
            )
        }
        profiles = {}

        config_manager.save(prefs, servers, profiles)

        # Verify data
        with open(config_manager.config_file, 'r') as f:
            data = json.load(f)

        assert data["version"] == CONFIG_VERSION
        assert "test" in data["servers"]

    def test_save_preserves_data_integrity(self, config_manager):
        """Test save preserves all data correctly."""
        prefs = Preferences(
            theme="light",
            default_path="C:\\Projects",
            minimize_on_launch=False
        )
        servers = {
            "fs": MCPServer(
                id="fs",
                type="stdio",
                command="cmd",
                args=["/c", "npx", "server"]
            )
        }
        profiles = {
            "test": Profile(
                id="test",
                name="Test Profile",
                servers=["fs"],
                created=datetime.now(),
                modified=datetime.now()
            )
        }

        config_manager.save(prefs, servers, profiles)
        loaded_prefs, loaded_servers, loaded_profiles = config_manager.load()

        assert loaded_prefs.theme == "light"
        assert loaded_prefs.default_path == "C:\\Projects"
        assert loaded_prefs.minimize_on_launch is False
        assert "fs" in loaded_servers
        assert "test" in loaded_profiles


class TestConfigManagerRollback:
    """Tests for save with rollback."""

    def test_save_with_rollback_success(self, config_manager):
        """Test successful save with rollback."""
        prefs = Preferences()
        result = config_manager.save_with_rollback(prefs, {}, {})
        assert result is True
        assert config_manager.config_file.exists()


    def test_custom_server_persists_across_load(self, config_manager):
        """Servers added via UI should persist after reload."""
        prefs, servers, profiles = config_manager.load()

        servers["custom_server"] = MCPServer(
            id="custom_server",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "persisted"],
            enabled=True,
            description="Custom server for persistence test",
            category="test"
        )

        config_manager.save(prefs, servers, profiles)

        _, reloaded_servers, _ = config_manager.load()

        assert "custom_server" in reloaded_servers
        reloaded = reloaded_servers["custom_server"]
        assert reloaded.command == "cmd"
        assert reloaded.args == ["/c", "echo", "persisted"]
        assert reloaded.enabled is True

    def test_save_with_rollback_failure_restores(self, config_manager, monkeypatch):
        """Test failed save triggers rollback."""
        # Create initial config
        prefs1 = Preferences(theme="light")
        config_manager.save(prefs1, {}, {})

        # Patch save to fail
        def failing_save(*args, **kwargs):
            raise IOError("Simulated write error")

        monkeypatch.setattr(config_manager, "save", failing_save)

        # Try to save (should fail and rollback)
        prefs2 = Preferences(theme="dark")
        result = config_manager.save_with_rollback(prefs2, {}, {})

        assert result is False

        # Verify original config preserved
        with open(config_manager.config_file, 'r') as f:
            data = json.load(f)
        assert data["preferences"]["theme"] == "light"


class TestConfigManagerPresets:
    """Tests for preset templates."""

    def test_load_presets_returns_templates(self, config_manager):
        """Test load_presets returns all templates."""
        presets = config_manager.load_presets()

        assert len(presets) == len(MCP_SERVER_TEMPLATES)
        assert "filesystem" in presets
        assert "ref" in presets
        assert "supabase" in presets

    def test_load_presets_returns_copy(self, config_manager):
        """Test load_presets returns copy, not reference."""
        presets1 = config_manager.load_presets()
        presets2 = config_manager.load_presets()

        # Modify one
        presets1["filesystem"].enabled = True

        # Should not affect the other
        assert presets2["filesystem"].enabled is False


class TestConfigManagerMigration:
    """Tests for version migration."""

    def test_migrate_same_version_no_change(self, config_manager):
        """Test migration with same version doesn't change data."""
        config_data = {
            "version": CONFIG_VERSION,
            "preferences": {},
            "servers": {},
            "profiles": {},
            "project_profiles": {}
        }

        result = config_manager.migrate(config_data)
        assert result["version"] == CONFIG_VERSION

    def test_migrate_old_version_updates(self, config_manager):
        """Test migration updates old version."""
        config_data = {
            "version": "0.9.0",
            "preferences": {},
            "servers": {},
            "profiles": {}
        }

        result = config_manager.migrate(config_data)
        assert result["version"] == CONFIG_VERSION


class TestConfigManagerValidation:
    """Tests for configuration validation."""

    def test_validate_valid_config(self, config_manager):
        """Test validation of valid config."""
        config_data = {
            "version": CONFIG_VERSION,
            "preferences": {},
            "servers": {},
            "profiles": {},
            "project_profiles": {}
        }

        is_valid, errors = config_manager.validate_config(config_data)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_keys(self, config_manager):
        """Test validation detects missing keys."""
        config_data = {
            "version": CONFIG_VERSION,
            "preferences": {}
            # Missing servers and profiles
        }

        is_valid, errors = config_manager.validate_config(config_data)
        assert is_valid is False
        assert len(errors) == 3
        assert any("servers" in e for e in errors)
        assert any("profiles" in e for e in errors)

    def test_validate_invalid_types(self, config_manager):
        """Test validation detects invalid types."""
        config_data = {
            "version": 123,  # Should be string
            "preferences": "invalid",  # Should be dict
            "servers": [],  # Should be dict
            "profiles": {},
            "project_profiles": []  # Should be dict
        }

        is_valid, errors = config_manager.validate_config(config_data)
        assert is_valid is False
        assert len(errors) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])