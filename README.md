# Claude Code Launcher

Claude Code Launcher is a Windows desktop companion for managing Claude Code MCP servers. It provides a Tkinter/ttkbootstrap interface for configuring servers, switching profiles, and launching Claude Code with validated settings—without editing JSON by hand.

## Highlights
- **Project-aware configuration** – Choose a working directory and maintain a recent-project list.
- **Server management UI** – Add, edit, delete, validate, and filter MCP servers by category.
- **Profiles** – Persist combinations of enabled servers for quick context switching.
- **Launch automation** – Generate MCP configs, detect terminals, and run Claude Code with multi-instance support.
- **Persistent preferences** – Theme toggle, saved profiles, validation cache, and configuration backups.

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

The launcher stores configuration files under `%USERPROFILE%\.claude` and writes logs to `cc-launcher.log` in the same directory.

## Documentation

All project documentation lives in [`docs/`](docs/):

- [`product-overview.md`](docs/product-overview.md) – Current product vision, supported workflows, and feature summary.
- [`architecture.md`](docs/architecture.md) – High-level system design, module responsibilities, and persistence model.
- [`ui-guide.md`](docs/ui-guide.md) – Tour of the interface, including the MCP server category filter and launch controls.
- [`developer-guide.md`](docs/developer-guide.md) – Environment setup, coding patterns, testing commands, and contribution guidelines.
- [`testing.md`](docs/testing.md) – Automated and manual test coverage plus execution instructions.
- [`changelog.md`](docs/changelog.md) – Major changes across releases.

## Contributing

1. Install dependencies with `pip install -r requirements.txt`.
2. Run the full test suite via `python -m pytest tests/ -v` before submitting changes.
3. See [`developer-guide.md`](docs/developer-guide.md) for coding conventions and release procedures.

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE) if present or consult the project maintainer for details.
