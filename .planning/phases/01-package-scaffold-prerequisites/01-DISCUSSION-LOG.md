# Phase 1: Package Scaffold + Prerequisites - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 1-Package Scaffold + Prerequisites
**Areas discussed:** studio_api interface, SQLite store (stdlib vs ORM)

---

## studio_api Interface

### Q1: What should detect_stories() accept as input?

| Option | Description | Selected |
|--------|-------------|----------|
| year + round (ints) | Simple and concrete — matches how pitlane-agent commands identify races | ✓ |
| RaceEntry dataclass | Already exists in pitlane_elo.data — pass the full race record | |
| session_type too | year + round + session_type (e.g. 'R') — signals.py already filters internally | |

**User's choice:** year + round as plain ints
**Notes:** None

---

### Q2: What should detect_stories() return?

| Option | Description | Selected |
|--------|-------------|----------|
| list[StorySignal] as-is | Return existing StorySignal dataclass directly. Phase 2 AngleService does transformation | ✓ |
| New StoryCandidate type | New boundary dataclass in studio_api mapping from StorySignal | |
| list[dict] | Plain dicts — untyped, harder to assert against in tests | |

**User's choice:** list[StorySignal] as-is
**Notes:** Phase 1 stays minimal; Phase 2 handles transformation.

---

### Q3: For the cross-package integration test, which real race data?

| Option | Description | Selected |
|--------|-------------|----------|
| Latest available 2025 race | Whatever is cached locally | |
| Hardcode a specific race (e.g. 2025 R1) | Deterministic but fragile | |
| Parameterized via env var | Flexible but adds setup overhead | |

**User's choice:** (free text) "Its 2026 Dude"
**Notes:** Use 2026 season data. Follow-up confirmed: latest available 2026 race (dynamic, not hardcoded round).

---

### Q4: For 2026 data, how should the test pick the race?

| Option | Description | Selected |
|--------|-------------|----------|
| Latest available 2026 race | Most recently cached round — no hardcoded number | ✓ |
| Hardcode 2026 Round 1 | Always uses same race — deterministic but fragile if not cached | |

**User's choice:** Latest available 2026 race
**Notes:** None

---

## SQLite Article Store

### Q1: How should ArticleStore access SQLite?

| Option | Description | Selected |
|--------|-------------|----------|
| Raw sqlite3 stdlib | No new deps. Simple 4-state table with plain SQL | |
| SQLAlchemy Core | Connection pooling + typed query builder. No ORM; adds dep | ✓ |
| SQLAlchemy ORM | Full ORM with declarative models. Most overhead | |

**User's choice:** SQLAlchemy Core
**Notes:** No existing ORM in the monorepo; SQLAlchemy Core is the first use.

---

### Q2: Should ArticleStore use a Pydantic model for records?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, Pydantic BaseModel | Typed records with validation. Already a FastAPI dep | ✓ |
| Plain dataclass | Lightweight, stdlib-only | |
| No model, raw dicts | Dict in/out. No type safety | |

**User's choice:** Pydantic BaseModel
**Notes:** No new dependency since FastAPI already requires Pydantic.

---

### Q3: Invalid state transitions should...

| Option | Description | Selected |
|--------|-------------|----------|
| Raise ValueError | Strict state machine — bugs obvious early; approval gate depends on this | ✓ |
| Silently ignore | No error, no-op — hides bugs | |

**User's choice:** Raise ValueError
**Notes:** The Phase 3 hard approval gate depends on strict enforcement.

---

## Claude's Discretion

- Package structure (src layout, module names, `__init__.py` contents) — follow pitlane-web pattern
- SQLAlchemy engine/connection setup — standard approach
- bleach.clean() wrapping pattern in pitlane-studio templates — Claude's call; just needs to exist and be unit-tested

## Deferred Ideas

None — discussion stayed within phase scope.
