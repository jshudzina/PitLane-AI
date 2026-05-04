---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 2
current_plan: None
status: Phase 2 planned — ready to execute
last_updated: "2026-05-03T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 7
  completed_plans: 4
  percent: 57
---

# Project State: PitLane Studio

*Last updated: 2026-05-03 — Phase 2 planned*

---

## Project Reference

**Core Value:** Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

**Current Focus:** Phase 2 — Story Angle Detection + Five-Act Data Layer

**Total Phases:** 3
**Current Phase:** 2
**Current Plan:** None

---

## Current Position

**Phase:** 2 — Story Angle Detection + Five-Act Data Layer (Ready to execute)
**Plans:** 3 plans in 2 waves (Wave 0 + Wave 1 parallel)
**Plans complete:** 4/7 (Phase 1 complete; Phase 2 planned, not yet executed)

```
Progress: [ Phase 1 ✓ ] → [ Phase 2 ◆ ] → [ Phase 3 ]
                                ^
                              (here)
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 3 |
| Phases complete | 1 |
| v1 requirements | 19 |
| Requirements mapped | 19 |
| Requirements complete | 4 (PKG-01, PKG-02, PKG-03, PKG-04) |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Separate `pitlane-studio` package | Co-authoring has a fundamentally different interaction model from the chat UI | Implemented |
| Markdown copy/paste as the v1 export path | Substack unofficial API is LOW confidence; markdown is reliable and sufficient | Confirmed |
| Substack unofficial API deferred to v2 | Cookie-based auth expires silently; adapter architecture is correct but API stability not validated | Confirmed |
| Svelte 5 + TipTap 2.x for frontend | Drag-and-drop beat timeline and per-block prose editor require client-side state HTMX cannot cleanly manage | Pending validation |
| Direct Python imports, not subprocess | pitlane-agent commands/ layer is pure Python and importable | Implemented |
| SQLite, not workspace system | Articles need stable identity and status transitions; workspaces are ephemeral | Implemented |
| EndureElo as signal source | Empirically outperforms SpeedElo and Bayesian model; already tested | Confirmed |
| FiveActMapper is static config, not AI | Act→data mapping is a design choice, not a reasoning task | Confirmed |
| Two-pass XSS sanitization | regex pre-pass strips script/style inner content; bleach.clean() strips remaining disallowed tags | Implemented |
| ArticleStore uses SQLAlchemy Core only | No ORM/Session — keeps the state machine explicit and avoids ORM complexity for a simple state table | Implemented |

### Known Issues / Blockers

- Code review (01-REVIEW.md) found 3 critical findings to address before Phase 3:
  - CR-01: Lazy imports in test files (violates CLAUDE.md)
  - CR-02: markupsafe undeclared direct dependency in pitlane-studio/pyproject.toml
  - CR-03: pitlane-agent not declared in pitlane-studio dependencies
- DNF classification for 2025 data: all DNFs classified as "retired" — `exclude_mechanical_dnf` disabled; ANGL-03 uses web search cross-check specifically because of this
- ELO thresholds for 2026 (`ΔR̂_3race > 0.5`) may need recalibration after 6+ races of data

### Research Flags (Requiring Validation)

- **Before Phase 2:** Substack API live endpoint — confirm `/api/v1/drafts` POST format, required cookie names, `draft_body` schema. Determines whether XPRT-02 moves to v1 or remains v2.
- **Before Phase 3:** TipTap + Svelte 5 headless integration — verify `onMount` pattern and `getJSON()` compatibility with Substack's ProseMirror variant. MEDIUM confidence only.

### Architecture Constraints (from codebase)

- uv monorepo: pitlane-studio at `packages/pitlane-studio/` — fully installed via `uv sync --all-packages`
- Tests run via: `uv run --directory packages/pitlane-studio pytest` (16 tests, all passing)
- All imports at top of file — no lazy imports inside functions or blocks (per project feedback; CR-01 to fix)
- Imports from pitlane-agent `commands/` layer, not CLI layer (pure functions, no SDK dependency)
- No authentication, no multi-tenancy — personal tool
- pitlane-studio port: 8001; pitlane-web port: 8000

---

## Phase 1 Completion Summary

**Completed:** 2026-05-03
**Plans executed:** 4/4 (Waves 0, 1, 2)
**Tests:** 16 passed, 0 xfail
**Verification:** 12/12 must-haves (passed)

What was built:

- `packages/pitlane-studio/` — fully installable uv workspace member (src layout, FastAPI /health, click CLI on port 8001)
- `pitlane_elo.studio_api` — public boundary with `detect_stories(year, round)` and `StorySignal`
- `claude-agent-sdk>=0.1.40,<0.2.0` pin in pitlane-agent (resolves 0.1.47)
- `pitlane_studio.filters.safe_html` — two-pass XSS sanitizer returning `markupsafe.Markup`
- `pitlane_studio.store.ArticleStore` — SQLAlchemy Core + Pydantic, strict state machine (draft→outline_generated→outline_approved→published)

---

## Session Continuity

**To resume after a break:**

1. Read this file — current phase is Phase 2
2. Read `.planning/ROADMAP.md` — Phase 2 goal and success criteria
3. Read `.planning/REQUIREMENTS.md` — ANGL-01..04, ACT-01..02 requirements for Phase 2
4. Run `/gsd-discuss-phase 2` to gather context before planning

**Next action:** Run `/gsd-execute-phase 2` to execute Phase 2 (plans ready — Wave 0 → Wave 1 parallel).

---

*State initialized: 2026-05-02 | Phase 1 complete: 2026-05-03*
