"""Terminal Manager - Handles terminal detection and launch command generation."""

import json
import logging
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import psutil

from models.server import MCPServer
from utils.env_expander import expand_env_vars_in_list

logger = logging.getLogger(__name__)


CLAUDE_CLI_COMMAND = "claude"


class TerminalType:
    """Terminal type constants (cross-platform)."""

    # Windows terminals
    WINDOWS_TERMINAL = "wt"
    POWERSHELL_7 = "pwsh"
    POWERSHELL_5 = "powershell"
    CMD = "cmd"
    
    # Unix shells
    BASH = "bash"
    ZSH = "zsh"
    SH = "sh"


class TerminalManager:
    """Manages terminal detection and generation of Claude Code launch commands."""

    def __init__(self) -> None:
        self.temp_config_path: Optional[Path] = None
        self.windows_terminal_path: Optional[str] = None

    def find_terminal(self, force_powershell: bool = False) -> str:
        """Find an available terminal (cross-platform detection)."""
        logger.info("Detecting available terminal (platform=%s, force_powershell=%s)...", 
                    sys.platform, force_powershell)

        if sys.platform == "win32":
            if not force_powershell:
                try:
                    result = subprocess.run(
                        ["cmd", "/c", "where", "wt"],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if result.returncode == 0:
                        wt_path = result.stdout.strip().splitlines()[0] if result.stdout else None
                        if wt_path:
                            self.windows_terminal_path = wt_path
                        else:
                            self.windows_terminal_path = self._resolve_windows_terminal_path()
                        logger.info("Windows Terminal detected")
                        return TerminalType.WINDOWS_TERMINAL
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.debug("Windows Terminal not found via `where wt`")

                wt_path = self._resolve_windows_terminal_path()
                if wt_path:
                    logger.info("Windows Terminal detected at %s", wt_path)
                    return TerminalType.WINDOWS_TERMINAL

            if shutil.which("pwsh"):
                logger.info("PowerShell 7 detected")
                return TerminalType.POWERSHELL_7

            if shutil.which("powershell"):
                logger.info("PowerShell 5 detected")
                return TerminalType.POWERSHELL_5

            logger.info("Falling back to CMD")
            return TerminalType.CMD

        elif sys.platform == "darwin":
            # macOS changed default shell from bash to zsh in Catalina (10.15)
            if shutil.which("zsh"):
                logger.info("zsh detected (macOS)")
                return TerminalType.ZSH
            elif shutil.which("bash"):
                logger.info("bash detected (macOS)")
                return TerminalType.BASH
            elif shutil.which("sh"):
                logger.info("sh detected (macOS)")
                return TerminalType.SH
            else:
                logger.warning("No known shell found on macOS, defaulting to bash")
                return TerminalType.BASH

        elif sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
            if shutil.which("bash"):
                logger.info("bash detected (Linux)")
                return TerminalType.BASH
            elif shutil.which("zsh"):
                logger.info("zsh detected (Linux)")
                return TerminalType.ZSH
            elif shutil.which("sh"):
                logger.info("sh detected (Linux)")
                return TerminalType.SH
            else:
                logger.warning("No known shell found on Linux, defaulting to bash")
                return TerminalType.BASH

        else:
            logger.warning("Unknown platform %s, defaulting to bash", sys.platform)
            return TerminalType.BASH

    def _resolve_windows_terminal_path(self) -> Optional[str]:
        """Resolve and cache the wt executable path if available."""
        if self.windows_terminal_path:
            cached_path = Path(self.windows_terminal_path)
            if cached_path.exists():
                return str(cached_path)

        wt_path = shutil.which("wt.exe") or shutil.which("wt")
        if wt_path:
            self.windows_terminal_path = wt_path
            return wt_path
        return None

    @staticmethod
    def _build_powershell_command(project_path: str, claude_command: str) -> str:
        """Create a PowerShell command that sets the location then launches Claude Code."""
        escaped_path = project_path.replace('"', '`"')
        return f'Set-Location -LiteralPath "{escaped_path}"; & {claude_command}'

    def check_powershell_version(self) -> Optional[str]:
        """Check PowerShell version."""
        try:
            result = subprocess.run(
                ["pwsh", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("PowerShell 7 version: %s", version)
                return version
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            result = subprocess.run(
                ["powershell", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info("PowerShell 5 version: %s", version)
                return version
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        logger.warning("Could not detect PowerShell version")
        return None

    def check_claude_code_running(self) -> Optional[int]:
        """Check if Claude Code is currently running."""
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    process_name = (proc.info["name"] or "").lower()
                    if process_name and ("node" in process_name or "claude" in process_name):
                        cmdline = proc.info.get("cmdline") or []
                        for raw_arg in cmdline:
                            if not raw_arg:
                                continue
                            arg = str(raw_arg).lower()
                            normalized = arg.replace("\\", "/")
                            if (
                                "claude-code" in normalized
                                or normalized.endswith("/claude")
                                or normalized.endswith("/claude.exe")
                                or normalized == "claude"
                            ):
                                pid = proc.info["pid"]
                                logger.info("Claude CLI process found: PID %s", pid)
                                return pid
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as exc:
            logger.error("Error checking for Claude Code process: %s", exc)
        return None

    def kill_claude_code(self, pid: Optional[int] = None) -> bool:
        """Terminate Claude Code process."""
        target_pid = pid or self.check_claude_code_running()
        if target_pid is None:
            logger.info("No Claude Code process to kill")
            return False

        try:
            process = psutil.Process(target_pid)
            logger.info("Terminating Claude Code process: PID %s", target_pid)
            process.terminate()
            try:
                process.wait(timeout=5)
                logger.info("Claude Code process terminated: PID %s", target_pid)
                return True
            except psutil.TimeoutExpired:
                logger.warning("Process did not terminate gracefully, force killing: PID %s", target_pid)
                process.kill()
                process.wait(timeout=2)
                logger.info("Claude Code process force killed: PID %s", target_pid)
                return True
        except psutil.NoSuchProcess:
            logger.info("Process already terminated: PID %s", target_pid)
            return True
        except psutil.AccessDenied:
            logger.error("Access denied when trying to kill process: PID %s", target_pid)
            return False
        except Exception as exc:
            logger.error("Error killing Claude Code process: %s", exc)
            return False

    def generate_mcp_config(
        self,
        servers: Dict[str, MCPServer],
        project_path: str,
    ) -> Path:
        """Generate temporary MCP config file for Claude Code."""
        if not servers:
            raise ValueError("No servers provided for MCP config generation")

        mcp_servers: Dict[str, Dict] = {}
        for server_id, server in servers.items():
            if not server.enabled:
                continue

            if server.type == "stdio":
                args = expand_env_vars_in_list(server.args or [], project_path)
                entry = {
                    "type": "stdio",
                    "command": server.command,
                    "args": args,
                }
                if server.env:
                    entry["env"] = server.env
                mcp_servers[server_id] = entry
            elif server.type == "http":
                entry = {
                    "type": "http",
                    "url": server.url,
                }
                if server.headers:
                    entry["headers"] = server.headers
                mcp_servers[server_id] = entry
            else:
                logger.warning("Unknown server type '%s' for server '%s', skipping", server.type, server_id)

        if not mcp_servers:
            raise ValueError("No enabled servers available for MCP config generation")

        config = {"mcpServers": mcp_servers}

        temp_dir = Path(tempfile.gettempdir())
        temp_dir.mkdir(parents=True, exist_ok=True)

        if self.temp_config_path and self.temp_config_path.exists():
            config_path = self.temp_config_path
        else:
            config_path = temp_dir / f"cc-mcp-{uuid.uuid4().hex[:8]}.json"

        try:
            with config_path.open("w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=2)
            logger.info("MCP config generated: %s", config_path)
            self.temp_config_path = config_path
            return config_path
        except Exception as exc:
            logger.error("Failed to write MCP config file: %s", exc)
            raise IOError(f"Failed to write MCP config: {exc}")

    @staticmethod
    def _escape_for_powershell(value: str) -> str:
        """Escape a string for inclusion inside PowerShell double quotes."""
        return value.replace('"', '`"')

    @staticmethod
    def _escape_for_bash(value: str) -> str:
        """Escape string for bash/zsh double quotes: $ ` " \ and newlines."""
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        value = value.replace('$', '\\$')
        value = value.replace('`', '\\`')
        return value

    def get_launch_command(
        self,
        servers: Dict[str, MCPServer],
        project_path: str,
    ) -> Tuple[bool, str]:
        """Generate a shell command to launch Claude Code (cross-platform)."""
        project_dir = Path(project_path)

        if not project_dir.exists():
            return False, f"Project directory does not exist: {project_path}"

        if not project_dir.is_dir():
            return False, f"Project path is not a directory: {project_path}"

        enabled_servers = {sid: server for sid, server in servers.items() if server.enabled}
        if not enabled_servers:
            return False, "Please enable at least one MCP server to build a launch command"

        try:
            config_path = self.generate_mcp_config(enabled_servers, project_path)
        except Exception as exc:
            logger.error("Failed to prepare MCP configuration: %s", exc)
            return False, str(exc)

        # Detect terminal type to generate platform-appropriate command
        terminal_type = self.find_terminal()

        # Generate command based on platform
        if terminal_type in (TerminalType.POWERSHELL_7, TerminalType.POWERSHELL_5, 
                             TerminalType.WINDOWS_TERMINAL, TerminalType.CMD):
            # Windows PowerShell syntax
            escaped_path = self._escape_for_powershell(str(project_dir))
            escaped_config = self._escape_for_powershell(str(config_path))
            
            command_lines = [
                f'Set-Location -LiteralPath "{escaped_path}"',
                f'{CLAUDE_CLI_COMMAND} --mcp-config "{escaped_config}"',
            ]
            logger.info("Generated PowerShell launch command for manual execution")
            return True, "\n".join(command_lines)

        elif terminal_type in (TerminalType.BASH, TerminalType.ZSH, TerminalType.SH):
            # Unix shell syntax (bash/zsh)
            escaped_path = self._escape_for_bash(str(project_dir))
            escaped_config = self._escape_for_bash(str(config_path))
            
            command = f'cd "{escaped_path}" && {CLAUDE_CLI_COMMAND} --mcp-config "{escaped_config}"'
            logger.info("Generated bash/zsh launch command for manual execution")
            return True, command

        else:
            # Fallback to bash syntax for unknown terminals
            escaped_path = self._escape_for_bash(str(project_dir))
            escaped_config = self._escape_for_bash(str(config_path))
            
            command = f'cd "{escaped_path}" && {CLAUDE_CLI_COMMAND} --mcp-config "{escaped_config}"'
            logger.warning("Unknown terminal type %s, using bash syntax", terminal_type)
            return True, command


    def cleanup_temp_config(self) -> bool:
        """Clean up temporary MCP config file."""
        if not self.temp_config_path:
            return True

        try:
            if self.temp_config_path.exists():
                self.temp_config_path.unlink()
                logger.info("Temp config deleted: %s", self.temp_config_path)
            self.temp_config_path = None
            return True
        except PermissionError:
            logger.warning("Cannot delete temp config (file locked): %s", self.temp_config_path)
            return False
        except Exception as exc:
            logger.error("Error deleting temp config: %s", exc)
            return False

