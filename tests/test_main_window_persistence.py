from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from models.preferences import Preferences
from models.profile import Profile
from models.server import MCPServer
from ui.main_window import MainWindow


def _build_window_stub() -> MainWindow:
    window = MainWindow.__new__(MainWindow)
    window.global_profiles = {}
    return window


def test_persist_config_updates_preferences_and_saves(tmp_path):
    window = _build_window_stub()

    project_path = tmp_path / "project"
    project_path.mkdir()

    other_path = tmp_path / "existing"

    broken_path = "BROKEN_PATH_VALUE"

    preferences = Preferences()
    preferences.theme = "light"
    preferences.recent_projects = [str(other_path), str(project_path), broken_path]
    preferences.project_last_profiles = {
        str(other_path): "existing-profile",
        broken_path: "broken-profile"
    }

    window.preferences = preferences
    window.project_selector = Mock(get_path=Mock(return_value=str(project_path)))
    window.profile_manager = Mock(get_selected_profile_id=Mock(return_value="new-profile"))
    window.current_theme = "dark"

    original_normalize = MainWindow._normalize_path

    def fake_normalize(path):
        if path == broken_path:
            return None
        return original_normalize(path)

    window._normalize_path = fake_normalize

    server = MCPServer(
        id="server-1",
        type="stdio",
        command="cmd",
        args=["/c", "echo"],
        env={},
        enabled=True
    )
    window.servers = {"server-1": server}

    now = datetime.now()
    profile = Profile(
        id="new-profile",
        name="New Profile",
        servers=["server-1"],
        created=now,
        modified=now
    )

    window.profile_manager_core = Mock(list_profiles=Mock(return_value={"new-profile": profile}))
    window.config_manager = Mock()

    window._persist_config()

    normalized_project = str(Path(project_path).resolve())

    assert preferences.last_path == normalized_project
    assert preferences.last_profile == "new-profile"
    assert preferences.project_last_profiles[normalized_project] == "new-profile"
    assert preferences.project_last_profiles[str(Path(other_path).resolve())] == "existing-profile"
    assert preferences.project_last_profiles[broken_path] == "broken-profile"
    assert broken_path in preferences.recent_projects
    assert preferences.theme == "dark"
    assert window.global_profiles == {"new-profile": profile}

    window.config_manager.save.assert_called_once_with(
        preferences,
        window.servers,
        {"new-profile": profile}
    )


def test_on_closing_persists_and_quits_when_not_tray():
    window = _build_window_stub()

    window._persist_config = Mock()
    window.preferences = Preferences()
    window.preferences.close_to_tray = False
    window.tray_manager = None
    window.terminal_manager = Mock(cleanup_temp_config=Mock())
    window.quit = Mock()

    window._on_closing()

    window._persist_config.assert_called_once()
    window.terminal_manager.cleanup_temp_config.assert_called_once()
    window.quit.assert_called_once()


def test_on_closing_minimizes_when_tray_enabled():
    window = _build_window_stub()

    window._persist_config = Mock()
    window.preferences = Preferences()
    window.preferences.close_to_tray = True
    window.tray_manager = object()
    window.withdraw = Mock()
    window.terminal_manager = Mock(cleanup_temp_config=Mock())
    window.quit = Mock()

    window._on_closing()

    window._persist_config.assert_called_once()
    window.withdraw.assert_called_once()
    window.terminal_manager.cleanup_temp_config.assert_not_called()
    window.quit.assert_not_called()

