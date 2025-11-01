"""Unit tests for terminal_manager.py"""

import pytest
import json
import subprocess
import psutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

from core.terminal_manager import TerminalManager, TerminalType
from models.server import MCPServer


# Fixtures

@pytest.fixture
def terminal_manager():
    """Create a TerminalManager instance."""
    return TerminalManager()


@pytest.fixture
def sample_servers():
    """Create sample enabled servers."""
    return {
        "filesystem": MCPServer(
            id="filesystem",
            type="stdio",
            command="cmd",
            args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", "%CD%"],
            enabled=True,
            description="Local file system access"
        ),
        "ref": MCPServer(
            id="ref",
            type="stdio",
            command="cmd",
            args=["/c", "npx", "-y", "@ref-mcp/server"],
            enabled=True,
            description="Documentation search"
        )
    }


@pytest.fixture
def sample_http_server():
    """Create sample HTTP server."""
    return {
        "api": MCPServer(
            id="api",
            type="http",
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token123"},
            enabled=True,
            description="External API"
        )
    }


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


# Terminal Detection Tests

class TestFindTerminal:
    """Tests for find_terminal()"""

    @patch('subprocess.run')
    def test_find_windows_terminal(self, mock_run, terminal_manager):
        """Test Windows Terminal detection."""
        mock_run.return_value = Mock(returncode=0, stdout="C:\\path\\to\\wt.exe")

        result = terminal_manager.find_terminal()

        assert result == TerminalType.WINDOWS_TERMINAL
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_find_powershell_7(self, mock_which, mock_run, terminal_manager):
        """Test PowerShell 7 detection when Windows Terminal not available."""
        mock_run.return_value = Mock(returncode=1)  # wt not found
        mock_which.side_effect = lambda cmd: "C:\\path\\pwsh.exe" if cmd == "pwsh" else None

        result = terminal_manager.find_terminal()

        assert result == TerminalType.POWERSHELL_7

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_find_powershell_5(self, mock_which, mock_run, terminal_manager):
        """Test PowerShell 5 detection when wt and pwsh not available."""
        mock_run.return_value = Mock(returncode=1)
        mock_which.side_effect = lambda cmd: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if cmd == "powershell" else None

        result = terminal_manager.find_terminal()

        assert result == TerminalType.POWERSHELL_5

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_find_cmd_fallback(self, mock_which, mock_run, terminal_manager):
        """Test CMD fallback when no other terminal found."""
        mock_run.return_value = Mock(returncode=1)
        mock_which.return_value = None

        result = terminal_manager.find_terminal()

        assert result == TerminalType.CMD


class TestCheckPowerShellVersion:
    """Tests for check_powershell_version()"""

    @patch('subprocess.run')
    def test_check_powershell_7_version(self, mock_run, terminal_manager):
        """Test PowerShell 7 version detection."""
        mock_run.return_value = Mock(returncode=0, stdout="7.5.3\n")

        result = terminal_manager.check_powershell_version()

        assert result == "7.5.3"
        mock_run.assert_called_once_with(
            ["pwsh", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True,
            text=True,
            timeout=5
        )

    @patch('subprocess.run')
    def test_check_powershell_5_version(self, mock_run, terminal_manager):
        """Test PowerShell 5 version detection when pwsh not available."""
        # First call (pwsh) fails, second call (powershell) succeeds
        mock_run.side_effect = [
            FileNotFoundError(),
            Mock(returncode=0, stdout="5.1.19041.4648\n")
        ]

        result = terminal_manager.check_powershell_version()

        assert result == "5.1.19041.4648"

    @patch('subprocess.run')
    def test_check_powershell_version_unavailable(self, mock_run, terminal_manager):
        """Test when PowerShell is unavailable."""
        mock_run.side_effect = FileNotFoundError()

        result = terminal_manager.check_powershell_version()

        assert result is None


# Claude Code Process Detection Tests

class TestCheckClaudeCodeRunning:
    """Tests for check_claude_code_running()"""

    @patch('psutil.process_iter')
    def test_claude_code_found(self, mock_process_iter, terminal_manager):
        """Test Claude Code process detection."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 12345,
            'name': 'node.exe',
            'cmdline': ['node', 'C:\\path\\to\\claude.exe', '--mcp-config', 'config.json']
        }
        mock_process_iter.return_value = [mock_proc]

        result = terminal_manager.check_claude_code_running()

        assert result == 12345

    @patch('psutil.process_iter')
    def test_claude_code_not_found(self, mock_process_iter, terminal_manager):
        """Test when Claude Code is not running."""
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 67890,
            'name': 'chrome.exe',
            'cmdline': ['chrome', '--some-flag']
        }
        mock_process_iter.return_value = [mock_proc]

        result = terminal_manager.check_claude_code_running()

        assert result is None

    @patch('psutil.process_iter')
    def test_access_denied_handled(self, mock_process_iter, terminal_manager):
        """Test that AccessDenied errors are handled gracefully."""
        mock_proc = Mock()
        mock_proc.info = {'pid': 1, 'name': 'system'}

        def side_effect(*args, **kwargs):
            if args[0] == ['pid', 'name', 'cmdline']:
                raise psutil.AccessDenied()
            return [mock_proc]

        mock_process_iter.side_effect = side_effect

        result = terminal_manager.check_claude_code_running()

        assert result is None


class TestKillClaudeCode:
    """Tests for kill_claude_code()"""

    @patch('psutil.Process')
    def test_kill_claude_code_success(self, mock_process_class, terminal_manager):
        """Test successful process termination."""
        mock_proc = Mock()
        mock_proc.wait = Mock()
        mock_process_class.return_value = mock_proc

        result = terminal_manager.kill_claude_code(pid=12345)

        assert result is True
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)

    @patch('psutil.Process')
    def test_kill_claude_code_force_kill(self, mock_process_class, terminal_manager):
        """Test force kill when graceful termination times out."""
        mock_proc = Mock()
        mock_proc.wait = Mock(side_effect=[psutil.TimeoutExpired(5), None])
        mock_process_class.return_value = mock_proc

        result = terminal_manager.kill_claude_code(pid=12345)

        assert result is True
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    @patch('psutil.Process')
    def test_kill_claude_code_no_such_process(self, mock_process_class, terminal_manager):
        """Test when process already terminated."""
        mock_process_class.side_effect = psutil.NoSuchProcess(12345)

        result = terminal_manager.kill_claude_code(pid=12345)

        assert result is True

    @patch('psutil.Process')
    def test_kill_claude_code_access_denied(self, mock_process_class, terminal_manager):
        """Test when access is denied."""
        mock_proc = Mock()
        mock_proc.terminate = Mock(side_effect=psutil.AccessDenied())
        mock_process_class.return_value = mock_proc

        result = terminal_manager.kill_claude_code(pid=12345)

        assert result is False

    @patch.object(TerminalManager, 'check_claude_code_running')
    def test_kill_claude_code_no_pid_provided(self, mock_check, terminal_manager):
        """Test when no PID provided and no process running."""
        mock_check.return_value = None

        result = terminal_manager.kill_claude_code()

        assert result is False


# MCP Config Generation Tests

class TestGenerateMCPConfig:
    """Tests for generate_mcp_config()"""

    def test_generate_stdio_servers(self, terminal_manager, sample_servers, temp_dir):
        """Test MCP config generation with stdio servers."""
        project_path = str(temp_dir)

        with patch('pathlib.Path.home', return_value=temp_dir):
            config_path = terminal_manager.generate_mcp_config(sample_servers, project_path)

        assert config_path.exists()
        assert config_path.suffix == '.json'
        assert 'cc-mcp-' in config_path.name

        with open(config_path, 'r') as f:
            config = json.load(f)

        assert 'mcpServers' in config
        assert 'filesystem' in config['mcpServers']
        assert 'ref' in config['mcpServers']

        # Check filesystem server has expanded %CD%
        fs_server = config['mcpServers']['filesystem']
        assert fs_server['type'] == 'stdio'
        assert fs_server['command'] == 'cmd'
        assert project_path in fs_server['args']

    def test_generate_http_server(self, terminal_manager, sample_http_server, temp_dir):
        """Test MCP config generation with HTTP server."""
        project_path = str(temp_dir)

        with patch('pathlib.Path.home', return_value=temp_dir):
            config_path = terminal_manager.generate_mcp_config(sample_http_server, project_path)

        with open(config_path, 'r') as f:
            config = json.load(f)

        api_server = config['mcpServers']['api']
        assert api_server['type'] == 'http'
        assert api_server['url'] == 'https://api.example.com/mcp'
        assert api_server['headers'] == {'Authorization': 'Bearer token123'}

    def test_generate_mixed_servers(self, terminal_manager, sample_servers, sample_http_server, temp_dir):
        """Test MCP config generation with mixed stdio and HTTP servers."""
        mixed_servers = {**sample_servers, **sample_http_server}
        project_path = str(temp_dir)

        with patch('pathlib.Path.home', return_value=temp_dir):
            config_path = terminal_manager.generate_mcp_config(mixed_servers, project_path)

        with open(config_path, 'r') as f:
            config = json.load(f)

        assert len(config['mcpServers']) == 3
        assert 'filesystem' in config['mcpServers']
        assert 'api' in config['mcpServers']

    def test_generate_no_servers_error(self, terminal_manager, temp_dir):
        """Test error when no servers provided."""
        with pytest.raises(ValueError, match="No servers provided"):
            terminal_manager.generate_mcp_config({}, str(temp_dir))

    def test_generate_env_var_expansion(self, terminal_manager, temp_dir):
        """Test environment variable expansion in args."""
        server = MCPServer(
            id="test",
            type="stdio",
            command="cmd",
            args=["/c", "echo", "%CD%"],
            enabled=True
        )
        project_path = str(temp_dir)

        with patch('pathlib.Path.home', return_value=temp_dir):
            config_path = terminal_manager.generate_mcp_config({"test": server}, project_path)

        with open(config_path, 'r') as f:
            config = json.load(f)

        # %CD% should be replaced with project_path
        assert project_path in config['mcpServers']['test']['args']


class TestGetLaunchCommand:
    """Tests for get_launch_command()."""

    def test_get_launch_command_success(self, terminal_manager, sample_servers, temp_dir):
        """Command generation returns PowerShell script lines."""
        project_path = str(temp_dir)

        with patch('pathlib.Path.home', return_value=temp_dir):
            success, command = terminal_manager.get_launch_command(sample_servers, project_path)

        assert success is True
        assert "Set-Location -LiteralPath" in command
        assert "claude --mcp-config" in command
        assert project_path in command

        config_path = terminal_manager.temp_config_path
        assert config_path is not None and config_path.exists()
        assert str(config_path) in command

        terminal_manager.cleanup_temp_config()

    def test_get_launch_command_requires_enabled_servers(self, terminal_manager, sample_servers, temp_dir):
        """At least one enabled server is required."""
        for server in sample_servers.values():
            server.enabled = False

        success, message = terminal_manager.get_launch_command(sample_servers, str(temp_dir))

        assert success is False
        assert "enable" in message.lower()

    def test_get_launch_command_invalid_project(self, terminal_manager, sample_servers):
        """Project path must exist on disk."""
        success, message = terminal_manager.get_launch_command(sample_servers, "C:\\does-not-exist")

        assert success is False
        assert "does not exist" in message

# Cleanup Tests

class TestCleanupTempConfig:
    """Tests for cleanup_temp_config()"""

    def test_cleanup_success(self, terminal_manager, temp_dir):
        """Test successful temp config cleanup."""
        config_path = temp_dir / "test-config.json"
        config_path.write_text('{"mcpServers": {}}')
        terminal_manager.temp_config_path = config_path

        result = terminal_manager.cleanup_temp_config()

        assert result is True
        assert not config_path.exists()
        assert terminal_manager.temp_config_path is None

    def test_cleanup_no_config(self, terminal_manager):
        """Test cleanup when no temp config exists."""
        terminal_manager.temp_config_path = None

        result = terminal_manager.cleanup_temp_config()

        assert result is True

    def test_cleanup_file_not_found(self, terminal_manager, temp_dir):
        """Test cleanup when file already deleted."""
        config_path = temp_dir / "missing-config.json"
        terminal_manager.temp_config_path = config_path

        result = terminal_manager.cleanup_temp_config()

        assert result is True
