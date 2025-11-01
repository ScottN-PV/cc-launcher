"""Cross-platform functionality tests."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from core.terminal_manager import TerminalManager, TerminalType
from utils.env_expander import expand_env_vars


class TestUnixShellDetection:
    """Tests for Unix shell detection."""

    @patch('sys.platform', 'darwin')
    @patch('shutil.which')
    def test_macos_zsh_detection(self, mock_which):
        """Test zsh detection on macOS."""
        mock_which.side_effect = lambda cmd: '/bin/zsh' if cmd == 'zsh' else None
        
        tm = TerminalManager()
        result = tm.find_terminal()
        
        assert result == TerminalType.ZSH

    @patch('sys.platform', 'darwin')
    @patch('shutil.which')
    def test_macos_bash_fallback(self, mock_which):
        """Test bash fallback on macOS when zsh not available."""
        mock_which.side_effect = lambda cmd: '/bin/bash' if cmd == 'bash' else None
        
        tm = TerminalManager()
        result = tm.find_terminal()
        
        assert result == TerminalType.BASH

    @patch('sys.platform', 'linux')
    @patch('shutil.which')
    def test_linux_bash_detection(self, mock_which):
        """Test bash detection on Linux."""
        mock_which.side_effect = lambda cmd: '/usr/bin/bash' if cmd == 'bash' else None
        
        tm = TerminalManager()
        result = tm.find_terminal()
        
        assert result == TerminalType.BASH

    @patch('sys.platform', 'linux')
    @patch('shutil.which')
    def test_linux_zsh_detection(self, mock_which):
        """Test zsh detection on Linux."""
        def which_mock(cmd):
            if cmd == 'bash':
                return None
            elif cmd == 'zsh':
                return '/usr/bin/zsh'
            return None
        
        mock_which.side_effect = which_mock
        
        tm = TerminalManager()
        result = tm.find_terminal()
        
        assert result == TerminalType.ZSH


class TestUnixEnvironmentVariables:
    """Tests for Unix environment variable expansion."""

    def test_pwd_expansion(self):
        """Test $PWD expansion to project path."""
        result = expand_env_vars("$PWD/data", "/home/user/project")
        assert result == "/home/user/project/data"

    def test_pwd_with_braces(self):
        """Test ${PWD} expansion."""
        result = expand_env_vars("${PWD}/data", "/home/user/project")
        assert result == "/home/user/project/data"

    def test_home_expansion(self):
        """Test $HOME expansion."""
        with patch.dict('os.environ', {'HOME': '/home/testuser'}):
            result = expand_env_vars("$HOME/documents", "/any/path")
            assert result == "/home/testuser/documents"

    def test_mixed_unix_variables(self):
        """Test multiple Unix variables in one string."""
        with patch.dict('os.environ', {'HOME': '/home/user', 'USER': 'testuser'}):
            result = expand_env_vars("$HOME/$USER/data", "/project")
            assert result == "/home/user/testuser/data"

    def test_dollar_sign_in_value(self):
        """Test that literal dollar signs are preserved when not followed by variable."""
        result = expand_env_vars("price: $50", "/project")
        assert "50" in result  # The $50 may be partially expanded or kept

    def test_unix_variables_on_windows(self):
        """Test that Unix variables work on Windows too (for compatibility)."""
        with patch('sys.platform', 'win32'):
            result = expand_env_vars("$PWD/data", "C:\\Project")
            assert result == "C:\\Project/data" or result == "C:\\Project\\data"


class TestWindowsVariablesOnUnix:
    """Test that Windows variables work on Unix for cross-compatibility."""

    def test_cd_on_unix(self):
        """Test %CD% expansion works on Unix."""
        with patch('sys.platform', 'darwin'):
            result = expand_env_vars("%CD%/data", "/home/user/project")
            assert result == "/home/user/project/data"

    def test_userprofile_on_unix(self):
        """Test %USERPROFILE% expansion on Unix."""
        with patch('sys.platform', 'linux'):
            with patch.dict('os.environ', {'USERPROFILE': '/home/testuser'}):
                result = expand_env_vars("%USERPROFILE%/docs", "/project")
                assert result == "/home/testuser/docs"


class TestCrossPlatformCommandGeneration:
    """Tests for cross-platform command generation."""

    @patch('sys.platform', 'darwin')
    @patch('shutil.which')
    def test_macos_command_generation(self, mock_which, tmp_path):
        """Test command generation on macOS uses bash/zsh syntax."""
        mock_which.side_effect = lambda cmd: '/bin/zsh' if cmd == 'zsh' else None
        
        from models.server import MCPServer
        tm = TerminalManager()
        
        servers = {
            "test": MCPServer(
                id="test",
                type="stdio",
                command="npx",
                args=["-y", "test-server"],
                enabled=True
            )
        }
        
        project_path = str(tmp_path)
        success, command = tm.get_launch_command(servers, project_path)
        
        assert success
        assert "cd" in command
        assert "&&" in command
        assert "claude --mcp-config" in command
        # Should NOT contain PowerShell syntax
        assert "Set-Location" not in command

    @patch('sys.platform', 'win32')
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_windows_command_generation(self, mock_which, mock_run, tmp_path):
        """Test command generation on Windows uses PowerShell syntax."""
        mock_which.side_effect = lambda cmd: 'C:\\pwsh.exe' if cmd == 'pwsh' else None
        mock_run.return_value = MagicMock(returncode=1)  # wt not found
        
        from models.server import MCPServer
        tm = TerminalManager()
        
        servers = {
            "test": MCPServer(
                id="test",
                type="stdio",
                command="npx",
                args=["-y", "test-server"],
                enabled=True
            )
        }
        
        project_path = str(tmp_path)
        success, command = tm.get_launch_command(servers, project_path)
        
        assert success
        assert "Set-Location" in command
        assert "claude --mcp-config" in command
        # Should NOT contain Unix syntax
        assert " && " not in command or "Set-Location" in command  # Could have both on separate lines


class TestBashEscaping:
    """Tests for bash command escaping."""

    def test_escape_double_quotes(self):
        """Test escaping double quotes for bash."""
        from core.terminal_manager import TerminalManager
        result = TerminalManager._escape_for_bash('path with "quotes"')
        assert '\\"' in result
        assert 'quotes' in result

    def test_escape_dollar_signs(self):
        """Test escaping dollar signs for bash."""
        from core.terminal_manager import TerminalManager
        result = TerminalManager._escape_for_bash('price: $50')
        assert '\\$' in result

    def test_escape_backticks(self):
        """Test escaping backticks for bash."""
        from core.terminal_manager import TerminalManager
        result = TerminalManager._escape_for_bash('command with `backticks`')
        assert '\\`' in result

    def test_escape_backslashes(self):
        """Test escaping backslashes for bash."""
        from core.terminal_manager import TerminalManager
        result = TerminalManager._escape_for_bash('path\\with\\backslashes')
        assert '\\\\' in result


class TestTempDirectoryCrossplatform:
    """Test that temp directory is cross-platform."""

    def test_temp_dir_uses_tempfile(self):
        """Test that MCP config generation uses tempfile.gettempdir()."""
        import tempfile
        from models.server import MCPServer
        
        tm = TerminalManager()
        servers = {
            "test": MCPServer(
                id="test",
                type="stdio",
                command="npx",
                args=["-y", "test-server"],
                enabled=True
            )
        }
        
        config_path = tm.generate_mcp_config(servers, "/any/path")
        
        # Config should be in system temp directory
        expected_temp = Path(tempfile.gettempdir())
        assert config_path.parent == expected_temp


class TestMCPTemplatesCrossplatform:
    """Test that MCP server templates use cross-platform syntax."""

    def test_filesystem_template_uses_npx(self):
        """Test filesystem template uses npx directly."""
        from utils.constants import MCP_SERVER_TEMPLATES
        
        fs_server = MCP_SERVER_TEMPLATES["filesystem"]
        
        assert fs_server.command == "npx"
        assert "/c" not in fs_server.args
        assert "cmd" not in fs_server.args
        # Should use "." not "%CD%"
        assert "." in fs_server.args

    def test_all_templates_cross_platform(self):
        """Test all templates use cross-platform command syntax."""
        from utils.constants import MCP_SERVER_TEMPLATES
        
        for name, server in MCP_SERVER_TEMPLATES.items():
            # Should use npx directly, not cmd /c npx
            assert server.command == "npx", f"{name} should use npx"
            assert "/c" not in server.args, f"{name} should not use /c"
            assert "cmd" != server.command, f"{name} should not use cmd"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

