# Phase 1: Package Scaffold + Prerequisites - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the foundational pitlane-studio package: uv workspace registration, FastAPI/uvicorn skeleton on port 8001, SQLite article store with a 4-state machine, pinned claude-agent-sdk dependency, sanitized Jinja2 template outputs, and the studio_api surface in pitlane-elo. All subsequent phases depend on this foundation being clean and stable.

</domain>

<decisions>
## Implementation Decisions

### studio_api Interface (PKG-02)
- **D-01:** `detect_stories(year: int, round: int) -> list[StorySignal]` — accepts year and round as plain ints; returns the existing `StorySignal` dataclass from `pitlane_elo.stories.signals` as-is. No new boundary type in Phase 1; Phase 2's AngleService handles transformation.
- **D-02:** Cross-package integration test uses the latest available 2026 race (most recently cached round). Not hardcoded to a specific round number.

### SQLite Article Store (PKG-04)
- **D-03:** Use **SQLAlchemy Core** (not ORM) for database access. No declarative models; just connection pooling and typed query builder. SQLAlchemy is already a FastAPI transitive dep (via pitlane-web's FastAPI dep) — no net-new dependency.
- **D-04:** Article records are represented in Python as **Pydantic BaseModel** instances. Pydantic is already a FastAPI dep.
- **D-05:** Invalid state transitions (e.g. `draft → published`, skipping `outline_generated` or `outline_approved`) **raise `ValueError`**. Strict state machine — the Phase 3 hard approval gate depends on this being enforced.

### Claude's Discretion
- Package structure (src layout, `__init__.py` contents, module names beyond what's specified) follows the pitlane-web pattern exactly.
- SQLAlchemy connection setup (engine creation, context manager pattern) — standard approach is fine.
- Jinja2 + bleach integration in pitlane-studio templates — bleach.clean() wrapping approach is Claude's call; PKG-03 only requires the wrapping exists and is unit-tested.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, and requirements list (PKG-01 through PKG-04)
- `.planning/REQUIREMENTS.md` — Full v1 requirements with traceability table

### Existing Package Patterns (Template)
- `packages/pitlane-web/pyproject.toml` — Template for pitlane-studio's pyproject.toml (uv workspace dep, FastAPI/uvicorn deps, script entry point pattern)
- `packages/pitlane-web/src/pitlane_web/cli.py` — CLI entry point pattern (click + uvicorn)
- `packages/pitlane-web/src/pitlane_web/app.py` — FastAPI app structure to follow

### ELO Signal Source
- `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` — `StorySignal` dataclass and `get_story_signals()` function that `detect_stories()` will wrap
- `packages/pitlane-elo/pyproject.toml` — Where `studio_api` module must be added

### Security Constraint
- `packages/pitlane-web/src/pitlane_web/templates/partials/message.html` line 136 — Existing `| safe` pattern; **bleach.clean() is NOT applied here** (out of Phase 1 scope — pitlane-studio only)
- `packages/pitlane-web/src/pitlane_web/templates/partials/conversation_history.html` line 7 — Same: existing `| safe` without bleach, out of Phase 1 scope

### Architecture Constraints
- `CLAUDE.md` — Monorepo rules, import rules, test commands, key constraints (SDK pin, XSS, import style)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pitlane_elo.stories.signals.StorySignal`: Return type for `detect_stories()` — import directly
- `pitlane_elo.data.get_race_entries()`: Can be used to find the latest 2026 race for the integration test
- `pitlane_web.cli:main`: CLI entry point pattern — replicate for `pitlane_studio.cli:main`

### Established Patterns
- **Package layout**: `packages/<name>/src/<name_underscored>/` with `__init__.py`, `cli.py`, `app.py`, `py.typed`
- **pyproject.toml**: `[tool.uv.sources]` workspace deps + `[project.scripts]` CLI entry point
- **FastAPI app**: Import pitlane-agent/elo at module level (not lazy) — per feedback rule
- **No SQLAlchemy ORM anywhere**: pitlane-web uses raw file-based storage; pitlane-studio is the first SQLAlchemy user — keep to Core only

### Integration Points
- `pitlane_elo.studio_api` — new module in pitlane-elo; imported by pitlane-studio's integration test and (in Phase 2) AngleService
- `packages/pitlane-studio/` registered in root `pyproject.toml` and `uv.lock` as a workspace package
- Port 8001 — does not conflict with pitlane-web (assumed to be on a different port)

</code_context>

<specifics>
## Specific Ideas

- `detect_stories(year: int, round: int) -> list[StorySignal]` — exact signature confirmed
- Integration test: use `pitlane_elo.data.get_race_entries()` or similar to find the latest 2026 race dynamically, then call `detect_stories(year=2026, round=<latest>)` and assert result is a non-empty list of `StorySignal` objects
- bleach.clean() scope is **pitlane-studio only** — do not touch existing pitlane-web templates

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Package Scaffold + Prerequisites*
*Context gathered: 2026-05-02*
