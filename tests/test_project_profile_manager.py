"""Regression tests for legacy project profile behavior."""

import json
from datetime import datetime

import pytest

from core.config_manager import ConfigManager
from models.profile import Profile


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    """Provide a ConfigManager wired to a temporary configuration directory."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir(parents=True, exist_ok=True)

    from utils import constants
    monkeypatch.setattr(constants, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(constants, "CONFIG_FILE", config_dir / "cc-launch.json")
    monkeypatch.setattr(constants, "BACKUP_FILE", config_dir / "cc-launch.backup")
    monkeypatch.setattr(constants, "LOCK_FILE", config_dir / "cc-launch.lock")

    manager = ConfigManager()
    manager.load()
    return manager, config_dir


def test_get_project_profiles_always_empty(config_env):
    manager, _ = config_env

    assert manager.get_project_profiles(None) == {}
    assert manager.get_project_profiles("C:/tmp/project") == {}


def test_set_project_profiles_is_noop(config_env):
    manager, config_dir = config_env

    project_path = str(config_dir / "demo")
    profile = Profile(
        id="legacy",
        name="Legacy",
        servers=["filesystem"],
        created=datetime.now(),
        modified=datetime.now(),
    )

    # Call setter – should not raise or persist anything.
    manager.set_project_profiles_for_path(project_path, {profile.id: profile})
    assert manager.get_project_profiles(project_path) == {}


def test_import_legacy_project_profiles_promotes_to_global(config_env, tmp_path):
    manager, _ = config_env

    project_dir = tmp_path / "legacy_proj"
    legacy_dir = project_dir / ".cc-launcher"
    legacy_dir.mkdir(parents=True, exist_ok=True)

    legacy_profile = Profile(
        id="legacy",
        name="Legacy",
        servers=["filesystem"],
        created=datetime.now(),
        modified=datetime.now(),
        description="Legacy project profile"
    )

    (legacy_dir / "profiles.json").write_text(
        json.dumps({"legacy": legacy_profile.to_dict()}),
        encoding="utf-8"
    )

    promoted = manager.import_legacy_project_profiles(str(project_dir))
    assert promoted == 1

    _, _, profiles = manager.load()
    assert "legacy" in profiles
    assert profiles["legacy"].scope == "global"
