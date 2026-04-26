# Code

## Code Structure
- **Root workspace:** `pyproject.toml` — uv monorepo, members under `packages/`
- **pitlane-elo:** `packages/pitlane-elo/src/pitlane_elo/` — ELO rating models, story detection, CLI (`pitlane-elo` entrypoint)
- **pitlane-agent:** `packages/pitlane-agent/src/pitlane_agent/` — AI agent, workspace management, CLI (`pitlane` entrypoint)
- **pitlane-web:** `packages/pitlane-web/` — web interface
- **Docs:** `docs/`, `mkdocs.yml`
- **Scripts:** `scripts/`

## Build
- **Sync all packages:** `uv sync --all-packages`

## Run
- **ELO CLI:** `uv run pitlane-elo --help`
- **Agent CLI:** `uv run pitlane --help`

## Pre-commit Verification
- **Format + lint:** `uv run ruff format . && uv run ruff check . --fix`
- **Unit tests (elo):** `uv run pytest packages/pitlane-elo/tests/ -v`
- **Unit tests (agent):** `uv run pytest packages/pitlane-agent/tests/ -v`
- **All tests:** `uv run pytest -v`

## Dependencies
- **Install/sync:** `uv sync --all-packages`
