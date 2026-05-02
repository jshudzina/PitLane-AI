# Phase 1: Package Scaffold + Prerequisites — Research

**Researched:** 2026-05-02
**Domain:** uv workspace packaging, SQLAlchemy Core, bleach/Jinja2, pitlane-elo studio_api
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `detect_stories(year: int, round: int) -> list[StorySignal]` — accepts year and round as plain ints; returns the existing `StorySignal` dataclass from `pitlane_elo.stories.signals` as-is. No new boundary type in Phase 1; Phase 2's AngleService handles transformation.
- **D-02:** Cross-package integration test uses the latest available 2026 race (most recently cached round). Not hardcoded to a specific round number.
- **D-03:** Use SQLAlchemy Core (not ORM) for database access. No declarative models; just connection pooling and typed query builder.
- **D-04:** Article records are represented in Python as Pydantic BaseModel instances.
- **D-05:** Invalid state transitions (e.g. `draft → published`, skipping `outline_generated` or `outline_approved`) raise `ValueError`. Strict state machine.

### Claude's Discretion

- Package structure (src layout, `__init__.py` contents, module names beyond what's specified) follows the pitlane-web pattern exactly.
- SQLAlchemy connection setup (engine creation, context manager pattern) — standard approach is fine.
- Jinja2 + bleach integration in pitlane-studio templates — bleach.clean() wrapping approach is Claude's call; PKG-03 only requires the wrapping exists and is unit-tested.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PKG-01 | Developer can install pitlane-studio as a uv workspace package alongside pitlane-agent and pitlane-elo (pyproject.toml, FastAPI skeleton, uvicorn entry point, `pitlane-studio` CLI) | uv workspace pattern from pitlane-web; FastAPI/click/uvicorn already locked versions in uv.lock |
| PKG-02 | pitlane-elo exposes a `studio_api` interface module with a cross-package integration test that calls `detect_stories()` with real data — not a mock | `detect_stories()` already fully implemented in `pitlane_elo.stories.signals`; studio_api is a thin re-export + parameter name adapter |
| PKG-03 | claude-agent-sdk is pinned to `<0.2.0` and any Jinja2 `| safe` template outputs are sanitized with `bleach.clean()` | sdk pinning is one-line change in pitlane-agent/pyproject.toml; bleach 6.3.0 in uv.lock already |
| PKG-04 | User can persist article drafts across sessions via SQLite at `~/.pitlane/studio/articles.db` with status machine (`draft` → `outline_generated` → `outline_approved` → `published`) | SQLAlchemy Core 2.0 patterns confirmed; SQLAlchemy is a net-new dep not currently in uv.lock |
</phase_requirements>

---

## Summary

Phase 1 creates the `pitlane-studio` package from scratch following the `pitlane-web` pattern, resolves two inherited blockers (SDK pin and XSS sanitization), and adds the `studio_api` surface to `pitlane-elo`. The work decomposes cleanly into five independent streams: package scaffold, studio_api interface, SDK pin, bleach sanitization, and SQLite article store.

The most important discovery from codebase inspection: **`detect_stories()` is already fully implemented in `pitlane_elo.stories.signals`** with the exact signal types (hot_streak, slump, surprise_over, surprise_under, teammate_shift) and `StorySignal` dataclass that Phase 2 needs. The `studio_api` module is a thin adapter — it re-exports `detect_stories` and `StorySignal` with the public-facing signature `detect_stories(year: int, round: int)`, mapping the `round` kwarg to `round_num` internally.

A critical finding: **SQLAlchemy is NOT currently in the uv.lock file** — it is not a transitive dep of FastAPI in this monorepo configuration. It must be added as an explicit dependency to `pitlane-studio`'s `pyproject.toml`. Additionally, **bleach 6.3.0 IS already in uv.lock** (as a transitive dep of jupyter in pitlane-elo notebooks), so it requires no net-new package resolution — only an explicit `bleach>=6.0` dep in pitlane-studio's pyproject.toml.

**Primary recommendation:** Implement in five waves — (1) package scaffold + CLI, (2) studio_api re-export in pitlane-elo, (3) SDK pin, (4) bleach Jinja2 filter, (5) ArticleStore. All waves except (2) are confined to `packages/pitlane-studio/`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Package registration | Build system (uv workspace) | — | pyproject.toml + root workspace config |
| FastAPI skeleton + health endpoint | API / Backend | — | uvicorn process, port 8001 |
| CLI entry point | Backend (CLI layer) | — | click + uvicorn.run() pattern |
| ArticleStore (SQLite) | Backend / Storage | — | SQLAlchemy Core at `~/.pitlane/studio/articles.db` |
| State machine validation | Backend / Storage | — | ArticleStore.transition_status() raises ValueError |
| studio_api interface | pitlane-elo package | pitlane-studio (consumer) | detect_stories() lives in pitlane-elo; studio_api is the published boundary |
| bleach sanitization | Backend (template filter) | — | Jinja2 filter in pitlane-studio templates only |
| SDK version pin | Build system | — | Upper bound in pitlane-agent/pyproject.toml |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.128.0 | API framework | Already in monorepo; locked version [VERIFIED: uv.lock] |
| uvicorn[standard] | current in lock | ASGI server | Already in monorepo [VERIFIED: uv.lock] |
| click | >=8.1.0 | CLI entry point | Already used in pitlane-web, pitlane-agent, pitlane-elo [VERIFIED: uv.lock] |
| sqlalchemy | >=2.0 | SQLite Core access | Latest 2.0.49 [VERIFIED: PyPI]; net-new explicit dep |
| pydantic | >=2.0 | Article record models | FastAPI transitive dep; v2 already in use [VERIFIED: uv.lock, version 2.12.5] |
| bleach | >=6.0 | Jinja2 HTML sanitization | 6.3.0 already in uv.lock (notebook transitive) [VERIFIED: uv.lock]; explicit dep needed |
| jinja2 | >=3.1 | Template rendering | Already in pitlane-web; same dep [VERIFIED: uv.lock] |
| hatchling | build backend | Wheel build | Used by all three existing packages [VERIFIED: pyproject.toml files] |

### Dependency Note: Versions

```
SQLAlchemy latest: 2.0.49 [VERIFIED: PyPI 2026-05-02]
bleach latest: 6.3.0 [VERIFIED: PyPI, already in uv.lock]
pydantic in lock: 2.12.5 [VERIFIED: uv.lock]
fastapi in lock: 0.128.0 [VERIFIED: uv.lock]
claude-agent-sdk in lock: 0.1.47 [VERIFIED: uv.lock], current pin: >=0.1.40 (needs <0.2.0 added)
```

### Installation

```bash
# Add to packages/pitlane-studio/pyproject.toml dependencies
uv add --directory packages/pitlane-studio sqlalchemy>=2.0
uv add --directory packages/pitlane-studio bleach>=6.0
# bleach already in lock, this makes it an explicit dep
```

---

## Architecture Patterns

### System Architecture Diagram

```
uv sync --all-packages
    └── installs packages/pitlane-studio/ as workspace member
              │
    pitlane-studio CLI (click)
              │
    uvicorn.run("pitlane_studio.app:app", port=8001)
              │
    FastAPI app
         ├── GET /health → {"status": "ok"}
         └── (Phase 2/3 routes)
              │
    ArticleStore (SQLAlchemy Core)
         └── ~/.pitlane/studio/articles.db
              │  Tables: articles (id, race_year, race_round, angle_id, status, ...)
              │
    pitlane_elo.studio_api  (cross-package import)
         └── detect_stories(year, round) → list[StorySignal]
                   │
         pitlane_elo.stories.signals.detect_stories(year, round_num, ...)
                   │
         ELO snapshots (Parquet) + race_entries (Parquet)
```

### Recommended Project Structure

```
packages/pitlane-studio/
├── pyproject.toml           # uv workspace member, deps: fastapi, uvicorn, sqlalchemy, bleach, jinja2, click, pitlane-elo
├── src/
│   └── pitlane_studio/
│       ├── __init__.py      # __version__ = "0.1.0"
│       ├── py.typed         # PEP 561 marker (matches pitlane-web pattern)
│       ├── app.py           # FastAPI app with /health endpoint
│       ├── cli.py           # click command → uvicorn.run on port 8001
│       ├── filters.py       # Jinja2 filters including safe_html (bleach.clean wrapper)
│       └── store/
│           ├── __init__.py
│           └── article_store.py   # ArticleStore: SQLAlchemy Core, Pydantic models
└── tests/
    ├── __init__.py
    ├── conftest.py          # tmp_path fixture, test DB path
    ├── test_article_store.py  # integration: real SQLite file
    ├── test_filters.py        # unit: bleach.clean sanitization
    └── test_studio_api.py     # cross-package integration: detect_stories() with real data
```

For pitlane-elo, add one file:

```
packages/pitlane-elo/src/pitlane_elo/
└── studio_api.py            # re-exports detect_stories, StorySignal with public signature
```

### Pattern 1: uv Workspace Package Registration

**What:** Add pitlane-studio as a workspace member with cross-package deps declared via `[tool.uv.sources]`.
**When to use:** Any new package in the monorepo.

```toml
# packages/pitlane-studio/pyproject.toml
[project]
name = "pitlane-studio"
version = "0.1.0"
requires-python = ">=3.12,<3.15"
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

[tool.uv.sources]
pitlane-elo = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pitlane_studio"]
```

The root `pyproject.toml` already has `[tool.uv.workspace] members = ["packages/*"]` — no change needed there. The root `[tool.uv.sources]` block will need `pitlane-studio = { workspace = true }` added to the root package's sources, and `"pitlane-studio"` added to root's `dependencies` list if desired, but this is optional. [VERIFIED: root pyproject.toml inspection]

### Pattern 2: studio_api Interface Module

**What:** A thin public boundary in pitlane-elo that re-exports `detect_stories` with the public API signature `(year: int, round: int)` mapping to the internal `round_num` parameter.

**Critical finding:** `detect_stories` in `signals.py` uses `round_num` as the positional parameter name. The public API per D-01 must accept `round` as the parameter name. The studio_api wrapper handles this adapter.

```python
# packages/pitlane-elo/src/pitlane_elo/studio_api.py
# Source: codebase inspection of signals.py
from pitlane_elo.stories.signals import StorySignal
from pitlane_elo.stories.signals import detect_stories as _detect_stories


def detect_stories(year: int, round: int) -> list[StorySignal]:
    """Public studio API: detect story signals for a completed race.

    Wraps pitlane_elo.stories.signals.detect_stories with the studio-facing
    signature. Returns an empty list if no ELO snapshots exist for the race.
    """
    return _detect_stories(year, round)


__all__ = ["StorySignal", "detect_stories"]
```

### Pattern 3: SQLAlchemy Core — ArticleStore

**What:** Single-table SQLite store using SQLAlchemy Core 2.0 (engine, MetaData, Table, typed queries). Pydantic BaseModel for Python-level representation.

```python
# Source: [CITED: docs.sqlalchemy.org/en/20/core/connections.html]
# Source: [CITED: docs.sqlalchemy.org/en/20/core/metadata.html]
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, DateTime, text
from sqlalchemy.engine import Engine
from pydantic import BaseModel
from datetime import datetime, UTC

# Valid status transitions — strict state machine (D-05)
_TRANSITIONS: dict[str, str] = {
    "draft": "outline_generated",
    "outline_generated": "outline_approved",
    "outline_approved": "published",
}

_VALID_STATUSES = frozenset(_TRANSITIONS.keys()) | {"published"}


class ArticleRecord(BaseModel):
    id: str
    race_year: int
    race_round: int
    angle_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime


def get_engine(db_path: Path | None = None) -> Engine:
    path = db_path or Path.home() / ".pitlane" / "studio" / "articles.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


metadata = MetaData()

articles_table = Table(
    "articles",
    metadata,
    Column("id", String, primary_key=True),
    Column("race_year", Integer, nullable=False),
    Column("race_round", Integer, nullable=False),
    Column("angle_id", String, nullable=True),
    Column("status", String, nullable=False, default="draft"),
    Column("created_at", String, nullable=False),  # ISO8601 string — SQLite has no native datetime
    Column("updated_at", String, nullable=False),
)


class ArticleStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._engine = get_engine(db_path)
        metadata.create_all(self._engine)

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

**SQLite datetime note:** SQLite has no native datetime type. Store as ISO8601 strings (`datetime.now(UTC).isoformat()`). [ASSUMED — standard SQLite practice; SQLAlchemy also supports `DateTime` type with native coercion, but string is simpler for Core-only usage]

### Pattern 4: bleach.clean() as Jinja2 Filter

**What:** Register a `safe_html` filter in pitlane-studio's Jinja2 environment that sanitizes HTML before rendering. Templates use `{{ content | safe_html }}` instead of `{{ content | safe }}`.

**bleach.clean() signature:** [VERIFIED: bleach 6.3.0 source via PyPI]
```
bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
             protocols=ALLOWED_PROTOCOLS, strip=False, strip_comments=True)
```

**Default ALLOWED_TAGS** is conservative: `{a, abbr, acronym, b, blockquote, code, em, i, li, ol, strong, ul}`. For markdown-to-HTML output, you need to extend it with block elements. [VERIFIED: bleach.readthedocs.io/en/latest/clean.html]

```python
# Source: [CITED: bleach.readthedocs.io/en/latest/clean.html]
import bleach
from markupsafe import Markup
from fastapi.templating import Jinja2Templates

# Tags appropriate for markdown-to-HTML output
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


def register_filters(templates: Jinja2Templates) -> None:
    templates.env.filters["safe_html"] = safe_html
```

**Important:** Return `Markup(cleaned)` so Jinja2 does not double-escape the output. The `strip=True` argument removes disallowed tags entirely rather than escaping them. [CITED: bleach.readthedocs.io/en/latest/clean.html]

**Scope:** This filter is registered ONLY in `pitlane_studio.filters`. Existing `pitlane_web` templates that use `| safe` are explicitly out of scope (confirmed in CONTEXT.md canonical_refs). [VERIFIED: CONTEXT.md]

### Pattern 5: claude-agent-sdk Upper Bound Pin

**What:** Add `<0.2.0` upper bound to the `claude-agent-sdk` dependency in `packages/pitlane-agent/pyproject.toml`.

**Current state:** `"claude-agent-sdk>=0.1.40"`, locked at `0.1.47` in `uv.lock`. [VERIFIED: pitlane-agent/pyproject.toml, uv.lock]

```toml
# packages/pitlane-agent/pyproject.toml — change this one line
dependencies = [
    "claude-agent-sdk>=0.1.40,<0.2.0",
    # ... rest unchanged
]
```

After editing, run `uv lock` to update the lockfile. This is a metadata-only change; the installed version (0.1.47) satisfies the new constraint so no package reinstallation is needed. [VERIFIED: version 0.1.47 < 0.2.0]

### Pattern 6: Integration Test — Finding Latest 2026 Race

**What:** The integration test for `detect_stories()` must use the latest cached 2026 race dynamically (D-02), not a hardcoded round number.

**Approach using `get_race_entries()`:** [VERIFIED: pitlane_elo/data.py inspection]

```python
# Source: codebase inspection of pitlane_elo.data.get_race_entries
from pitlane_elo.data import get_race_entries

def get_latest_cached_round(year: int) -> int | None:
    """Return the highest round number with data for the given year, or None."""
    entries = get_race_entries(year, session_type="R")
    if not entries:
        return None
    return max(e["round"] for e in entries)
```

```python
# tests/test_studio_api.py (integration — no mocks)
import pytest
from pitlane_elo.data import get_race_entries
from pitlane_elo.studio_api import StorySignal, detect_stories


def test_detect_stories_latest_2026_race():
    """Integration test: detect_stories() with real cached data, no mocks."""
    entries = get_race_entries(2026, session_type="R")
    if not entries:
        pytest.skip("No 2026 race data cached — run ELO pipeline first")
    latest_round = max(e["round"] for e in entries)
    signals = detect_stories(year=2026, round=latest_round)
    assert isinstance(signals, list)
    assert all(isinstance(s, StorySignal) for s in signals)
    # May be empty if ELO snapshots not built; that's a data issue, not a code issue
    # The integration contract is: function is callable and returns list[StorySignal]
```

**Note on test assertion:** `detect_stories()` returns empty list if no ELO snapshots exist for the race (see `signals.py` line: `if not race_snapshots: return []`). The `pytest.skip` approach correctly distinguishes "no data" from "code error". The Phase 1 success criterion requires the test PASSES — if 2026 data is cached, signals should be non-empty; if not, skip is the correct outcome. [VERIFIED: signals.py inspection]

### Anti-Patterns to Avoid

- **Do not use `| safe` in pitlane-studio templates** — always use `| safe_html` (the bleach-wrapped filter). The `| safe` marker in Jinja2 bypasses all escaping with no sanitization.
- **Do not use SQLAlchemy ORM** — DeclarativeBase, mapped_column, Session are all ORM. Use Table, Column, MetaData, engine.begin()/connect() only (D-03).
- **Do not lazy-import** — `from pitlane_elo.studio_api import detect_stories` must be at top of file, not inside a function body (project feedback rule: imports at top always).
- **Do not use `pip` directly** — all installs via `uv add --directory packages/<name>`.
- **Do not touch pitlane-web templates** — bleach scope is pitlane-studio only.
- **Do not hardcode a round number** in the integration test — use `get_race_entries(2026)` to find max round dynamically (D-02).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML sanitization | Custom regex stripping | `bleach.clean()` | Regex misses nested tags, attribute injection, encoded entities |
| Connection pooling | Manual `sqlite3` connection management | SQLAlchemy Core `create_engine` | Connection pool, thread safety, proper transaction handling |
| Type coercion for DB records | Manual dict-to-object conversion | Pydantic BaseModel `.model_validate()` | Validation, type coercion, serialization all handled |
| uv workspace dep resolution | Manual path manipulation | `[tool.uv.sources] pitlane-elo = { workspace = true }` | uv handles editable install, version resolution, and lock |

---

## Common Pitfalls

### Pitfall 1: `round` Parameter Name Mismatch
**What goes wrong:** `signals.py` uses `round_num` as the positional parameter. The studio_api contract (D-01) requires `round`. Calling `studio_api.detect_stories(year=2026, round=5)` and having that pass through correctly requires the wrapper to map `round` → `round_num`.
**Why it happens:** Python keyword argument names are part of the public API; `round` is also a Python builtin which `signals.py` carefully avoids.
**How to avoid:** The `studio_api.detect_stories` wrapper uses `round` as its parameter and calls `_detect_stories(year, round)` (positional), not `_detect_stories(year=year, round_num=round)`.
**Warning signs:** `TypeError: detect_stories() got an unexpected keyword argument 'round'` if you try to call the underlying function with `round=`.

### Pitfall 2: SQLAlchemy Is Not a Current Transitive Dep
**What goes wrong:** The CONTEXT.md note says "SQLAlchemy is already a FastAPI transitive dep (via pitlane-web's FastAPI dep)." This is incorrect — SQLAlchemy is NOT in the current uv.lock. Adding pitlane-studio without explicitly listing `sqlalchemy>=2.0` in its dependencies will cause an import error at runtime.
**Why it happens:** FastAPI does not require SQLAlchemy; it's often co-used but not a transitive dep. This monorepo's fastapi install does not pull it in. [VERIFIED: uv.lock grep found no sqlalchemy entry]
**How to avoid:** Explicitly add `sqlalchemy>=2.0` to pitlane-studio's `[project] dependencies` and run `uv lock`.

### Pitfall 3: bleach Default Tag Allowlist Is Too Restrictive for Markdown
**What goes wrong:** Using `bleach.clean(text)` with defaults will strip `<p>`, `<h1>`-`<h6>`, `<pre>`, `<table>` etc. from markdown-converted HTML, leaving malformed output.
**Why it happens:** bleach's default `ALLOWED_TAGS` covers only inline elements; block elements from markdown are not included.
**How to avoid:** Use the `_MARKDOWN_TAGS` set defined in Pattern 4 above as the `tags=` argument.
**Warning signs:** Headlines and paragraphs disappearing from rendered template output.

### Pitfall 4: Returning `str` Instead of `Markup` from bleach Filter
**What goes wrong:** If `safe_html` returns a plain `str`, Jinja2 will HTML-escape the already-clean HTML a second time, producing visible `&lt;p&gt;` in the browser.
**Why it happens:** Jinja2 auto-escaping is enabled; only `Markup` instances bypass it.
**How to avoid:** Always `return Markup(bleach.clean(...))` from the filter function.

### Pitfall 5: Missing `~/.pitlane/studio/` Directory
**What goes wrong:** SQLAlchemy's `create_engine(f"sqlite:///{path}")` does not create parent directories. If `~/.pitlane/studio/` does not exist, you get `OperationalError: unable to open database file`.
**Why it happens:** SQLite itself does not create intermediate directories.
**How to avoid:** Call `path.parent.mkdir(parents=True, exist_ok=True)` before `create_engine()`. See `get_engine()` pattern above.

### Pitfall 6: State Machine — `published` Has No Forward Transition
**What goes wrong:** `_TRANSITIONS` dict only covers forward moves. Calling `transition_status(id, "draft")` from `published` would silently succeed if not guarded.
**Why it happens:** The dict lookup `_TRANSITIONS.get(current)` returns `None` for `published`, but `None != target_status` is still a ValueError — so it IS guarded. But this should be explicit in tests.
**How to avoid:** Integration test must verify `draft → published` raises ValueError (skipping intermediate states) AND `published → draft` raises ValueError (reversal attempt).

---

## Code Examples

### ArticleStore: Full State Transition Round-trip Test

```python
# Source: codebase inspection + [CITED: docs.sqlalchemy.org/en/20/core/connections.html]
import pytest
from pathlib import Path
from pitlane_studio.store.article_store import ArticleStore
import uuid


def test_article_full_lifecycle(tmp_path: Path):
    store = ArticleStore(db_path=tmp_path / "articles.db")
    article_id = str(uuid.uuid4())
    store.create(article_id, race_year=2026, race_round=5)
    
    record = store.get(article_id)
    assert record.status == "draft"
    
    store.transition_status(article_id, "outline_generated")
    store.transition_status(article_id, "outline_approved")
    store.transition_status(article_id, "published")
    
    final = store.get(article_id)
    assert final.status == "published"


def test_invalid_transition_raises_value_error(tmp_path: Path):
    store = ArticleStore(db_path=tmp_path / "articles.db")
    article_id = str(uuid.uuid4())
    store.create(article_id, race_year=2026, race_round=5)
    
    with pytest.raises(ValueError):
        store.transition_status(article_id, "published")  # skip intermediate states
    
    with pytest.raises(ValueError):
        store.transition_status(article_id, "outline_approved")  # must go via outline_generated first
```

### CLI Entry Point (port 8001)

```python
# Source: pitlane_web/cli.py pattern [VERIFIED: codebase inspection]
import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8001, type=int, show_default=True)
@click.option("--reload/--no-reload", default=None)
@click.version_option(package_name="pitlane-studio")
def main(host: str, port: int, reload: bool | None) -> None:
    """Run the PitLane Studio co-authoring server."""
    if reload is None:
        import os
        reload = os.getenv("PITLANE_ENV", "production") == "development"
    uvicorn.run("pitlane_studio.app:app", host=host, port=port, reload=reload)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `session.query()` ORM style | SQLAlchemy 2.0 Core `engine.begin()` + table expressions | SQLAlchemy 2.0 (2023) | 2.0 API is the standard; 1.x legacy API still works but deprecated |
| bleach 5.x (`ALLOWED_TAGS` as list) | bleach 6.x (`ALLOWED_TAGS` as set) | bleach 6.0 (2023) | Minor; use set literal in tag definitions |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLite ISO8601 string storage is simpler than SQLAlchemy DateTime type for Core-only usage | Pattern 3 | If DateTime coercion is needed, switch to `DateTime` column type — low impact, easy fix |
| A2 | `detect_stories()` returns empty list (not error) when 2026 ELO snapshots are not built — integration test uses `pytest.skip` on missing data | Pattern 6 | If function raises on missing data, test strategy changes to expect-exception; check signals.py line 429 |
| A3 | `strip=True` in bleach.clean() is the correct choice for pitlane-studio (remove unknown tags rather than escape them) | Pattern 4 | If escaping is preferred over stripping, change to `strip=False`; no functional difference for well-formed markdown HTML |

**Note on A2:** This is actually VERIFIED — `signals.py` line 428-429 shows `if not race_snapshots: return []`. [VERIFIED: signals.py inspection]

---

## Open Questions

1. **Does the root pyproject.toml need pitlane-studio added to its `[project] dependencies` list?**
   - What we know: Root `pyproject.toml` has `package = false` (it's a virtual workspace root) and lists pitlane-agent, pitlane-elo, pitlane-web. The `[tool.uv.workspace] members = ["packages/*"]` glob will auto-discover pitlane-studio.
   - What's unclear: Whether the root's `[tool.uv.sources]` and `[project] dependencies` need updating for `uv sync --all-packages` to install pitlane-studio.
   - Recommendation: Add `pitlane-studio` to root `[project] dependencies` and `[tool.uv.sources]` following the existing pattern. The `--all-packages` flag installs all workspace members regardless, but explicit listing maintains consistency.

2. **Does pitlane-elo need pitlane-studio as a test dependency?**
   - What we know: The integration test lives in `packages/pitlane-studio/tests/test_studio_api.py` and imports from `pitlane_elo.studio_api`. This is a pitlane-studio test, not a pitlane-elo test.
   - What's unclear: Whether pitlane-elo needs any changes to its own test suite to cover `studio_api.py`.
   - Recommendation: No pitlane-elo test changes needed. `studio_api.py` is a thin re-export with no logic; coverage comes from the pitlane-studio cross-package integration test.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | pyproject.toml constraint | ✓ | system Python (confirmed by existing packages) | — |
| uv | Package management | ✓ | 0.10.9 [VERIFIED: `uv --version`] | — |
| SQLAlchemy | ArticleStore | Not in lock yet | Will be 2.0.49 after `uv add` | — |
| bleach | Jinja2 sanitization | In lock (transitive) | 6.3.0 [VERIFIED: uv.lock] | — |
| ELO snapshots (Parquet) | Integration test | Present (assumed from cached data) | 2026 data required | `pytest.skip` if absent |

**Missing dependencies with no fallback:**
- SQLAlchemy must be added via `uv add --directory packages/pitlane-studio sqlalchemy>=2.0`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already configured in root pyproject.toml and pitlane-elo/pyproject.toml) |
| Config file | Root `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["packages/*/tests"]` |
| Quick run command | `uv run --directory packages/pitlane-studio pytest -x` |
| Full suite command | `uv run pytest` (from repo root, covers all packages) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PKG-01 | `pitlane-studio` installs and health endpoint returns 200 | smoke | `uv run --directory packages/pitlane-studio pytest tests/test_app.py -x` | ❌ Wave 0 |
| PKG-02 | `detect_stories()` callable with real 2026 data, returns `list[StorySignal]` | integration | `uv run --directory packages/pitlane-studio pytest tests/test_studio_api.py -x` | ❌ Wave 0 |
| PKG-03 | bleach.clean() sanitizes XSS attempt in safe_html filter | unit | `uv run --directory packages/pitlane-studio pytest tests/test_filters.py -x` | ❌ Wave 0 |
| PKG-04 | ArticleStore creates, transitions, and persists to real SQLite file | integration | `uv run --directory packages/pitlane-studio pytest tests/test_article_store.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --directory packages/pitlane-studio pytest -x`
- **Per wave merge:** `uv run pytest` (full suite from root)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `packages/pitlane-studio/tests/__init__.py` — required for pytest discovery
- [ ] `packages/pitlane-studio/tests/conftest.py` — shared `tmp_path`-based fixtures
- [ ] `packages/pitlane-studio/tests/test_app.py` — PKG-01 smoke test
- [ ] `packages/pitlane-studio/tests/test_studio_api.py` — PKG-02 integration test
- [ ] `packages/pitlane-studio/tests/test_filters.py` — PKG-03 unit test
- [ ] `packages/pitlane-studio/tests/test_article_store.py` — PKG-04 integration test
- [ ] pitlane-studio package itself (entire `packages/pitlane-studio/` tree)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in v1 (personal tool, per REQUIREMENTS.md) |
| V3 Session Management | no | No sessions in pitlane-studio Phase 1 |
| V4 Access Control | no | No multi-tenancy |
| V5 Input Validation | yes | Pydantic BaseModel for article records; bleach.clean() for HTML output |
| V6 Cryptography | no | No cryptography in Phase 1 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via LLM-generated HTML in templates | Tampering / Spoofing | `bleach.clean()` via `safe_html` filter; never `\| safe` in pitlane-studio |
| Path traversal in SQLite db_path | Tampering | `Path.home() / ".pitlane" / "studio" / "articles.db"` — fixed path, no user input in path construction |
| State machine bypass (skip outline approval) | Tampering | `ArticleStore.transition_status()` raises `ValueError` on illegal transitions (D-05) |

---

## Project Constraints (from CLAUDE.md)

| Directive | Constraint |
|-----------|-----------|
| Package manager | `uv` only — never `pip` directly |
| Install all packages | `uv sync --all-packages` |
| Run tests | `uv run --directory packages/<package-name> pytest` |
| Add dependency | `uv add --directory packages/<package-name> <dep>` |
| New package pattern | Follow `packages/pitlane-web/` (FastAPI + uvicorn) |
| Imports | Always at top of file — never lazy imports inside functions or blocks |
| Import style | `from pitlane_elo.studio_api import detect_stories` — not subprocess/CLI invocation |
| SDK pin | `claude-agent-sdk<0.2.0` — enforce in pyproject.toml |
| XSS | All Jinja2 `\| safe` outputs in pitlane-studio must go through `bleach.clean()` |
| bleach scope | pitlane-studio ONLY — do NOT touch existing pitlane-web templates |
| SQLite path | `~/.pitlane/studio/articles.db` |
| SQLAlchemy | Core only, no ORM |
| Port | 8001 (pitlane-studio), does not conflict with pitlane-web |

---

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` — `detect_stories()` full implementation, `StorySignal` dataclass, `round_num` parameter name
- Codebase inspection: `packages/pitlane-elo/src/pitlane_elo/data.py` — `get_race_entries()` signature and return type
- Codebase inspection: `packages/pitlane-web/pyproject.toml`, `packages/pitlane-agent/pyproject.toml`, `packages/pitlane-elo/pyproject.toml` — dependency patterns
- Codebase inspection: `pyproject.toml` (root) — workspace configuration, `members = ["packages/*"]`
- Codebase inspection: `uv.lock` — confirmed SQLAlchemy NOT present, bleach 6.3.0 present, fastapi 0.128.0, pydantic 2.12.5, claude-agent-sdk 0.1.47
- Context7: `/websites/sqlalchemy_en_20_core` — `engine.begin()`, `MetaData.create_all()`, connection patterns
- [CITED: bleach.readthedocs.io/en/latest/clean.html] — `bleach.clean()` parameters, default ALLOWED_TAGS, Markup return requirement

### Secondary (MEDIUM confidence)
- PyPI metadata: SQLAlchemy 2.0.49, bleach 6.3.0 Python >=3.10 compatibility — confirmed via `curl https://pypi.org/pypi/<pkg>/json`
- `uv --version` output: 0.10.9 — current installed uv version

### Tertiary (LOW confidence)
- None — all claims verified via codebase or official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified from uv.lock and PyPI
- Architecture: HIGH — patterns taken directly from existing codebase
- Pitfalls: HIGH — SQLAlchemy transitive-dep pitfall VERIFIED by uv.lock inspection; others verified by code inspection
- Test patterns: HIGH — pytest config verified from root pyproject.toml

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (stable deps; bleach and SQLAlchemy are stable libraries)
