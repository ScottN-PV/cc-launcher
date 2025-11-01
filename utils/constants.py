"""Constants and pre-loaded MCP server templates for Claude Code MCP Manager."""

from pathlib import Path
from typing import Dict
from models.server import MCPServer


# Paths
USER_HOME = Path.home()
CONFIG_DIR = USER_HOME / ".claude"
CONFIG_FILE = CONFIG_DIR / "cc-launch.json"
VALIDATION_CACHE_FILE = CONFIG_DIR / "cc-validation-cache.json"
BACKUP_FILE = CONFIG_DIR / "cc-launch.backup"
LOCK_FILE = CONFIG_DIR / "cc-launch.lock"
LOG_FILE = CONFIG_DIR / "cc-launcher.log"

# Application
APP_NAME = "Claude Code MCP Manager"
APP_VERSION = "1.0.0"
CONFIG_VERSION = "1.0.0"  # Configuration file format version
WINDOW_MIN_WIDTH = 600
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_WIDTH = 800
WINDOW_DEFAULT_HEIGHT = 700

# Validation
VALIDATION_CACHE_HOURS = 24
NPM_REGISTRY_URL = "https://registry.npmjs.org"
VALIDATION_TIMEOUT_SECONDS = 5

# Pre-loaded MCP Server Templates (Cross-Platform)
MCP_SERVER_TEMPLATES: Dict[str, MCPServer] = {
    "filesystem": MCPServer(
        id="filesystem",
        type="stdio",
        enabled=False,
        is_template=True,
        order=1,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."],
        env={},
        description="Access local file system for reading and writing files",
        category="core"
    ),
    "ref": MCPServer(
        id="ref",
        type="stdio",
        enabled=False,
        is_template=True,
        order=2,
        command="npx",
        args=["-y", "@ref-mcp/server"],
        env={},
        description="Search documentation and references online",
        category="documentation"
    ),
    "supabase": MCPServer(
        id="supabase",
        type="stdio",
        enabled=False,
        is_template=True,
        order=3,
        command="npx",
        args=["-y", "@supabase/mcp-server"],
        env={},
        description="Supabase database integration and management",
        category="database"
    ),
    "lucide-icons": MCPServer(
        id="lucide-icons",
        type="stdio",
        enabled=False,
        is_template=True,
        order=4,
        command="npx",
        args=["-y", "lucide-icons-mcp"],
        env={},
        description="Search and use Lucide icon library",
        category="ui"
    ),
    "shadcn": MCPServer(
        id="shadcn",
        type="stdio",
        enabled=False,
        is_template=True,
        order=5,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-shadcn"],
        env={},
        description="shadcn/ui component library integration",
        category="ui"
    ),
    "sequential-thinking": MCPServer(
        id="sequential-thinking",
        type="stdio",
        enabled=False,
        is_template=True,
        order=6,
        command="npx",
        args=["-y", "@sequential-thinking/mcp"],
        env={},
        description="Advanced reasoning and problem-solving tool",
        category="reasoning"
    ),
    "motion": MCPServer(
        id="motion",
        type="stdio",
        enabled=False,
        is_template=True,
        order=7,
        command="npx",
        args=["-y", "@motion/mcp-server"],
        env={},
        description="Motion animation library for web interfaces",
        category="animation"
    )
}

# Error Messages (User-friendly)
ERROR_MESSAGES = {
    "CONFIG_NOT_FOUND": "Configuration file not found. Creating new configuration with default servers...",
    "CONFIG_CORRUPTED": "Configuration file corrupted. Restoring from backup...",
    "CONFIG_LOCKED": "Configuration file is locked. Retrying...",
    "BACKUP_RESTORED": "Configuration restored from backup successfully.",
    "TERMINAL_NOT_FOUND": "Windows Terminal not found. Using PowerShell fallback. Install Windows Terminal from Microsoft Store for best experience.",
    "POWERSHELL_OLD": "PowerShell 5.1 detected. Consider upgrading to PowerShell 7 for better performance.",
    "NPM_CHECK_FAILED": "Unable to verify server online. Using cached validation data.",
    "NPM_NOT_INSTALLED": "Server package not installed locally. It will be downloaded when Claude Code starts.",
    "CLAUDE_CODE_RUNNING": "Claude Code is already running (PID: {pid}). Kill existing session before launching?",
    "LAUNCH_FAILED": "Failed to start Claude Code. Check that 'claude' CLI is installed and in PATH. See logs for details.",
    "MCP_CONFIG_FAILED": "Failed to generate MCP configuration. Check server settings.",
    "NETWORK_OFFLINE": "Unable to reach NPM registry. Running in offline mode with cached data.",
    "INVALID_PATH": "Invalid project path. Please select a valid directory.",
    "NO_SERVERS_SELECTED": "No servers selected. Please enable at least one server before launching.",
    "SERVER_VALIDATION_FAILED": "Some servers failed validation. Launch anyway?",
}

# UI Theme colors (for ttkbootstrap)
THEMES = {
    "dark": "darkly",
    "light": "cosmo"
}