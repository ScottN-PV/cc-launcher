# UI Guide

This guide introduces the main areas of the Claude Code Launcher interface and explains how to accomplish common tasks.

## Layout Overview

The main window is divided into five sections from top to bottom:

1. **Header** – Displays the application title and a theme toggle button (☀ for dark theme, 🌙 for light theme). The selected theme persists across sessions.
2. **Project Selector** – Choose the working directory for the next Claude Code session. Recently used paths appear in the dropdown, and validation icons (✓/✗) confirm the selection. Changes are saved immediately.
3. **Profile Manager** – A combobox lists saved profiles. Buttons allow creating, saving, or deleting profiles. Metadata beneath the controls summarises server counts and timestamps.
4. **MCP Server List** – Shows available MCP servers with checkbox toggles, descriptions, validation status, and contextual actions.
5. **Launch Command Panel** – Generates a copy-ready PowerShell script that sets the working directory and invokes `claude --mcp-config` with the currently enabled servers.

## MCP Server List

### Toolbar Actions
- **Add Server** – Opens the server dialog to capture ID, type (stdio/http), command/URL, arguments, environment variables, headers, description, and category. Newly created servers appear enabled and can be toggled afterward from the list.
- **Delete Server** – Removes the selected server (confirmation required). Disabled when nothing is selected.
- **Category Filter** – A combobox positioned between Delete and Validate All. Choose a category to display only matching servers or select “All Categories” to reset the view.
- **Validate All** – Forces revalidation of every server, refreshing npm/cache data and status icons.

### Status Icons
- **Checkbox column** – Indicates whether a server is enabled (✅) or disabled (⬜). Click to toggle.
- **Status column** – Displays validation results: success, cached data, npm warnings, or error messages.

### Context Menu
Right-click any server to edit, delete, or validate it individually.

## Profiles
- Profiles store the enabled server IDs. When you save or switch profiles, the server list updates immediately.
- The last-used profile is restored on launch. Profile operations automatically persist through the configuration manager.

## Launch Command Panel
- When a valid project path and at least one enabled server are present, the panel displays two PowerShell lines:
  1. `Set-Location -LiteralPath "…"`
  2. `claude --mcp-config "…"`
- Use **Copy Command** to place the script on the clipboard. Run it in PowerShell to start Claude Code with the selected servers.
- If prerequisites are missing (invalid path or no enabled servers) the panel explains how to resolve the issue.

## Validation Feedback
- Validation operations run in the background and update the list once complete.
- Errors appear both in the status column and as message boxes with actionable descriptions.

## System Tray Integration
- Closing the window triggers minimise-to-tray behaviour if the preference is enabled. The tray icon menu provides quick access to reopen the window or exit the application.
- The tray menu also exposes recently used profiles for fast switching.

## Preferences & Persistence
- Preferences such as theme, last project path, last profile, and recent projects are stored automatically in the global configuration file.
- The application performs atomic writes and maintains a backup to prevent data loss.

## Manual Testing
- For manual terminal verification, run `python manual_test_launch.py` and follow the prompts. This tool demonstrates command generation without spawning processes.
