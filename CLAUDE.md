# Claude.md

Project-specific guidance for AI agents and contributors has moved to [`docs/developer-guide.md`](docs/developer-guide.md) and the rest of the documentation suite inside [`docs/`](docs/).

Please consult those files for the latest architecture, testing, and workflow details.
### Task Tracking
**IMPORTANT**: The project uses `TASKS.md` for detailed task tracking. Always:
1. **Read TASKS.md first** when starting a new session
2. **Update task status immediately** after completing each task
3. **Mark tests as completed only after they pass**
4. **Never skip tests** - they must pass before moving to next phase

Current phase progress is tracked in TASKS.md with test counts and blockers.

### Testing Requirements
- **Unit tests required** for all new core functionality
- **Integration tests** for complex workflows (config persistence, etc.)
- Tests must pass 100% before marking phase complete
- Use pytest with verbose output (`-v` flag)

### Code Style
- Follow existing patterns in data models (dataclasses with `to_dict()` / `from_dict()`)
- Use type hints consistently
- Use descriptive variable names (e.g., `config_file` not `cf`)
- Log important operations (config loads, errors) but never log sensitive data (API keys, tokens)

## Critical Implementation Notes

### File Operations
- **Always use atomic writes**: Write to temp file, then `Path.replace()` for rename
- **Create backups before modifying config**: Copy existing file to `.backup` before save
- **Handle locked files**: Use timeout-based retries (default 5 seconds)
- **Deep copy templates**: Use `copy.deepcopy()` when returning pre-loaded templates to prevent mutations

### Windows Compatibility
- Use `Path` objects from `pathlib`, not string concatenation
- Use `cmd /c` prefix for npm commands (better than direct npx on Windows)
- Handle spaces in paths: Quote with double quotes in shell commands
- Environment variables: `%VAR%` syntax (not `$VAR` or `${VAR}`)

### Error Handling
- Use user-friendly error messages from `ERROR_MESSAGES` constant
- Never show stack traces to users
- Log detailed errors for troubleshooting (in log file, not UI)
- Graceful degradation: Offline mode if network fails, fallback to PowerShell if Windows Terminal missing

### Security
- **Never log sensitive data**: API keys, tokens, passwords, environment variables
- **Validate all user inputs**: Use validators for paths, URLs, commands
- **Prevent command injection**: Validate and escape shell commands
- **Secure credential storage**: Use Windows Credential Manager via keyring library (Phase 5)

## MCP Config Generation (Phase 4)

When launching Claude Code, the app will generate a temporary MCP config:
```json
{
  "mcpServers": {
    "server_id": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "npx", "-y", "package-name", "expanded-args"]
    }
  }
}
```

**Launch command patterns (in priority order):**
```bash
# Primary: Windows Terminal with cmd wrapper (avoids UAC popup)
cmd /c start wt -w 0 new-tab -d "C:\path\to\project" -- pwsh -NoExit -Command "Set-Location -LiteralPath \"C:\path\"; & claude-code --mcp-config \"config.json\""

# Fallback: Direct PowerShell (100% reliable, no Windows Terminal features)
pwsh -NoExit -Command "Set-Location -LiteralPath \"C:\path\to\project\"; & claude-code --mcp-config \"config.json\""
```

**Important:** Always wrap `wt` in `cmd /c start` to avoid UAC popup when using WindowsApps alias.

Temp config is cleaned up on app exit (but NOT while Claude Code is running).

## Common Pitfalls

1. **Template Mutation**: Always deep copy `MCP_SERVER_TEMPLATES` before returning - callers may modify
2. **Windows File Locking**: Use retry logic with timeout, Windows locks files more aggressively than Unix
3. **Config Corruption**: Always test backup restoration - it's a critical recovery path
4. **Environment Variable Expansion**: Test with spaces in paths - e.g., `C:\Program Files\`
5. **Datetime Serialization**: Use `.isoformat()` for JSON, `fromisoformat()` when loading
6. **Windows Terminal Launch**: Never use app execution alias or direct WindowsApps wt.exe - use `cmd /c start wt` pattern instead

## External Dependencies

**UI Framework:** Tkinter + ttkbootstrap (modern themes, no separate install)
**System Tray:** pystray (threaded, cross-platform)
**Process Management:** psutil (for Claude Code process detection - Phase 4)
**Async Operations:** aiohttp (for NPM registry validation - Phase 2)
**Windows Integration:** pywin32, keyring (registry, credential manager - Phase 5)

All dependencies in `requirements.txt`.

## Next Development Steps

**Phase 1 (COMPLETE):**
All tasks completed and verified. See TASKS.md Session 4 notes.

**Phase 2 (COMPLETE):**
Server Management UI, NPM validation with caching, offline mode. See TASKS.md Session 5 notes.

**Phase 3 (COMPLETE):**
Profile system with full CRUD, UI components, quick switching (Ctrl+P), tray menu integration. See TASKS.md Session 6 notes.

**Phase 4 (CURRENT - Next Task):**
4.1 Terminal Detection - Implement terminal_manager.py with find_terminal() and check_powershell_version()

**Upcoming Phases:**
- Phase 4: Terminal integration, MCP config generation, Claude Code launch
- Phase 5: Polish, packaging, and PyInstaller build

See `TASKS.md` for complete phase breakdown and detailed task list.

## Reference Documents

- `cc-launcher-prd.md` - Product requirements, user stories, success metrics
- `cc-launcher-tech-spec.md` - Detailed technical specification, API documentation
- `TASKS.md` - Phase-by-phase task tracking with test requirements and blockers