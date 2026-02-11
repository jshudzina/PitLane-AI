---
name: uv-pytest
description: Running pytest in uv monorepos with correct package management. Use when running tests in this codebase - ensures correct uv commands are used instead of bare pytest or pip, handles module import errors with proper sync flags, and manages monorepo package structure correctly.
---

# UV Pytest for Monorepos

Run pytest correctly in uv-managed monorepos with packages in `packages/` directory.

## Core Rules

**ALWAYS follow these rules:**

1. **Use `uv run --directory` for pytest**
   ```bash
   uv run --directory packages/PACKAGE_NAME pytest [args]
   ```
   NEVER use bare `pytest` command.

2. **Sync environment when modules are missing**
   If you encounter import errors or "module not found":
   ```bash
   uv sync --all-packages --all-groups --reinstall
   ```
   Then retry the pytest command.

3. **NEVER use pip**
   This is a uv-managed project. Use `uv` commands only, never `pip install` or similar.

## Common Scenarios

### Run all tests for a specific package
```bash
uv run --directory packages/pitlane-core pytest
```

### Run tests with verbosity
```bash
uv run --directory packages/pitlane-core pytest -v
```

### Run specific test file
```bash
uv run --directory packages/pitlane-core pytest tests/test_session.py
```

### Run specific test function
```bash
uv run --directory packages/pitlane-core pytest tests/test_session.py -k test_workspace_creation
```

### Run with coverage
```bash
uv run --directory packages/pitlane-core pytest --cov
```

## Using the Helper Script

A helper script is available that automatically syncs the environment before running tests:

```bash
./uv-pytest/scripts/run_pytest.sh PACKAGE_NAME [pytest-args]
```

Examples:
```bash
./uv-pytest/scripts/run_pytest.sh pitlane-core -v
./uv-pytest/scripts/run_pytest.sh pitlane-core tests/test_session.py -k test_function
```

The script ensures the environment is synced with `--all-packages --all-groups --reinstall` before running tests.

## Troubleshooting

**"Module not found" or import errors:**
1. Run: `uv sync --all-packages --all-groups --reinstall`
2. Retry the pytest command

**Tests not discovered:**
- Verify you're using `--directory packages/PACKAGE_NAME`
- Check that the package name is correct
- Ensure you're running from the repository root

**Wrong Python or dependencies:**
- NEVER use pip to install packages
- Use `uv sync --all-packages --all-groups --reinstall` to fix environment issues
