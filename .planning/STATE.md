---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 3
current_plan: None
status: Phase 3 planned — ready to execute
last_updated: "2026-05-05T00:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 14
  completed_plans: 8
  percent: 67
---

# Project State: PitLane Studio

*Last updated: 2026-05-05 — Phase 3 planned (6 plans, 3 waves)*

---

## Project Reference

**Core Value:** Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

**Current Focus:** Phase 3 — Plan-Then-Write Pipeline + Co-Authoring UI

**Total Phases:** 3
**Current Phase:** 3
**Current Plan:** None

---

## Current Position

**Phase:** 3 — Plan-Then-Write Pipeline + Co-Authoring UI (Ready to execute)
**Plans:** 6 plans, 3 waves
**Plans complete:** 8/8 (Phases 1 and 2 complete)

```
Progress: [ Phase 1 ✓ ] → [ Phase 2 ✓ ] → [ Phase 3 ◆ ]
                                                  ^
                                                (here)
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 3 |
| Phases complete | 2 |
| v1 requirements | 19 |
| Requirements mapped | 19 |
| Requirements complete | 10 (PKG-01..04, ANGL-01..04, ACT-01..02) |

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

**Next action:** Run `/gsd-discuss-phase 3` to gather context before planning Phase 3.

---

## Phase 2 Completion Summary

**Completed:** 2026-05-04
**Plans executed:** 4/4 (Waves 0, 1, 2 + gap-closure)
**Tests:** 42 passed, 2 skipped (expected live-data integration skips)
**Verification:** 6/6 must-haves (passed)

What was built:

- `pitlane_studio.services.angles` — `AngleService`, `AngleCandidate` (Pydantic), `DataNotReadyError`; full pipeline: data gate → ELO signals → non-ELO signals → DNF cross-check (web search, retry loop) → novelty filter → rank → return 4–6 candidates
- `pitlane_studio.services.five_act` — `ACT_CONFIG` static dict mapping 5 acts to pitlane-agent commands; `FiveActMapper.fetch_act_data()` with in-memory cache
- `_check_dnf` uses `tool_types = ["web_search_20250305", "web_search"]` retry loop; `BadRequestError` caught and retried with fallback tool type
- All imports at module top in both test files; `pytest.importorskip` at module scope for optional integration test

---

*State initialized: 2026-05-02 | Phase 1 complete: 2026-05-03 | Phase 2 complete: 2026-05-04*
