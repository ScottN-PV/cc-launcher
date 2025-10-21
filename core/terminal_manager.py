"""Terminal Manager - Handles terminal detection, Claude Code process management, and launch."""

import json
import logging
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

from models.server import MCPServer
from utils.env_expander import expand_env_vars_in_list

logger = logging.getLogger(__name__)


CLAUDE_CLI_COMMAND = "claude"


class TerminalType:
    """Terminal type constants."""

    WINDOWS_TERMINAL = "wt"
    POWERSHELL_7 = "pwsh"
    POWERSHELL_5 = "powershell"
    CMD = "cmd"


class TerminalManager:
    """Manages terminal operations and Claude Code launching."""

    def __init__(self) -> None:
        self.temp_config_path: Optional[Path] = None
        self.claude_code_pid: Optional[int] = None
        self.active_sessions: List[Dict] = []
        self.windows_terminal_path: Optional[str] = None

    def find_terminal(self, force_powershell: bool = False) -> str:
        """Find an available terminal in priority order: wt -> pwsh -> powershell -> cmd."""
        logger.info("Detecting available terminal (force_powershell=%s)...", force_powershell)

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

        temp_dir = Path.home() / "AppData" / "Local" / "Temp"
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

    def get_launch_command(
        self,
        servers: Dict[str, MCPServer],
        project_path: str,
    ) -> Tuple[bool, str]:
        """Generate a PowerShell command to launch Claude Code without executing it."""
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

        escaped_path = self._escape_for_powershell(str(project_dir))
        escaped_config = self._escape_for_powershell(str(config_path))

        command_lines = [
            f'Set-Location -LiteralPath "{escaped_path}"',
            f'{CLAUDE_CLI_COMMAND} --mcp-config "{escaped_config}"',
        ]

        logger.info("Generated launch command for manual execution")
        return True, "\n".join(command_lines)

    def build_launch_command(
        self,
        terminal_type: str,
        project_path: str,
        config_path: Path,
    ) -> List[str]:
        """Build launch command for Claude Code."""
        project_path_str = str(project_path)
        config_path_str = str(config_path)
        claude_command = f'{CLAUDE_CLI_COMMAND} --mcp-config "{config_path_str}"'

        if terminal_type == TerminalType.WINDOWS_TERMINAL:
            # Use cmd /c start wt to avoid UAC popup with WindowsApps alias
            wt_exec = self._resolve_windows_terminal_path() or "wt"
            if "Program Files\\WindowsApps" in wt_exec:
                wt_exec = "wt"
            ps_command = self._build_powershell_command(project_path_str, claude_command)
            command = [
                "cmd",
                "/c",
                "start",
                wt_exec,
                "-w",
                "0",
                "new-tab",
                "-d",
                project_path_str,
                "--",
                "pwsh",
                "-NoExit",
                "-Command",
                ps_command,
            ]
        elif terminal_type == TerminalType.POWERSHELL_7:
            ps_command = self._build_powershell_command(project_path_str, claude_command)
            command = ["pwsh", "-NoExit", "-Command", ps_command]
        elif terminal_type == TerminalType.POWERSHELL_5:
            ps_command = self._build_powershell_command(project_path_str, claude_command)
            command = ["powershell", "-NoExit", "-Command", ps_command]
        elif terminal_type == TerminalType.CMD:
            command = [
                "cmd",
                "/k",
                f"cd /d \"{project_path_str}\" && {claude_command}",
            ]
        else:
            raise ValueError(f"Unknown terminal type: {terminal_type}")

        logger.info("Built launch command for %s: %s", terminal_type, " ".join(command))
        return command

    def launch_claude_code(
        self,
        servers: Dict[str, MCPServer],
        project_path: str,
        allow_multiple: bool = True,
        force_powershell: bool = False,
    ) -> Tuple[bool, str]:
        """Launch Claude Code with provided MCP servers."""
        project_dir = Path(project_path)
        if not project_dir.exists():
            return False, f"Project directory does not exist: {project_path}"
        if not project_dir.is_dir():
            return False, f"Project path is not a directory: {project_path}"

        existing_pid = self.check_claude_code_running()
        if existing_pid and not allow_multiple:
            return False, (
                f"Claude Code is already running (PID {existing_pid}). "
                "Enable multi-instance mode to launch multiple sessions."
            )

        session_id = uuid.uuid4().hex[:8]
        logger.info("Starting new session: %s", session_id)

        terminal_type = self.find_terminal(force_powershell=force_powershell)
        logger.info("Using terminal: %s", terminal_type)

        try:
            config_path = self.generate_mcp_config(servers, project_path)
        except Exception as exc:
            logger.error("Failed to generate MCP config: %s", exc)
            return False, str(exc)

        try:
            command = self.build_launch_command(terminal_type, project_path, config_path)
            logger.info("Launching Claude Code...")
            process = subprocess.Popen(
                command,
                cwd=project_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            async_terminal = terminal_type == TerminalType.WINDOWS_TERMINAL
            time.sleep(0.5)
            return_code = process.poll()

            if isinstance(return_code, int):
                stderr_output = ""
                if process.stderr:
                    try:
                        stderr_output = process.stderr.read().decode("utf-8", errors="ignore").strip()
                    except Exception as exc:
                        logger.warning("Error reading launch stderr: %s", exc)
                    finally:
                        process.stderr.close()
                if async_terminal and return_code == 0 and not stderr_output:
                    logger.debug(
                        "Launcher command exited immediately after dispatch (expected for Windows Terminal)."
                    )
                else:
                    message = stderr_output or f"launcher exited with code {return_code}"
                    return False, f"Claude Code failed to start: {message}"
            else:
                if process.stderr:
                    try:
                        process.stderr.close()
                    except Exception as exc:
                        logger.debug("Could not close launch stderr pipe: %s", exc)

            logger.info("Waiting for Claude Code process to start...")
            time.sleep(2)

            pid = self.check_claude_code_running()
            if pid:
                self.claude_code_pid = pid
                self.add_session(pid, project_path, config_path, session_id)
                return True, (
                    "Claude Code launched successfully\n"
                    f"Session: {session_id}\n"
                    f"PID: {pid}\n"
                    f"Project: {project_path}"
                )

            logger.warning("Claude Code process not detected after launch")
            return True, f"Claude Code launched (process detection unavailable)\nSession: {session_id}"
        except ValueError as exc:
            logger.error("Validation error: %s", exc)
            return False, str(exc)
        except IOError as exc:
            logger.error("IO error: %s", exc)
            return False, str(exc)
        except Exception as exc:
            logger.error("Unexpected error launching Claude Code: %s", exc)
            return False, f"Unexpected error: {exc}"

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

    def get_active_sessions(self) -> List[Dict]:
        """Get list of active Claude Code sessions."""
        active: List[Dict] = []
        for session in self.active_sessions:
            try:
                proc = psutil.Process(session["pid"])
                if proc.is_running():
                    active.append(session)
                else:
                    logger.debug("Session %s no longer running", session["session_id"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.debug("Session %s process not found", session["session_id"])

        self.active_sessions = active
        return active

    def add_session(self, pid: int, project_path: str, config_path: Path, session_id: str) -> None:
        """Track a new Claude Code session."""
        session = {
            "session_id": session_id,
            "pid": pid,
            "project_path": project_path,
            "config_path": str(config_path),
            "started_at": datetime.now().isoformat(),
        }
        self.active_sessions.append(session)
        logger.info("Session tracked: %s (PID %s)", session_id, pid)

    def kill_session(self, session_id: str) -> Tuple[bool, str]:
        """Kill a specific Claude Code session by ID."""
        for session in list(self.active_sessions):
            if session["session_id"] == session_id:
                success = self.kill_claude_code(session["pid"])
                if success:
                    self.active_sessions.remove(session)
                    try:
                        config_path = Path(session["config_path"])
                        if config_path.exists():
                            config_path.unlink()
                            logger.info("Cleaned up config for session %s", session_id)
                    except Exception as exc:
                        logger.warning("Could not cleanup config for session %s: %s", session_id, exc)
                    return True, f"Session {session_id} terminated"
                return False, f"Failed to terminate session {session_id}"
        return False, f"Session {session_id} not found"

    def cleanup_all_sessions(self) -> None:
        """Clean up all tracked sessions and temp configs."""
        logger.info("Cleaning up all sessions...")
        for session in list(self.active_sessions):
            try:
                config_path = Path(session["config_path"])
                if config_path.exists():
                    config_path.unlink()
                    logger.debug("Deleted temp config: %s", config_path)
            except Exception as exc:
                logger.warning("Could not delete temp config %s: %s", session.get("config_path"), exc)
        self.active_sessions.clear()
        logger.info("All sessions cleaned up")
