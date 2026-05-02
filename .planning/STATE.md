# Project State: PitLane Studio

*Last updated: 2026-05-02*

---

## Project Reference

**Core Value:** Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

**Current Focus:** Phase 1 — Package Scaffold + Prerequisites

**Total Phases:** 3
**Current Phase:** 1
**Current Plan:** None (planning not yet started)

---

## Current Position

**Phase:** 1 — Package Scaffold + Prerequisites
**Status:** Not started
**Plans complete:** 0/?

```
Progress: [ Phase 1 ] → [ Phase 2 ] → [ Phase 3 ]
             ^
           (here)
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 3 |
| Phases complete | 0 |
| v1 requirements | 19 |
| Requirements mapped | 19 |
| Requirements complete | 0 |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Separate `pitlane-studio` package | Co-authoring has a fundamentally different interaction model from the chat UI | Pending implementation |
| Markdown copy/paste as the v1 export path | Substack unofficial API is LOW confidence; markdown is reliable and sufficient | Confirmed |
| Substack unofficial API deferred to v2 | Cookie-based auth expires silently; adapter architecture is correct but API stability not validated | Confirmed |
| Svelte 5 + TipTap 2.x for frontend | Drag-and-drop beat timeline and per-block prose editor require client-side state HTMX cannot cleanly manage | Pending validation |
| Direct Python imports, not subprocess | pitlane-agent commands/ layer is pure Python and importable | Confirmed |
| SQLite, not workspace system | Articles need stable identity and status transitions; workspaces are ephemeral | Confirmed |
| EndureElo as signal source | Empirically outperforms SpeedElo and Bayesian model; already tested | Confirmed |
| FiveActMapper is static config, not AI | Act→data mapping is a design choice, not a reasoning task | Confirmed |

### Known Issues / Blockers

- `claude-agent-sdk` is not yet pinned to `<0.2.0` — uv API drift risk (Phase 1 prerequisite)
- Jinja2 `| safe` template outputs not yet sanitized with `bleach.clean()` — XSS risk (Phase 1 prerequisite)
- DNF classification for 2025 data: all DNFs classified as "retired" — `exclude_mechanical_dnf` disabled; ANGL-03 uses web search cross-check specifically because of this
- ELO thresholds for 2026 (`ΔR̂_3race > 0.5`) may need recalibration after 6+ races of data

### Research Flags (Requiring Validation)

- **Before Phase 2:** Substack API live endpoint — confirm `/api/v1/drafts` POST format, required cookie names, `draft_body` schema. Determines whether XPRT-02 moves to v1 or remains v2.
- **Before Phase 3:** TipTap + Svelte 5 headless integration — verify `onMount` pattern and `getJSON()` compatibility with Substack's ProseMirror variant. MEDIUM confidence only.

### Architecture Constraints (from codebase)

- uv monorepo: new package lives at `packages/pitlane-studio/` following pitlane-web pattern
- Tests run via: `uv run --directory packages/pitlane-studio pytest` (per uv-pytest skill)
- All imports at top of file — no lazy imports inside functions or blocks (per project feedback)
- Imports from pitlane-agent `commands/` layer, not CLI layer (pure functions, no SDK dependency)
- No authentication, no multi-tenancy — personal tool

---

## Session Continuity

**To resume after a break:**
1. Read this file — current phase and plan are at the top
2. Read `.planning/ROADMAP.md` — phase goals and success criteria
3. Read `.planning/REQUIREMENTS.md` — traceability table for current phase
4. Check `.planning/plans/` for any written plans (when Phase 1 planning begins)

**Next action:** Run `/gsd-plan-phase 1` to create the implementation plan for Phase 1.

---

*State initialized: 2026-05-02*
