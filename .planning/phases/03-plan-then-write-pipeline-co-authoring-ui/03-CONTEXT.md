# Phase 3: Plan-Then-Write Pipeline + Co-Authoring UI - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the PipelineOrchestrator (outline generation → hard backend-enforced approval gate → per-beat SSE prose streaming), FastAPI routes wiring the pipeline, a SvelteKit 5 + TipTap 2.x co-authoring frontend, and markdown export. Phase delivers the complete journalist-facing writing workflow end to end.

Requirements in scope: ACT-03, PTW-01, PTW-02, PTW-03, PTW-04, UI-01, UI-02, UI-03, XPRT-01.

</domain>

<decisions>
## Implementation Decisions

### Beat Structure (PTW-01, PTW-03)

- **D-01:** Beats are variable in count — the journalist can add, remove, or reorder beats in the outline panel before approval. The five-act framework is the default starting structure (5 beats mapped from FiveActMapper's ACT_CONFIG), but the outline is editable. The prose pipeline generates one streaming LLM call per approved beat, for however many beats exist.
- **D-02:** The full approved outline (all beat titles and data anchors) is injected into every individual beat's generation prompt, regardless of beat count.

### SSE Streaming (PTW-03)

- **D-03:** One SSE request per beat, made sequentially by the frontend. Endpoint: `GET /articles/{id}/beats/{beat_number}/stream`. After outline approval, the frontend auto-advances through all approved beats automatically — no manual trigger per beat. The journalist observes prose appearing beat by beat.
- **D-04:** SSE events per beat stream: `beat_start`, `token` (streamed prose tokens), `beat_done` (full prose + placeholder markers), `error`. Frontend connects to beat N+1 immediately after receiving `beat_done` for beat N.

### Approval Gate (PTW-02)

- **D-05:** The backend enforces the hard approval gate via ArticleStore state. The `/stream` endpoints return HTTP 409 if `article.status != "outline_approved"`. The existing ArticleStore `outline_generated → outline_approved` transition is the mechanism — no new logic required. There is no bypass path.

### Article Content Persistence

- **D-06:** Beat prose is persisted to SQLite as each beat's SSE stream completes (on `beat_done`). New `beats` table: `(article_id, beat_number, beat_title, prose, placeholder_markers_json, created_at, updated_at)`. This allows the journalist to refresh the page and continue editing without data loss.
- **D-07:** The outline itself (beat titles, data anchors, beat order) is also persisted to SQLite when it is first generated and again when the journalist edits it. New `outline_beats` table: `(article_id, beat_number, beat_title, data_anchors, act_number, position)`. Approval updates ArticleStore status to `outline_approved`.

### Frontend Serving & Dev Workflow (UI-01, UI-02, UI-03)

- **D-08:** SvelteKit static build served by FastAPI at `/`. Build output destination: `packages/pitlane-studio/src/pitlane_studio/static/`. FastAPI mounts this directory as a `StaticFiles` app. Single process, single port (8001). No CORS config needed.
- **D-09:** SvelteKit app lives at `packages/pitlane-studio/frontend/`. Build command: `npm run build` (from `frontend/`), output to `../src/pitlane_studio/static/`. The `frontend/` directory has its own `package.json`, `vite.config.ts`, and `svelte.config.js`.
- **D-10:** TipTap + Svelte 5 integration is flagged MEDIUM confidence (STATE.md research flag). Wave 0 of Phase 3 planning includes a TipTap + Svelte 5 spike: validate `onMount` instantiation pattern, `editor.getJSON()` round-trip, and custom node extension. The spike must pass before the full editor implementation wave begins.

### Claude's Discretion

- Placeholder hook representation in TipTap (custom node extension vs. mark vs. inline leaf) — Claude picks the approach that renders as a visually distinct unfilled block and survives `getJSON()` round-trips cleanly.
- Race selector UX details (year/round dropdowns vs. searchable list) — Claude picks a simple, functional approach.
- Exact SSE event schema beyond `beat_start / token / beat_done / error` — Claude specifies what's in each payload.
- FastAPI route organization (router files, grouping) — Claude follows the pattern from existing `app.py`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, requirements (ACT-03, PTW-01..04, UI-01..03, XPRT-01)
- `.planning/REQUIREMENTS.md` — Full v1 requirements; Phase 3 section contains all requirement definitions

### Phase 3 Foundation (existing services)
- `packages/pitlane-studio/src/pitlane_studio/services/angles.py` — `AngleService.get_angles(year, round)` → `list[AngleCandidate]`; `DataNotReadyError` for blocking state
- `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` — `ACT_CONFIG` static dict (5 acts), `FiveActMapper.fetch_act_data()` with in-memory cache
- `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` — ArticleStore state machine (`draft → outline_generated → outline_approved → published`); SQLAlchemy Core pattern to follow for new tables

### FastAPI Skeleton
- `packages/pitlane-studio/src/pitlane_studio/app.py` — Existing FastAPI app on port 8001; StaticFiles mount to be added here

### Architecture Constraints
- `CLAUDE.md` — Monorepo rules, import rules (all imports at top of file), test commands, XSS constraint (`bleach.clean()` on any `| safe` Jinja2 output)

### Prior Phase Context
- `.planning/phases/01-package-scaffold-prerequisites/01-CONTEXT.md` — SQLAlchemy Core pattern, Pydantic BaseModel convention
- `.planning/phases/02-story-angle-detection-five-act-data-layer/02-CONTEXT.md` — AngleCandidate schema, FiveActMapper decisions, DNF cross-check decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ArticleStore` — state machine + SQLAlchemy Core pattern; `beats` and `outline_beats` tables should follow the same Core (no ORM) pattern
- `AngleService.get_angles(year, round)` — already returns `list[AngleCandidate]` with `angle_id`, `name`, `signal_type`, `confidence`, `data_rationale`; directly feeds UI-01 angle cards
- `FiveActMapper.fetch_act_data(year, round, act_number)` — feeds ACT-03 five-act sidebar; in-memory cached; call on race load
- `pitlane_studio.filters.safe_html` — XSS sanitizer; any user-editable content rendered in Jinja2 must pass through this

### Established Patterns
- **Direct Python imports, never subprocess** — PipelineOrchestrator imports from `pitlane_agent.commands.*` and `pitlane_elo.studio_api` directly
- **All imports at top of file** — enforced project-wide; no lazy imports
- **Pydantic BaseModel** for all data schemas at the Python layer
- **SQLAlchemy Core only** — no ORM/Session; use `Table/Column/MetaData` as in `article_store.py`
- **anthropic SDK (not claude-agent-sdk)** for LLM calls in the pipeline — already used in `angles.py` for DNF check

### Integration Points
- New FastAPI routes connect to: `AngleService`, `ArticleStore`, `FiveActMapper`, new `PipelineOrchestrator`
- SvelteKit frontend communicates only with FastAPI at port 8001 (same origin, no CORS)
- `beats` and `outline_beats` SQLite tables live in the same `~/.pitlane/studio/articles.db` as `articles`

</code_context>

<specifics>
## Specific Ideas

- Five-act structure is the default starting point for the outline, pre-populated from `ACT_CONFIG` labels and `FiveActMapper` data — the journalist edits from there, not from a blank page
- The hard approval gate is enforced in two layers: UI hides the generate button, backend returns 409 if status is wrong — both must be present
- Beat prose generation uses the `anthropic` SDK (consistent with the DNF check in Phase 2) — not claude-agent-sdk
- Markdown export (`XPRT-01`) renders placeholder hooks as `[JOURNALIST: quote]`, `[JOURNALIST: context]`, `[JOURNALIST: causal]` markers in plain markdown

</specifics>

<deferred>
## Deferred Ideas

- Substack unofficial API draft export (XPRT-02, XPRT-03) — v2; markdown copy/paste is the v1 path
- Draggable beat reordering in timeline view (CM-02) — v2
- Article draft list / resume saved drafts (CM-01) — v2
- Audience framing controls (WE-01) — v2
- Character arc detection (WE-02) — v2
- Multimodal chart pairing (WE-03) — v2

</deferred>

---

*Phase: 3-Plan-Then-Write Pipeline + Co-Authoring UI*
*Context gathered: 2026-05-05*
