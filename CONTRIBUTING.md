# Contributing to Claude Code MCP Manager

Thank you for your interest in contributing to Claude Code MCP Manager! This guide will help you get started.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cc-mcp-manager.git
   cd cc-mcp-manager
   ```
3. **Set up your development environment**:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-windows.txt
   
   # macOS / Linux
   source .venv/bin/activate
   pip install -r requirements.txt -r requirements-unix.txt
   ```

## Development Workflow

### Before Making Changes

1. Create a new branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Ensure the existing tests pass:
   ```bash
   python -m pytest tests/ -v
   ```

### While Working

- Follow the coding guidelines in [`docs/developer-guide.md`](docs/developer-guide.md)
- Write clear, descriptive commit messages
- Add tests for new features or bug fixes
- Keep commits focused and atomic

### Code Style

- Use Python 3.11+ features appropriately
- Prefer dataclasses for data structures with `to_dict`/`from_dict` methods
- Use `pathlib.Path` for file operations
- Use `logging` module instead of print statements
- Keep UI code in `ui/` and business logic in `core/`
- Follow PEP 8 naming conventions

### Testing

- Add tests for new functionality in the `tests/` directory
- Ensure all tests pass before submitting:
  ```bash
  python -m pytest tests/ -v
  ```
- Aim for high test coverage of business logic

### Documentation

- Update relevant documentation in `docs/` when adding features
- Update `README.md` if installation or usage changes
- Add entries to `docs/changelog.md` for user-facing changes
- Keep docstrings clear and up-to-date

## Submitting Changes

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. **Open a Pull Request** on GitHub with:
   - A clear title describing the change
   - A detailed description of what changed and why
   - Reference to any related issues
   - Screenshots for UI changes

### Pull Request Checklist

- [ ] All tests pass (`python -m pytest tests/ -v`)
- [ ] New tests added for new features/fixes
- [ ] Documentation updated as needed
- [ ] Changelog updated for user-facing changes
- [ ] No debug code or commented-out code left in
- [ ] No personal paths or credentials in code

## Reporting Issues

When reporting bugs, please include:
- Operating system and version (Windows 10/11, macOS version, Linux distribution)
- Python version
- Steps to reproduce the issue
- Expected vs actual behavior
- Relevant log output from `~/.claude/cc-launcher.log`

## Platform Support

The project now supports Windows, macOS, and Linux. When contributing:
- Test on your platform if possible
- Use platform-agnostic code when feasible
- Use `sys.platform` checks for platform-specific behavior
- Update documentation to reflect platform differences

## Feature Requests

Feature requests are welcome! Please:
- Check existing issues and [`docs/backlog.md`](docs/backlog.md) first
- Describe the use case and proposed solution
- Explain how it benefits users

## Code Review Process

- Maintainers will review pull requests as time permits
- Address review feedback by pushing new commits to your branch
- Once approved, your PR will be merged

## Questions?

- Check the documentation in the `docs/` folder
- Open an issue for questions about the project
- Review existing issues and pull requests

## License

By contributing, you agree that your contributions will be licensed under the same MIT License that covers the project.

Thank you for contributing!

