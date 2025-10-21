# Architecture

The Claude Code Launcher is organised into modular layers that separate configuration management, business logic, UI components, and utilities. The following sections describe each layer and the flow of data through the application.

## High-Level Flow
1. **Startup** – `main.py` initialises logging, configuration management, and the Tkinter event loop.
2. **Configuration load** – `ConfigManager` reads `%USERPROFILE%\.claude\cc-launch.json`, creating defaults and backups if necessary. Preferences, servers, and profiles are materialised into dataclass instances.
3. **UI bootstrap** – `ui.main_window.MainWindow` receives the loaded state plus service objects (`ProfileManager`, `TerminalManager`, `ServerValidator`). The window constructs child components (project selector, profile manager, server list, launch panel) and binds callbacks.
4. **User interaction** – Actions performed in the UI invoke business-logic callbacks (e.g., toggling a server, saving a profile). `ConfigManager.save` writes updates atomically and maintains a backup file. Recent projects and preferences are synchronised on every relevant change.
5. **Launch preparation** – When enough information is present (project path + enabled servers) the `TerminalManager` builds a temporary MCP configuration and returns a PowerShell snippet. The UI exposes the snippet for manual execution.

## Modules

### core/config_manager.py
- Centralised read/write access to the user configuration file.
- Handles atomic writes (`.tmp` file + `Path.replace`), backup creation, and lock-file coordination to avoid concurrent edits.
- Provides migration hooks and ensures pre-loaded MCP server templates exist.

### core/profile_manager.py
- CRUD operations for global profiles using the `ConfigManager` for persistence.
- Updates profile timestamps (`created`, `modified`, `last_used`) and synchronises preferences (`last_profile`).
- Provides convenience methods for querying enabled servers.

### core/terminal_manager.py
- Detects available terminals (Windows Terminal, PowerShell 7, PowerShell 5, CMD) with an optional PowerShell-only fallback.
- Generates temporary MCP configuration files containing only enabled servers and expands environment variables (`%CD%`, `%USERPROFILE%`, `%TEMP%`).
- Builds launch commands and exposes a copy-friendly PowerShell snippet (`get_launch_command`).
- Includes utilities for multi-instance management and direct launching (retained for advanced uses or future UI hooks).

### core/server_validator.py
- Performs command/package validation for MCP servers.
- Checks npm registry availability and global installation status with caching (24-hour JSON cache stored alongside the main configuration).
- Supports forced refresh and integration with the UI’s status indicators.

### models/
- Dataclasses describe persisted structures (`Preferences`, `MCPServer`, `Profile`, `ValidationStatus`).
- Provide `to_dict`/`from_dict` methods to serialise data for `ConfigManager`.

### utils/
- `constants.py` – hosts template server definitions and configuration paths.
- `validators.py` – input validation helpers (paths, URLs, commands) used throughout the UI and config pipeline.
- `env_expander.py` – environment variable expansion utilities used by the terminal manager and server validator.
- `logger.py` – configures rotating log handlers.

### ui/
- `main_window.py` – orchestrates the window layout, binds callbacks, and coordinates persistence.
- `components/` – reusable widgets: project selector, profile manager, server list (with category filter), and launch command panel.
- `dialogs/` – modal windows for adding/editing servers and profiles.

### tests/
- Pytest suite covering configuration, validation, profiles, terminal logic, UI components, and multi-instance behaviour. See [`testing.md`](testing.md) for details.

## Persistence Model
- **Configuration file** – `%USERPROFILE%\.claude\cc-launch.json` stores preferences, servers, and profiles.
- **Backups** – `%USERPROFILE%\.claude\cc-launch.backup` mirrors the configuration on every save after the first.
- **Lock file** – `%USERPROFILE%\.claude\cc-launch.lock` prevents concurrent writers.
- **Validation cache** – `%USERPROFILE%\.claude\cc-validation-cache.json` caches npm lookup results for 24 hours.
- **Logs** – `%USERPROFILE%\.claude\cc-launcher.log` (rotating 3 × 1 MB files) records operational events.
- **Temporary MCP configs** – Created in the OS temp directory and cleaned when new commands are generated or they are superseded.

## Error Handling & Resilience
- Extensive logging around configuration saves, validation errors, and launch preparation.
- Graceful handling of missing directories, permissions issues, or malformed configuration files.
- Validation cache falls back to cached data when offline or when registry checks fail.
- UI surfaces actionable error messages (e.g., invalid project path, missing enabled servers, config write failures).

## Extensibility Considerations
- Unused modules such as `core/project_profile_manager.py` are retained for backward compatibility but effectively disabled by the current configuration pipeline.
- `TerminalManager.launch_claude_code` provides a direct execution path that can be reconnected to future UI controls if automatic launching is reintroduced.
- Documentation of unimplemented features (e.g., MCP import) has been removed; any revival should create dedicated specs within the new `docs/` structure.
