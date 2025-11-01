# Developer Guide

## Environment Setup
1. Install Python 3.11+ (the project currently runs on Python 3.13 in CI/local testing).
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-windows.txt
   
   # macOS / Linux
   source .venv/bin/activate
   pip install -r requirements.txt -r requirements-unix.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

Configuration files are stored in `~/.claude` (Windows: `%USERPROFILE%\.claude`). The first run seeds default MCP templates and preferences.

## Project Structure
- `core/` – Business logic (configuration, profiles, terminal, validation).
- `models/` – Dataclasses for persisted entities.
- `utils/` – Shared helpers (constants, validators, env expansion, logging).
- `ui/` – Tkinter widgets, components, and dialogs.
- `tests/` – Pytest suite covering the modules above.
- `docs/` – Documentation suite (overview, architecture, testing, changelog).

See [`architecture.md`](architecture.md) for a deeper component breakdown.

## Coding Guidelines
- Prefer dataclasses for persisted structures and include `to_dict`/`from_dict` helpers.
- Use the logging module (`logging.getLogger(__name__)`) instead of print statements.
- Avoid duplicate logic between UI and business layers—UI should delegate persistence to `ConfigManager` and `ProfileManager`.
- When manipulating file paths, rely on `pathlib.Path` and `ConfigManager` helpers to maintain cross-platform compatibility.
- Keep UI styling consistent with ttkbootstrap themes; avoid inline colours unless necessary.

## Testing
- Run the full suite before submitting changes:
  ```bash
  python -m pytest tests/ -v
  ```
- For a targeted run:
  ```bash
  python -m pytest tests/test_config_manager.py -v
  ```
- Tests cover configuration, profiles, server validation, terminal detection, and cross-platform behaviors. See [`testing.md`](testing.md) for current coverage details.

## Logging & Diagnostics
- Logs write to `~/.claude/cc-launcher.log` (Windows: `%USERPROFILE%\.claude\cc-launcher.log`) with rotation (3 × 1 MB).
- When touching configuration or terminal code, ensure log messages remain descriptive to help future debugging.

## Documentation Workflow
- Update `README.md` when features or onboarding steps change.
- Store detailed reference material in `docs/` to keep the repository root uncluttered.
- When adding major features, append a summary to [`changelog.md`](changelog.md).
- Remove or archive outdated notes to avoid confusing future contributors and AI assistants.

## Release Checklist
1. Ensure `python -m pytest tests/ -v` passes with no unexpected skips or failures.
2. Verify that configuration changes persist across restarts and that the launch command appears for an enabled server set.
3. Update documentation and changelog entries to reflect user-facing changes.
4. Confirm that stray temporary files are not committed.

## Issue Tracking & Backlog
- Use [`docs/backlog.md`](backlog.md) to record open ideas that are not yet scheduled.
- Remove completed items promptly to keep the backlog actionable.
