# Changelog

All notable changes to Claude Code MCP Manager are documented in this file.

## [2.0.0] - 2025-11-01

### Major Changes
- **Renamed project** from "Claude Code Launcher" to "Claude Code MCP Manager" to better reflect the tool's purpose
- **Cross-platform support** - Now works on Windows, macOS, and Linux
- **Streamlined workflow** - Removed direct launch functionality; tool now generates copy-ready commands only

### Added
- Unix shell support (bash, zsh, sh) for macOS and Linux
- Cross-platform environment variable expansion (supports both `$VAR` and `%VAR%` syntax)
- Platform-aware command generation (PowerShell for Windows, bash/zsh for Unix)
- System tray graceful degradation for unsupported Linux desktop environments
- Comprehensive cross-platform test suite (`tests/test_cross_platform.py`)
- GitHub Actions CI/CD workflow for automated testing on Windows, macOS, and Linux
- Cross-platform testing guide (`docs/testing-cross-platform.md`)
- Community testing request document (`TESTING_NEEDED.md`)
- Platform-specific requirements files (`requirements-windows.txt`, `requirements-unix.txt`)

### Changed
- MCP server templates now use cross-platform `npx` syntax instead of Windows-specific `cmd /c npx`
- Temp file paths now use `tempfile.gettempdir()` for cross-platform compatibility
- Environment variable expansion supports both Windows (`%CD%`) and Unix (`$PWD`) syntax
- UI descriptions adapt based on platform (PowerShell vs terminal references)
- Documentation updated throughout to reflect cross-platform support

### Removed
- Direct Claude Code launching functionality (`launch_claude_code()` method)
- Session management and tracking features
- Launch automation references from documentation
- Windows-only assumptions throughout codebase

### Fixed
- Hardcoded Windows-specific paths replaced with cross-platform alternatives
- MCP templates using Windows-only command syntax
- Environment variable expansion limited to Windows syntax

### Technical
- Added `sys.platform` detection throughout codebase
- Implemented bash/zsh command escaping alongside PowerShell escaping
- Updated terminal detection to support multiple platforms
- Enhanced system tray manager with platform availability checking

## [1.0.0] - Previous Release

### Features
- Windows 10/11 desktop UI
- PowerShell-only fallback for environments where Windows Terminal cannot be used
- Launch workflow generates copyable PowerShell commands via Launch Command Panel
- Profile-based server management
- Server validation with npm registry checks
- Configuration persistence with automatic backups
