# Coding Conventions

Python monorepo with consistent Ruff-enforced style across all three packages.

**Analysis Date:** 2026-05-02

## Naming Patterns

**Files:**
- `snake_case` for all Python source files: `agent.py`, `cli_stories.py`, `ratings_store.py`, `van_kesteren.py`
- CLI sub-commands split into dedicated files: `cli_analyze.py`, `cli_fetch.py`, `cli_stories.py` in `pitlane-agent`
- Sub-packages use single flat name: `pitlane_agent`, `pitlane_elo`, `pitlane_web`

**Classes:**
- `PascalCase`: `F1Agent`, `RatingModel`, `EloSnapshot`, `EloConfig`, `StorySignal`
- Abstract base classes named as roles: `RatingModel` (not `AbstractRatingModel`)
- TypedDicts named descriptively in `PascalCase`: `LiftAndCoastZone`, `DriverInfo`, `RaceSummaryStats`

**Functions and methods:**
- `snake_case` throughout: `get_rating()`, `process_race()`, `predict_win_probabilities()`
- Private helpers prefixed with `_`: `_filter_entries()`, `_resolve_retention_years()`, `_write_race_parquet()`
- Module-level private names prefixed with `_`: `_RACE_DDL`, `_agent_cache`, `_tracing_enabled`

**Variables:**
- `snake_case` for all variables
- Constants in `UPPER_SNAKE_CASE`: `DEFAULT_STATE_RETENTION_YEARS`, `PACKAGE_DIR`, `SESSION_COOKIE_NAME`

**Type annotations:**
- `from __future__ import annotations` used in 31 of 87 source files (primarily `pitlane-elo`)
- `pitlane-agent` source files import `from __future__ import annotations` inconsistently — some have it, most do not
- TypedDicts preferred over dataclasses for data-shaped dicts passed between layers
- `dataclass` used for value objects: `TemporalContext`, `RaceWeekendInfo` in `pitlane_agent/temporal/context.py`
- Abstract base classes use `ABC` + `@abstractmethod`: `pitlane_elo/ratings/base.py`

## Code Style

**Formatter:**
- Ruff format (configured in root `pyproject.toml`)
- Quote style: double quotes (`"`)
- Indent style: spaces (4-space indent)
- Line length: 120 characters

**Linting:**
- Ruff lint with the following rule sets:
  - `E`, `W` — pycodestyle errors and warnings
  - `F` — pyflakes
  - `I` — isort (import sorting)
  - `N` — pep8-naming
  - `UP` — pyupgrade (modern Python idioms)
  - `B` — flake8-bugbear
  - `C4` — flake8-comprehensions
  - `SIM` — flake8-simplify
- `ignore = []` — no rules suppressed at the config level
- `type: ignore` comments used in scripts and Bayesian code where FastF1/pandas types are imprecise (acceptable suppression pattern)

**Target Python version:** 3.12 minimum, tested on 3.12, 3.13, 3.14

## Import Organization

Ruff isort (`I` rule set) enforces import order. Observed pattern:

**Order:**
1. `from __future__ import annotations` (when present — first line)
2. Standard library imports
3. Third-party imports (numpy, pandas, duckdb, fastapi, etc.)
4. Local package imports (`from pitlane_agent.xxx import ...`, `from pitlane_elo.xxx import ...`)
5. Relative imports (`from . import tracing`)

**No path aliases** — all imports use full package names.

**Rule:** Imports must always be at the top of the file — never inside functions or conditional blocks.

## Error Handling

**Patterns:**
- Exceptions are raised with descriptive messages; no custom exception hierarchy observed
- `type: ignore` used narrowly for FastF1/pandas interop where types cannot be statically proved (scripts and Bayesian layer)
- `monkeypatch` used in tests to suppress external side effects rather than wrapping in try/except in production code

## Logging

**Framework:** Standard library `logging`

**Pattern:**
```python
import logging
logger = logging.getLogger(__name__)
```
Used in `pitlane_agent/agent.py` and other agent-layer modules. Not consistently present in all modules — some utility modules omit loggers and use direct return values.

## Comments

**Module docstrings:** All source files have a module-level docstring describing purpose (1–3 sentences).

**Class docstrings:** Present on all public classes.

**Function/method docstrings:** Present on all public functions with `Args:` and `Returns:` sections in Google style where arguments are non-obvious.

**Section separators:** Long files use `# ---...--- \n # Section Name \n # ---...---` to divide logical sections (consistent in conftest files and large modules like `pitlane_elo/snapshots.py`).

**Inline comments:** Used sparingly to explain "why", not "what".

## Function Design

**Size:** Functions are generally focused; large analysis commands are split into helper functions within the same module.

**Parameters:** Keyword-only arguments used for boolean flags (e.g., `*, dnf_category: str = "none"`).

**Return values:** Functions return typed values or `TypedDict` instances; CLI commands write side effects to files and print summaries.

## Module Design

**Exports:** `__init__.py` files are kept minimal — most modules export nothing from `__init__` and callers import directly from submodules.

**Barrel files:** Not used — explicit import paths are required.

**Package structure:** `src/` layout used for all three packages (`src/pitlane_agent/`, `src/pitlane_elo/`, `src/pitlane_web/`). Build backend is `hatchling`.

## Commit Style

Conventional Commits enforced by pre-commit hook (`conventional-pre-commit`). Format: `type(scope): message` (e.g., `fix: ...`, `feat: ...`, `chore: ...`, `test: ...`).

## Pre-commit Hooks

Configured in `/.pre-commit-config.yaml`:
- `ruff` with `--fix` (auto-fix on commit)
- `ruff-format`
- `check-yaml`, `check-toml`, `check-json`
- `end-of-file-fixer`, `trailing-whitespace`
- `check-added-large-files` (max 500 KB)
- `check-merge-conflict`, `detect-private-key`
- `conventional-pre-commit` (commit-msg stage)

---

*Convention analysis: 2026-05-02*
