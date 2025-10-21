# Testing Guide

## Automated Tests

The project uses Pytest for automated coverage. As of 2025-10-02 the suite contains **190 passing tests** with **3 documented skips** (async npm validation edge cases).

### Running Tests
```bash
python -m pytest tests/ -v
```

To execute a subset, target the desired module:
```bash
python -m pytest tests/test_config_manager.py -v
python -m pytest tests/test_terminal_manager.py -k "launch" -v
```

### Key Suites
- `tests/test_config_manager.py` – Persistence, atomic saves, lock handling.
- `tests/test_config_integration.py` – End-to-end read/write validation.
- `tests/test_profile_manager.py` – Profile CRUD and preference synchronisation.
- `tests/test_server_validator.py` – npm validation logic (three async tests skipped by design).
- `tests/test_terminal_manager.py` & `tests/test_terminal_manager_multi_instance.py` – Terminal detection, command generation, session tracking.
- `tests/test_main_window_persistence.py` – UI persistence regression coverage (project path, theme, category filter consistency).
- `tests/test_server_list_filter.py` – Verifies the MCP server category filter.

## Manual Testing

Use the `manual_test_launch.py` script to preview launch commands without starting terminals:
```bash
python manual_test_launch.py
```

The script reports detected terminals, shows the generated MCP config, and prompts before executing anything.

## Reporting Results
- Record significant changes in [`docs/changelog.md`](changelog.md).
- Update this document if new suites or manual procedures are introduced.

## Continuous Validation Ideas
- Consider integrating the test suite with CI (e.g., GitHub Actions) to ensure consistent results across environments.
- Monitor the three skipped async tests; if aiohttp mocking becomes easier to maintain, revisit them for full coverage.
