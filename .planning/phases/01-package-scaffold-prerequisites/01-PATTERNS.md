# Phase 1: Package Scaffold + Prerequisites — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/pitlane-studio/pyproject.toml` | config | — | `packages/pitlane-web/pyproject.toml` | exact |
| `packages/pitlane-studio/src/pitlane_studio/__init__.py` | config | — | `packages/pitlane-web/src/pitlane_web/__init__.py` | exact |
| `packages/pitlane-studio/src/pitlane_studio/cli.py` | utility (CLI) | request-response | `packages/pitlane-web/src/pitlane_web/cli.py` | exact |
| `packages/pitlane-studio/src/pitlane_studio/app.py` | controller | request-response | `packages/pitlane-web/src/pitlane_web/app.py` | exact |
| `packages/pitlane-studio/src/pitlane_studio/filters.py` | utility | transform | `packages/pitlane-web/src/pitlane_web/filters.py` | role-match |
| `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` | service | CRUD | no direct analog (first SQLAlchemy user) | no-analog |
| `packages/pitlane-elo/src/pitlane_elo/studio_api.py` | service | request-response | `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` (wraps) | role-match |
| `packages/pitlane-studio/tests/conftest.py` | test | — | `packages/pitlane-elo/tests/conftest.py` | role-match |
| `packages/pitlane-studio/tests/test_*.py` | test | — | `packages/pitlane-web/tests/test_security.py` | role-match |
| `pyproject.toml` (root, modify) | config | — | existing root `pyproject.toml` | exact |
| `packages/pitlane-agent/pyproject.toml` (modify) | config | — | existing `packages/pitlane-agent/pyproject.toml` | exact |

---

## Pattern Assignments

### `packages/pitlane-studio/pyproject.toml` (config)

**Analog:** `packages/pitlane-web/pyproject.toml`

**Full template pattern** (lines 1-48 of analog):
```toml
[project]
name = "pitlane-studio"
version = "0.1.0"
description = "F1 journalism co-authoring interface"
readme = "README.md"
requires-python = ">=3.12,<3.15"
license = { text = "Apache-2.0" }
authors = [
    { name = "John Hudzina", email = "pitlaneagent@gmail.com" },
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Programming Language :: Python :: 3 :: Only",
]
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "click>=8.1.0",
    "sqlalchemy>=2.0",
    "bleach>=6.0",
    "pydantic>=2.0",
    "pitlane-elo",
]

[project.scripts]
pitlane-studio = "pitlane_studio.cli:main"

[project.urls]
Homepage = "https://github.com/jshudzina/PitLane-AI"
Repository = "https://github.com/jshudzina/PitLane-AI"
Issues = "https://github.com/jshudzina/PitLane-AI/issues"

[tool.uv.sources]
pitlane-elo = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pitlane_studio"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--strict-markers", "--strict-config", "-ra"]
```

**Key deltas from pitlane-web:**
- `name = "pitlane-studio"` (not `pitlane-web`)
- Entry point: `pitlane-studio = "pitlane_studio.cli:main"`
- No `python-multipart`, no `markdown`, no `slowapi` — those are web-only
- Add `sqlalchemy>=2.0`, `bleach>=6.0`, `pydantic>=2.0`
- Workspace dep is `pitlane-elo` (not `pitlane-agent`)
- Add `[tool.pytest.ini_options]` section (copied from `packages/pitlane-agent/pyproject.toml` lines 56-69)

---

### `packages/pitlane-studio/src/pitlane_studio/__init__.py` (config)

**Analog:** `packages/pitlane-web/src/pitlane_web/__init__.py` (lines 1-3)

**Full file pattern:**
```python
"""PitLane Studio - F1 journalism co-authoring interface."""

__version__ = "0.1.0"
```

---

### `packages/pitlane-studio/src/pitlane_studio/cli.py` (utility, request-response)

**Analog:** `packages/pitlane-web/src/pitlane_web/cli.py`

**Imports pattern** (lines 1-14 of analog):
```python
import os
import sys

import click
import uvicorn
```

**Helper function pattern** (lines 17-24 of analog):
```python
def get_default_reload() -> bool:
    """Determine if reload should be enabled based on environment."""
    env = os.getenv("PITLANE_ENV", "production")
    return env == "development"
```

**Click command pattern** (lines 27-61 of analog):
```python
@click.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
@click.option("--port", default=8001, type=int, show_default=True, help="Port to bind to")
@click.option("--reload/--no-reload", default=None,
              help="Enable auto-reload (default: enabled in development)")
@click.option("--log-level", default="info",
              type=click.Choice(["critical","error","warning","info","debug","trace"],
                                case_sensitive=False),
              show_default=True)
@click.version_option(package_name="pitlane-studio")
def main(host: str, port: int, reload: bool | None, log_level: str) -> None:
    """Run the PitLane Studio co-authoring server."""
```

**Uvicorn run pattern** (lines 114-128 of analog):
```python
    if reload is None:
        reload = get_default_reload()
    try:
        uvicorn.run(
            "pitlane_studio.app:app",   # <-- change from pitlane_web.app:app
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.lower(),
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)
```

**Key delta:** `default=8001` for port (not 8000). Drop `--env` option (not needed for Phase 1). Module string is `"pitlane_studio.app:app"`.

---

### `packages/pitlane-studio/src/pitlane_studio/app.py` (controller, request-response)

**Analog:** `packages/pitlane-web/src/pitlane_web/app.py`

**Imports pattern** (lines 1-46 of analog — keep only what pitlane-studio needs):
```python
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from .filters import register_filters
```

**Logging setup pattern** (lines 50-64 of analog):
```python
_log_level_str = os.getenv("PITLANE_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("pitlane_studio").setLevel(_log_level)

logger = logging.getLogger(__name__)
```

**App setup pattern** (lines 70-88 of analog):
```python
app = FastAPI(title="PitLane Studio", description="F1 journalism co-authoring interface")

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)
register_filters(templates)
```

**Health endpoint pattern** (lines 141-144 of analog):
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Key deltas from pitlane-web app.py:**
- No `slowapi` rate limiting (not needed in Phase 1)
- No session cookie management
- No `StaticFiles` mount (Phase 2+ concern)
- No `pitlane_agent` imports (studio imports `pitlane_elo.studio_api` in Phase 2)
- Phase 1 scope: `app` definition + logging setup + `register_filters(templates)` + `/health` endpoint only

---

### `packages/pitlane-studio/src/pitlane_studio/filters.py` (utility, transform)

**Analog:** `packages/pitlane-web/src/pitlane_web/filters.py`

**Module structure pattern** (lines 1-11 of analog):
```python
"""Jinja2 filters for PitLane Studio."""

import logging
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)
```

**Filter function signature pattern** (lines 14-72 of analog — note: pitlane-studio adds bleach, pitlane-web does not):
```python
# pitlane-web registers filters like this — copy this pattern:
def some_filter(text: str) -> str:
    """Docstring describing the filter."""
    ...
```

**Register function pattern** (lines 172-179 of analog):
```python
def register_filters(templates: Jinja2Templates) -> None:
    """Register custom Jinja2 filters with the templates instance."""
    templates.env.filters["safe_html"] = safe_html
    # add other filters as needed


__all__ = ["safe_html", "register_filters"]
```

**New content for pitlane-studio (no analog in codebase — use RESEARCH.md Pattern 4):**
```python
import bleach
from markupsafe import Markup

_MARKDOWN_TAGS = {
    "a", "abbr", "acronym", "b", "blockquote", "br", "code", "em",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "li", "ol", "p",
    "pre", "s", "strong", "table", "tbody", "td", "th", "thead", "tr", "ul",
}
_MARKDOWN_ATTRS: dict[str, list[str]] = {
    "a": ["href", "title"],
    "abbr": ["title"],
    "acronym": ["title"],
}


def safe_html(text: str) -> Markup:
    """Sanitize HTML and mark safe for Jinja2 rendering."""
    cleaned = bleach.clean(text, tags=_MARKDOWN_TAGS, attributes=_MARKDOWN_ATTRS, strip=True)
    return Markup(cleaned)
```

**Critical:** Return `Markup(cleaned)` — not plain `str` — or Jinja2 will double-escape the output. Use `strip=True` so disallowed tags are removed, not escaped. The `markupsafe` package is a direct dependency of Jinja2, no separate install needed.

---

### `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` (service, CRUD)

**No direct codebase analog** — pitlane-studio is the first SQLAlchemy user in this monorepo. Use RESEARCH.md Pattern 3 directly.

**Import pattern** (all at top — per project feedback rule):
```python
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine
```

**State machine constants:**
```python
_TRANSITIONS: dict[str, str] = {
    "draft": "outline_generated",
    "outline_generated": "outline_approved",
    "outline_approved": "published",
}
_VALID_STATUSES = frozenset(_TRANSITIONS.keys()) | {"published"}
```

**Pydantic model pattern** (aligns with D-04):
```python
class ArticleRecord(BaseModel):
    id: str
    race_year: int
    race_round: int
    angle_id: str | None
    status: str
    created_at: str   # ISO8601 string — SQLite has no native datetime
    updated_at: str
```

**Engine factory with mkdir guard** (critical — see Pitfall 5 in RESEARCH.md):
```python
def get_engine(db_path: Path | None = None) -> Engine:
    path = db_path or Path.home() / ".pitlane" / "studio" / "articles.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")
```

**Table definition (Core, no ORM):**
```python
metadata = MetaData()

articles_table = Table(
    "articles",
    metadata,
    Column("id", String, primary_key=True),
    Column("race_year", Integer, nullable=False),
    Column("race_round", Integer, nullable=False),
    Column("angle_id", String, nullable=True),
    Column("status", String, nullable=False, default="draft"),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)
```

**State transition method pattern** (enforces D-05):
```python
def transition_status(self, article_id: str, target_status: str) -> ArticleRecord:
    """Advance article to target_status. Raises ValueError on illegal transition."""
    with self._engine.begin() as conn:
        row = conn.execute(
            articles_table.select().where(articles_table.c.id == article_id)
        ).fetchone()
        if row is None:
            raise ValueError(f"Article {article_id!r} not found")
        current = row.status
        if _TRANSITIONS.get(current) != target_status:
            raise ValueError(
                f"Invalid transition: {current!r} → {target_status!r}. "
                f"Expected: {_TRANSITIONS.get(current)!r}"
            )
        conn.execute(
            articles_table.update()
            .where(articles_table.c.id == article_id)
            .values(status=target_status, updated_at=datetime.now(UTC).isoformat())
        )
    return self.get(article_id)
```

**Never use:** `Session`, `DeclarativeBase`, `mapped_column`, `session.query()` — these are ORM patterns (D-03 forbids ORM).

---

### `packages/pitlane-elo/src/pitlane_elo/studio_api.py` (service, request-response)

**Analog for module structure:** `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` (lines 1-20 for docstring/import style)

**signals.py import style** (lines 1-20 of analog):
```python
"""Story angle detection signals.
...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from pitlane_elo.data import RaceEntry, get_data_dir, get_race_entries
from pitlane_elo.snapshots import EloSnapshot, get_race_snapshot
```

**detect_stories signature in signals.py** (lines 414-421 of analog — this is what studio_api wraps):
```python
def detect_stories(
    year: int,
    round_num: int,          # <-- internal name is round_num (not round)
    *,
    session_type: str = "R",
    data_dir: Path | None = None,
    trend_lookback: int = 3,
) -> list[StorySignal]:
```

**studio_api.py full content** (adapter pattern — maps public `round` → internal `round_num`):
```python
"""Public studio API for pitlane-elo.

Exposes a stable boundary for pitlane-studio and integration tests.
"""

from __future__ import annotations

from pitlane_elo.stories.signals import StorySignal
from pitlane_elo.stories.signals import detect_stories as _detect_stories


def detect_stories(year: int, round: int) -> list[StorySignal]:  # noqa: A002
    """Detect story signals for a completed race.

    Public studio API. Wraps pitlane_elo.stories.signals.detect_stories
    with the studio-facing signature. Returns an empty list if no ELO
    snapshots exist for the race.

    Args:
        year: Season year (e.g. 2026)
        round: Round number within the season (e.g. 5)

    Returns:
        List of StorySignal instances, sorted by |value| descending.
        Empty list if no ELO snapshots have been built for this race.
    """
    return _detect_stories(year, round)   # positional call — avoids round_num kwarg mismatch


__all__ = ["StorySignal", "detect_stories"]
```

**Critical:** Call `_detect_stories(year, round)` positionally — do NOT use `_detect_stories(year=year, round_num=round)`. The `round` builtin shadow is intentional here; add `# noqa: A002` if ruff is configured with flake8-builtins.

---

### `packages/pitlane-studio/tests/conftest.py` (test)

**Analog:** `packages/pitlane-elo/tests/conftest.py` (fixture-only conftest pattern)

**Module structure pattern** (lines 1-13 of analog):
```python
"""Pytest configuration and shared fixtures for pitlane-studio tests."""

from __future__ import annotations

from pathlib import Path

import pytest
```

**tmp_path-based fixture pattern** (lines 160-163 of analog):
```python
@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a temporary data directory (no files yet)."""
    return tmp_path
```

**pitlane-studio conftest.py content:**
```python
"""Pytest configuration and shared fixtures for pitlane-studio tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pitlane_studio.store.article_store import ArticleStore


@pytest.fixture()
def tmp_store(tmp_path: Path) -> ArticleStore:
    """ArticleStore backed by a temporary SQLite file."""
    return ArticleStore(db_path=tmp_path / "articles.db")
```

**Key:** Use `tmp_path` (pytest built-in) as the base — no need to create the directory manually; `ArticleStore.__init__` calls `path.parent.mkdir(parents=True, exist_ok=True)` internally.

---

### `packages/pitlane-studio/tests/test_article_store.py` (test, CRUD integration)

**Analog:** `packages/pitlane-web/tests/test_security.py` (class-based test organization, lines 1-50)

**Import + class pattern** (lines 1-17 of analog):
```python
"""Integration tests for ArticleStore — uses real SQLite file (no mocks)."""

import uuid
from pathlib import Path

import pytest

from pitlane_studio.store.article_store import ArticleRecord, ArticleStore
```

**Test class pattern:**
```python
class TestArticleStoreLifecycle:
    def test_create_returns_draft(self, tmp_store: ArticleStore): ...
    def test_full_lifecycle(self, tmp_store: ArticleStore): ...
    def test_invalid_transition_skip_raises(self, tmp_store: ArticleStore): ...
    def test_invalid_transition_reverse_raises(self, tmp_store: ArticleStore): ...
    def test_unknown_article_raises(self, tmp_store: ArticleStore): ...
```

**Must cover** (per RESEARCH.md code examples):
- `draft → outline_generated → outline_approved → published` succeeds
- `draft → published` (skip) raises `ValueError`
- `draft → outline_approved` (skip) raises `ValueError`
- `published → draft` (reverse) raises `ValueError`
- `get(unknown_id)` raises or returns None (decide and test explicitly)

---

### `packages/pitlane-studio/tests/test_filters.py` (test, unit)

**Analog:** `packages/pitlane-web/tests/test_security.py` (unit test style)

**Import pattern:**
```python
"""Unit tests for pitlane-studio Jinja2 filters."""

import pytest
from markupsafe import Markup

from pitlane_studio.filters import safe_html
```

**Must cover:**
- XSS attempt is stripped: `safe_html('<script>alert(1)</script>') == Markup('')`
- Unknown block tags are removed: `<div>` content preserved, tag stripped
- Allowed markdown tags pass through: `<p>`, `<h1>`, `<strong>`, `<a href="...">`
- Return type is `Markup` (not plain `str`)

---

### `packages/pitlane-studio/tests/test_studio_api.py` (test, cross-package integration)

**No mock pattern** — this is an integration test with real data (D-02).

**Import pattern:**
```python
"""Cross-package integration test: detect_stories() with real cached data."""

import pytest
from pitlane_elo.data import get_race_entries
from pitlane_elo.studio_api import StorySignal, detect_stories
```

**pytest.skip pattern for missing data** (from RESEARCH.md Pattern 6):
```python
def test_detect_stories_latest_2026_race():
    """Integration test: detect_stories() with real cached data, no mocks."""
    entries = get_race_entries(2026, session_type="R")
    if not entries:
        pytest.skip("No 2026 race data cached — run ELO pipeline first")
    latest_round = max(e["round"] for e in entries)
    signals = detect_stories(year=2026, round=latest_round)
    assert isinstance(signals, list)
    assert all(isinstance(s, StorySignal) for s in signals)
```

**Key:** No `mock.patch`, no `MagicMock`. The `pytest.skip` call correctly distinguishes "no data" (expected in CI without cached Parquet) from "code error."

---

### Root `pyproject.toml` — modification

**Analog:** existing root `pyproject.toml` (lines 22-39)

**Current `[project] dependencies`** (lines 22-25):
```toml
dependencies = [
    "pitlane-agent",
    "pitlane-elo",
    "pitlane-web",
]
```

**Required change — add pitlane-studio:**
```toml
dependencies = [
    "pitlane-agent",
    "pitlane-elo",
    "pitlane-web",
    "pitlane-studio",
]
```

**Current `[tool.uv.sources]`** (lines 36-39):
```toml
[tool.uv.sources]
pitlane-agent = { workspace = true }
pitlane-elo = { workspace = true }
pitlane-web = { workspace = true }
```

**Required change — add pitlane-studio:**
```toml
[tool.uv.sources]
pitlane-agent = { workspace = true }
pitlane-elo = { workspace = true }
pitlane-web = { workspace = true }
pitlane-studio = { workspace = true }
```

**Note:** `[tool.uv.workspace] members = ["packages/*"]` (line 60) auto-discovers the package — but explicit listing in `dependencies` and `sources` maintains consistency with the three existing packages.

---

### `packages/pitlane-agent/pyproject.toml` — modification

**Current dependency** (line 22):
```toml
"claude-agent-sdk>=0.1.40",
```

**Required change — add upper bound pin:**
```toml
"claude-agent-sdk>=0.1.40,<0.2.0",
```

This is the only change to this file. After editing, run `uv lock` to update the lockfile (the installed version 0.1.47 satisfies `<0.2.0` so no reinstallation occurs).

---

## Shared Patterns

### Top-Level Imports (Project Feedback Rule)
**Source:** `packages/pitlane-web/src/pitlane_web/app.py` lines 1-46
**Apply to:** All new `.py` files
```python
# ALL imports at the top of the file — never inside functions, conditionals, or blocks
# Wrong (forbidden):
def main():
    import os   # <-- DO NOT DO THIS

# Correct:
import os
def main(): ...
```

### register_filters Pattern
**Source:** `packages/pitlane-web/src/pitlane_web/filters.py` lines 172-184
**Apply to:** `pitlane_studio/app.py`, `pitlane_studio/filters.py`
```python
def register_filters(templates: Jinja2Templates) -> None:
    """Register custom Jinja2 filters with the templates instance."""
    templates.env.filters["filter_name"] = filter_function

__all__ = ["filter_function", "register_filters"]
```

### FastAPI Health Endpoint
**Source:** `packages/pitlane-web/src/pitlane_web/app.py` lines 141-144
**Apply to:** `pitlane_studio/app.py`
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

### Hatchling Build Backend
**Source:** `packages/pitlane-web/pyproject.toml` lines 42-47
**Apply to:** `packages/pitlane-studio/pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pitlane_studio"]
```

### py.typed Marker
**Source:** Exists in `packages/pitlane-web/src/pitlane_web/` directory (PEP 561)
**Apply to:** `packages/pitlane-studio/src/pitlane_studio/py.typed`
Create as an empty file: `touch packages/pitlane-studio/src/pitlane_studio/py.typed`

### pytest.ini_options
**Source:** `packages/pitlane-agent/pyproject.toml` lines 56-69
**Apply to:** `packages/pitlane-studio/pyproject.toml` — add this section:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--strict-markers", "--strict-config", "-ra"]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` | service | CRUD | No SQLAlchemy Core usage exists anywhere in the monorepo; pitlane-studio is the first consumer. Use RESEARCH.md Pattern 3 directly. |
| `packages/pitlane-studio/src/pitlane_studio/store/__init__.py` | config | — | Sub-package `__init__.py` pattern: empty file or `from .article_store import ArticleStore; __all__ = ["ArticleStore"]` |

---

## Anti-Pattern Registry (copy into plans as guardrails)

| Anti-Pattern | Where Forbidden | Correct Pattern |
|---|---|---|
| `{{ content \| safe }}` in templates | All pitlane-studio templates | `{{ content \| safe_html }}` |
| SQLAlchemy ORM (`Session`, `DeclarativeBase`, `mapped_column`) | `article_store.py` | Core only: `Table`, `Column`, `engine.begin()` |
| Lazy imports inside functions | All files | All imports at top of file |
| `subprocess` / CLI invocation of pitlane-elo | Any pitlane-studio file | `from pitlane_elo.studio_api import detect_stories` |
| `pip install` | Any shell command | `uv add --directory packages/<name> <dep>` |
| Hardcoded round number in integration test | `test_studio_api.py` | `max(e["round"] for e in get_race_entries(2026))` |
| `_detect_stories(year=year, round_num=round)` | `studio_api.py` | `_detect_stories(year, round)` (positional) |
| Skipping `path.parent.mkdir()` before `create_engine` | `article_store.py` | Always call `mkdir(parents=True, exist_ok=True)` first |

---

## Metadata

**Analog search scope:** `packages/pitlane-web/`, `packages/pitlane-elo/`, `packages/pitlane-agent/`, root `pyproject.toml`
**Files scanned:** 11 source files read directly
**Pattern extraction date:** 2026-05-02
