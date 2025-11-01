# Claude Code MCP Manager

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/ScottN-PV/cc-mcp-manager)

**Cross-platform** desktop application for managing [Claude Code](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) MCP servers. Works on Windows, macOS, and Linux.

Stop editing JSON config files by hand. Claude Code MCP Manager gives you a visual interface to configure MCP servers, switch between profiles, and generate ready-to-run shell commands for launching Claude Code with your desired server configuration.

## Platform Support

- ✅ **Windows** 10/11 (PowerShell, Windows Terminal, CMD)
- ✅ **macOS** 10.15+ (zsh, bash)
- ✅ **Linux** (bash, zsh, modern distributions)

## Why Use This?

Managing MCP server configurations manually is tedious and error-prone. Claude Code MCP Manager solves this by:

- **Visual Interface** – No more hand-editing JSON files or wrestling with command-line syntax
- **Multi-Project Support** – Quickly switch between different project configurations
- **Server Validation** – Check if MCP servers are available before launching
- **Profile Management** – Save and recall combinations of servers for different workflows
- **Platform-Native** – Generates commands for PowerShell (Windows) or bash/zsh (macOS/Linux)

## Key Features

- ✅ **Cross-platform** – Works on Windows, macOS, and Linux with platform-native shell detection
- 📁 **Project-aware** – Choose a working directory and maintain a recent-project list
- 🔧 **Server management UI** – Add, edit, delete, validate, and filter MCP servers by category
- 🎭 **Profiles** – Save combinations of enabled servers for quick context switching
- 📋 **Command generation** – Copy ready-to-run shell commands for launching Claude Code
- 💾 **Persistent preferences** – Theme toggle, saved profiles, validation cache, and automatic configuration backups

## Quick Start

### Installation

**All Platforms:**
```bash
pip install -r requirements.txt
```

**Windows** (additional dependencies):
```bash
pip install -r requirements-windows.txt
```

**macOS / Linux** (additional dependencies):
```bash
pip install -r requirements-unix.txt
```

### Running
```bash
python main.py
```

The manager stores configuration files under `~/.claude` (Windows: `%USERPROFILE%\.claude`) and writes logs to `cc-launcher.log` in the same directory.

> **Heads up:** The system tray icon only appears when the desktop environment exposes tray support. On Linux this usually means running under X11/Wayland with a tray applet. When unavailable, the application continues without a tray and automatically disables the feature for future sessions.

## Usage

1. **Select a project directory** – Choose where Claude Code should run
2. **Enable MCP servers** – Check the servers you want to use
3. **Copy the command** – The tool generates a platform-appropriate shell command
4. **Run in your terminal** – Paste and execute the command

The generated command will:
- Change to your project directory
- Launch Claude Code with `--mcp-config` pointing to a temporary configuration file

The manager generates copy-ready commands for you to run manually. This approach is more reliable across platforms and gives you full control over where and how Claude Code launches.

## Requirements

- Python 3.11+
- Tkinter (usually bundled with Python)
- psutil (installed via `requirements.txt`)
- Node.js and npm (for MCP servers)
- Claude Code CLI installed and in PATH

## Documentation

All project documentation lives in [`docs/`](docs/):

- [`product-overview.md`](docs/product-overview.md) – Current product vision, supported workflows, and feature summary.
- [`architecture.md`](docs/architecture.md) – High-level system design, module responsibilities, and persistence model.
- [`ui-guide.md`](docs/ui-guide.md) – Tour of the interface, including the MCP server category filter and launch controls.
- [`developer-guide.md`](docs/developer-guide.md) – Environment setup, coding patterns, testing commands, and contribution guidelines.
- [`testing.md`](docs/testing.md) – Automated and manual test coverage plus execution instructions.
- [`changelog.md`](docs/changelog.md) – Major changes across releases.

## Troubleshooting

### System Tray Icon Not Appearing (Linux)

Some Linux desktop environments (especially GNOME 3.26+) don't support legacy system tray icons. The application will detect this, show a warning once, and continue working normally without the tray icon.

### Permission Errors on macOS

macOS may prompt for folder access permissions when selecting a project directory for the first time. Grant the permission to allow the application to access your project files.

### Command Not Working in Terminal

Ensure that:
- `claude` CLI is installed and in your PATH
- Node.js and npm are installed (required for MCP servers)
- You've copied the entire command from the manager

### Configuration Issues

Configuration is stored in:
- **Windows**: `%USERPROFILE%\.claude\`
- **macOS/Linux**: `~/.claude/`

Check `cc-launcher.log` in this directory for detailed error messages.

## Contributing

Contributions are welcome! Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

Quick start:
1. Install dependencies with `pip install -r requirements.txt` (plus platform-specific requirements)
2. Run the full test suite: `python -m pytest tests/ -v`
3. See [`docs/developer-guide.md`](docs/developer-guide.md) for coding conventions

## License

This project is released under the [MIT License](LICENSE).
