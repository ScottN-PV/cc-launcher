"""Unit tests for TerminalManager multi-instance features."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import psutil

from core.terminal_manager import TerminalManager
from models.server import MCPServer


class TestTerminalManagerMultiInstance:
    """Test suite for TerminalManager multi-instance support."""

    @pytest.fixture
    def terminal_manager(self):
        """Create a TerminalManager instance."""
        return TerminalManager()

    @pytest.fixture
    def sample_servers(self):
        """Create sample MCP servers."""
        return {
            "filesystem": MCPServer(
                id="filesystem",
                type="stdio",
                command="cmd",
                args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem"],
                enabled=True
            )
        }

    def test_launch_with_allow_multiple_true(self, terminal_manager, sample_servers, tmp_path):
        """Test launch with allow_multiple=True does not block if CC running."""
        import subprocess
        project_path = str(tmp_path)

        # Mock check_claude_code_running to return a PID (CC already running initially, then new PID)
        with patch.object(terminal_manager, 'check_claude_code_running', side_effect=[12345, 12346]):
            with patch.object(terminal_manager, 'find_terminal', return_value='pwsh'):
                with patch.object(terminal_manager, 'generate_mcp_config', return_value=Path('/tmp/test.json')):
                    with patch.object(terminal_manager, 'build_launch_command', return_value=['pwsh', '-Command', 'test']):
                        with patch('subprocess.Popen') as mock_popen:
                            # Mock process that stays running
                            mock_process = MagicMock()
                            mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd=['pwsh'], timeout=2)
                            mock_popen.return_value = mock_process

                            # Should succeed even with existing CC process
                            success, message = terminal_manager.launch_claude_code(
                                sample_servers,
                                project_path,
                                allow_multiple=True
                            )

                            # Should not block (will fail for other reasons in mock)
                            # But the key test is it doesn't return early with "already running" error
                            assert "already running" not in message.lower()

    def test_launch_with_allow_multiple_false(self, terminal_manager, sample_servers, tmp_path):
        """Test launch with allow_multiple=False blocks if CC running."""
        project_path = str(tmp_path)

        # Mock check_claude_code_running to return a PID (CC already running)
        with patch.object(terminal_manager, 'check_claude_code_running', return_value=12345):
            success, message = terminal_manager.launch_claude_code(
                sample_servers,
                project_path,
                allow_multiple=False
            )

            assert success is False
            assert "already running" in message.lower()
            assert "12345" in message

    def test_session_id_generation(self, terminal_manager, sample_servers, tmp_path):
        """Test that each launch generates a unique session ID."""
        import subprocess
        project_path = str(tmp_path)

        # Mock successful launch
        with patch.object(terminal_manager, 'check_claude_code_running', side_effect=[None, 12345, None, 12346]):
            with patch.object(terminal_manager, 'find_terminal', return_value='pwsh'):
                with patch.object(terminal_manager, 'generate_mcp_config', return_value=Path('/tmp/test.json')):
                    with patch.object(terminal_manager, 'build_launch_command', return_value=['pwsh']):
                        with patch('subprocess.Popen') as mock_popen:
                            mock_process = MagicMock()
                            # Use TimeoutExpired instead of generic Exception
                            mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd=['pwsh'], timeout=2)
                            mock_popen.return_value = mock_process

                            # Launch twice
                            success1, message1 = terminal_manager.launch_claude_code(sample_servers, project_path)
                            success2, message2 = terminal_manager.launch_claude_code(sample_servers, project_path)

                            # Both should have session IDs
                            assert "Session:" in message1, f"Expected 'Session:' in message1: {message1}"
                            assert "Session:" in message2, f"Expected 'Session:' in message2: {message2}"

                            # Extract session IDs (8-char hex)
                            # Messages contain "Session: <id>"
                            lines1 = message1.split('\n')
                            lines2 = message2.split('\n')
                            session1 = [l for l in lines1 if "Session:" in l][0].split(':')[1].strip()
                            session2 = [l for l in lines2 if "Session:" in l][0].split(':')[1].strip()

                            # Should be different
                            assert session1 != session2
                            # Should be 8 chars each
                            assert len(session1) == 8
                            assert len(session2) == 8

    def test_add_session_stores_fields(self, terminal_manager):
        """Test add_session stores all required fields."""
        pid = 12345
        project_path = "C:\\test\\project"
        config_path = Path("C:\\temp\\config.json")
        session_id = "abcd1234"

        terminal_manager.add_session(pid, project_path, config_path, session_id)

        assert len(terminal_manager.active_sessions) == 1
        session = terminal_manager.active_sessions[0]

        assert session['pid'] == pid
        assert session['project_path'] == project_path
        assert session['config_path'] == str(config_path)
        assert session['session_id'] == session_id
        assert 'started_at' in session
        # Verify started_at is a valid ISO format datetime
        datetime.fromisoformat(session['started_at'])

    def test_get_active_sessions_returns_tracked(self, terminal_manager):
        """Test get_active_sessions returns tracked sessions."""
        # Add some sessions
        terminal_manager.add_session(12345, "C:\\project1", Path("C:\\temp\\config1.json"), "sess0001")
        terminal_manager.add_session(12346, "C:\\project2", Path("C:\\temp\\config2.json"), "sess0002")

        # Mock psutil to show both processes running
        with patch('psutil.Process') as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_running.return_value = True
            mock_process.return_value = mock_proc

            sessions = terminal_manager.get_active_sessions()

            assert len(sessions) == 2
            assert sessions[0]['session_id'] == "sess0001"
            assert sessions[1]['session_id'] == "sess0002"

    def test_get_active_sessions_filters_dead_processes(self, terminal_manager):
        """Test get_active_sessions filters out dead processes."""
        # Add two sessions
        terminal_manager.add_session(12345, "C:\\project1", Path("C:\\temp\\config1.json"), "sess0001")
        terminal_manager.add_session(12346, "C:\\project2", Path("C:\\temp\\config2.json"), "sess0002")

        # Mock psutil: first process dead, second alive
        def mock_process_factory(pid):
            mock_proc = MagicMock()
            if pid == 12345:
                # First process is dead
                mock_proc.is_running.return_value = False
            else:
                # Second process is alive
                mock_proc.is_running.return_value = True
            return mock_proc

        with patch('psutil.Process', side_effect=mock_process_factory):
            sessions = terminal_manager.get_active_sessions()

            # Should only return the alive session
            assert len(sessions) == 1
            assert sessions[0]['session_id'] == "sess0002"
            assert sessions[0]['pid'] == 12346

    def test_kill_session_by_id_terminates(self, terminal_manager, tmp_path):
        """Test kill_session terminates specific session."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')

        # Add a session
        terminal_manager.add_session(12345, "C:\\project", config_path, "sess0001")

        # Mock kill_claude_code to succeed
        with patch.object(terminal_manager, 'kill_claude_code', return_value=True):
            success, message = terminal_manager.kill_session("sess0001")

            assert success is True
            assert "sess0001" in message
            assert "terminated" in message.lower()

            # Session should be removed from active list
            assert len(terminal_manager.active_sessions) == 0

    def test_kill_session_cleans_config(self, terminal_manager, tmp_path):
        """Test kill_session cleans up temp config file."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{}')

        # Verify file exists
        assert config_path.exists()

        # Add a session
        terminal_manager.add_session(12345, "C:\\project", config_path, "sess0001")

        # Mock kill_claude_code to succeed
        with patch.object(terminal_manager, 'kill_claude_code', return_value=True):
            success, message = terminal_manager.kill_session("sess0001")

            assert success is True
            # Config file should be deleted
            assert not config_path.exists()

    def test_kill_session_not_found(self, terminal_manager):
        """Test kill_session with non-existent session ID."""
        success, message = terminal_manager.kill_session("nonexistent")

        assert success is False
        assert "not found" in message.lower()

    def test_cleanup_all_sessions(self, terminal_manager, tmp_path):
        """Test cleanup_all_sessions removes all temp configs."""
        # Create temp config files
        config1 = tmp_path / "config1.json"
        config2 = tmp_path / "config2.json"
        config1.write_text('{}')
        config2.write_text('{}')

        # Add sessions
        terminal_manager.add_session(12345, "C:\\project1", config1, "sess0001")
        terminal_manager.add_session(12346, "C:\\project2", config2, "sess0002")

        # Cleanup all
        terminal_manager.cleanup_all_sessions()

        # Both config files should be deleted
        assert not config1.exists()
        assert not config2.exists()
