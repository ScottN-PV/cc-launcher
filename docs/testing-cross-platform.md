# Cross-Platform Testing Guide

This document provides guidance for testing Claude Code MCP Manager across Windows, macOS, and Linux platforms.

## Automated Testing

### Running Tests Locally

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_terminal_manager.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### CI/CD Testing

The project uses GitHub Actions to automatically test on:
- **Windows**: windows-latest
- **macOS**: macos-latest  
- **Linux**: ubuntu-latest

With Python versions: 3.11, 3.12

See `.github/workflows/cross-platform-tests.yml` for the full configuration.

## Manual Testing Checklist

When testing on a new platform, verify these key areas:

### Installation
- [ ] Virtual environment creation works
- [ ] All dependencies install without errors
- [ ] Application launches without import errors

### Terminal Detection
- [ ] Correct shell/terminal is detected for the platform
  - Windows: PowerShell 7, PowerShell 5, or CMD
  - macOS: zsh or bash
  - Linux: bash or zsh
- [ ] Terminal detection logs appear in `~/.claude/cc-launcher.log`

### Command Generation
- [ ] Select a project directory
- [ ] Enable at least one MCP server
- [ ] Generated command uses correct syntax for platform:
  - Windows: `Set-Location -LiteralPath "..."` then `claude --mcp-config "..."`
  - Unix: `cd "..." && claude --mcp-config "..."`
- [ ] Command can be copied to clipboard
- [ ] Command executes successfully in native terminal
- [ ] Application remembers the last selected profile and enabled servers without auto-launching terminals

### Environment Variable Expansion
- [ ] Windows: `%CD%`, `%USERPROFILE%`, `%TEMP%` expand correctly
- [ ] Unix: `$PWD`, `$HOME`, `$TMPDIR` expand correctly
- [ ] Mixed syntax doesn't break (Windows still supports `$VAR` for compatibility)

### MCP Configuration
- [ ] Temp config file created in platform temp directory
- [ ] Config file contains correct JSON structure
- [ ] Server args use cross-platform syntax (`npx` not `cmd /c npx`)

### System Tray
- [ ] Windows: Tray icon appears and works
- [ ] macOS: Menu bar icon appears and works  
- [ ] Linux: Check multiple desktop environments:
  - [ ] KDE: Should work
  - [ ] XFCE: Should work
  - [ ] GNOME: May not work (graceful degradation expected)
  - [ ] If tray fails, app should show a warning once, disable the preference, and continue normally without the icon

### UI Elements
- [ ] Application window appears correctly
- [ ] Theme toggle (light/dark) works
- [ ] File dialogs use platform-native appearance
- [ ] Fonts render correctly
- [ ] No layout issues specific to platform

### File Operations
- [ ] Config directory created at `~/.claude/`
- [ ] Config file read/write works
- [ ] Backup file creation works
- [ ] Log file writes correctly
- [ ] File permissions are appropriate

### Edge Cases
- [ ] Paths with spaces work correctly
- [ ] Paths with special characters work
- [ ] Long paths don't cause issues
- [ ] Unicode in project paths works

## Platform-Specific Issues to Watch For

### Windows
- UAC prompts when accessing certain directories
- Different path separators (`\` vs `/`)
- Case-insensitive filesystem
- Windows Terminal vs PowerShell differences

### macOS
- Gatekeeper warnings on first run
- Permission prompts for folder access
- Case-sensitive vs case-insensitive filesystems (varies)
- zsh default shell since Catalina (10.15)

### Linux
- Many desktop environment variations
- Different system tray implementations
- Package manager differences (npm installation)
- Wayland vs X11 display servers
- Variety of default shells

## Testing Without Access to a Platform

If you don't have access to a specific platform:

### Use Docker for Linux Testing

```bash
# Build test image
docker build -f Dockerfile.test -t cc-manager-test .

# Run tests
docker run --rm cc-manager-test
```

### Use GitHub Actions

- Fork the repository
- Push your changes
- GitHub Actions will automatically test on all platforms
- Review the logs for any platform-specific failures

### Request Community Testing

See `TESTING_NEEDED.md` for guidelines on requesting help from community testers.

## Reporting Platform-Specific Bugs

When reporting a bug that's specific to one platform:

1. **Title**: Prefix with platform, e.g., "[macOS] System tray icon not appearing"
2. **Environment Details**:
   - OS name and version
   - Python version (`python --version`)
   - Shell/terminal being used
   - Desktop environment (Linux only)
3. **Logs**: Attach relevant portions of `~/.claude/cc-launcher.log`
4. **Steps**: Clear reproduction steps
5. **Expected vs Actual**: What you expected to happen vs what actually happened

## Adding Platform-Specific Tests

When adding new platform-specific functionality:

1. **Mock `sys.platform`** in tests:
   ```python
   from unittest.mock import patch
   
   @patch('sys.platform', 'darwin')
   def test_macos_behavior(self):
       # Test code here
   ```

2. **Test all platform branches**:
   - Windows (`win32`)
   - macOS (`darwin`)
   - Linux (`linux`)

3. **Use platform-agnostic assertions** when possible

4. **Document platform assumptions** in test docstrings

## Performance Testing

Test on each platform:
- Startup time
- UI responsiveness
- Config file load time
- Command generation speed

Expected benchmarks:
- Startup: < 2 seconds
- Config load: < 100ms
- Command generation: < 50ms

## Accessibility Testing

Ensure keyboard navigation works on all platforms:
- Tab through controls
- Enter/Space activate buttons
- Escape closes dialogs
- Platform-specific shortcuts (Ctrl vs Cmd)

