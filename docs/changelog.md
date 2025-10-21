# Changelog

All notable changes to Claude Code Launcher are documented here. Dates use YYYY-MM-DD.

## 2025-10-02
- Added category filter to the MCP server list, enabling focused views of related servers.
- Hardened configuration persistence: recent projects, project/profile mappings, and theme preference updates now save reliably during shutdown.
- Introduced regression tests for the server list filter and main window persistence logic.

## 2025-09-30
- Delivered multi-instance Claude Code support with session tracking utilities in `TerminalManager`.
- Added PowerShell-only fallback for environments where Windows Terminal cannot be used.
- Reworked the launch workflow to generate copyable PowerShell commands via the Launch Command Panel.
- Expanded automated test coverage (project profile logic, multi-instance behaviour) and provided `manual_test_launch.py` for terminal diagnostics.

## 2025-09-15
- Initial release featuring project selection, MCP server management (add/edit/delete/validate), profile storage, theme toggle, and configuration persistence backed by atomic saves and backups.
