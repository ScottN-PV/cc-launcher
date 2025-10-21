# Product Overview

## Vision
Claude Code Launcher streamlines the way Windows developers prepare Claude Code sessions. The application centralises MCP (Model Context Protocol) server management, profile switching, and launch preparation so that teams can focus on building rather than maintaining JSON files or shell scripts.

## Core Workflows

### 1. Configure the project context
- Choose a project directory using the project selector.
- Recently opened paths are retained for quick access.
- Preferences (including theme and last project) persist between sessions.

### 2. Manage MCP servers
- View all configured servers in a sortable list with validation status.
- Add or edit servers via dedicated dialogs that capture command/URL, arguments, environment variables, headers, description, and category information.
- Toggle servers on/off with checkboxes; enabled state is saved automatically.
- Validate servers on demand to confirm npm package availability and local installation.
- Filter the list by category to focus on related tools.

### 3. Maintain profiles
- Combine enabled servers into named profiles for fast context switching.
- Last-used profile loads automatically when the launcher starts.
- Profiles are stored in the global configuration and include timestamps for auditing.

### 4. Generate launch commands
- The launch command panel builds a ready-to-run PowerShell command that sets the working directory and invokes `claude --mcp-config` with a freshly generated temporary MCP file.
- Users can copy the command to the clipboard and execute it in the terminal of their choice.

## Feature Summary
- Windows 10/11 desktop UI built with Tkinter and ttkbootstrap.
- Persistent configuration in `%USERPROFILE%\.claude` with automatic backups.
- Category-aware MCP server list with validation indicators.
- Theme toggle (light/dark) and saved window state.
- Multi-instance awareness in the terminal manager and session tracking utilities for advanced scenarios.
- Comprehensive unit and integration tests covering configuration, validation, profiles, and terminal workflows.

## Supported Use Cases
- Teams running multiple Claude Code projects with distinct MCP requirements.
- Developers who need a reliable way to validate servers before launching Claude Code.
- Users who prefer copying a launch command rather than letting a tool spawn terminals directly.

## Out of Scope
- Project-specific profile storage (legacy functionality replaced by global profiles).
- Automated Claude Code process management beyond generating and copying launch commands.
- MCP server import/update workflows (may be revisited in future releases).
