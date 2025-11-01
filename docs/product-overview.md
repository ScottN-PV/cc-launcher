# Product Overview

## Vision
Claude Code MCP Manager streamlines the way developers on Windows, macOS, and Linux prepare Claude Code sessions. The application centralizes MCP (Model Context Protocol) server management, profile switching, and launch command generation so that teams can focus on building rather than maintaining JSON files or shell scripts.

## Core Workflows

### 1. Configure the project context
- Choose a project directory using the project selector
- Recently opened paths are retained for quick access
- Preferences (including theme and last project) persist between sessions

### 2. Manage MCP servers
- View all configured servers in a sortable list with validation status
- Add or edit servers via dedicated dialogs that capture command/URL, arguments, environment variables, headers, description, and category information
- Toggle servers on/off with checkboxes; enabled state is saved automatically
- Validate servers on demand to confirm npm package availability
- Filter the list by category to focus on related tools

### 3. Maintain profiles
- Combine enabled servers into named profiles for fast context switching
- Last-used profile loads automatically when the manager starts
- Profiles are stored in the global configuration and include timestamps for auditing

### 4. Generate launch commands
- The launch command panel builds a ready-to-run shell command (PowerShell on Windows, bash/zsh on Unix)
- Commands set the working directory and invoke `claude --mcp-config` with a freshly generated temporary MCP file
- Users copy the command to the clipboard and execute it in their preferred terminal

## Feature Summary
- **Cross-platform** – Works on Windows 10/11, macOS 10.15+, and modern Linux distributions
- **Platform-native** – Detects and generates commands for PowerShell, bash, zsh automatically
- Desktop UI built with Tkinter and ttkbootstrap (cross-platform)
- Persistent configuration in `~/.claude` with automatic backups
- Category-aware MCP server list with validation indicators
- Theme toggle (light/dark) and saved window state
- System tray integration (with graceful degradation on unsupported Linux desktop environments)
- Comprehensive unit and integration tests covering configuration, validation, profiles, and cross-platform terminal workflows

## Supported Use Cases
- Teams running multiple Claude Code projects with distinct MCP requirements across different operating systems
- Developers who need a reliable way to validate servers before launching Claude Code
- Users who prefer copying a launch command rather than automatic terminal spawning

## Out of Scope
- Automated Claude Code process management (tool generates commands only)
- Direct terminal launching (commands are copied for manual execution)
- MCP server import/update workflows (may be revisited in future releases)
