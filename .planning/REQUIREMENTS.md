# Requirements: PitLane Studio

**Defined:** 2026-05-02
**Core Value:** Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

## v1 Requirements

### Package & Infrastructure

- [ ] **PKG-01**: Developer can install pitlane-studio as a uv workspace package alongside pitlane-agent and pitlane-elo (pyproject.toml, FastAPI skeleton, uvicorn entry point, `pitlane-studio` CLI)
- [ ] **PKG-02**: pitlane-elo exposes a `studio_api` interface module with a cross-package integration test that calls `detect_stories()` with real data — not a mock
- [ ] **PKG-03**: claude-agent-sdk is pinned to `<0.2.0` and any Jinja2 `| safe` template outputs are sanitized with `bleach.clean()`
- [ ] **PKG-04**: User can persist article drafts across sessions via SQLite at `~/.pitlane/studio/articles.db` with status machine (`draft` → `outline_generated` → `outline_approved` → `published`)

### Story Angle Detection

- [ ] **ANGL-01**: User can load any completed race and receive 4–6 story angle candidates derived from ELO signals (SurpriseScore, ΔR̂, teammate ΔR̂ crossing, hot/cold streaks)
- [ ] **ANGL-02**: Angle candidates are ranked by field-relative significance (top 2 per signal type) and filtered for novelty (suppress same driver + same signal type if it appeared in the prior 2 races)
- [ ] **ANGL-03**: Driver crisis angles (slump, underperformance) are cross-checked against web search results for that race's DNF/retirement events before surfacing — FastF1 DNF classification is not used
- [ ] **ANGL-04**: Angle generation is blocked with a user-facing message if race session data is less than 2 hours old or lap count is incomplete

### Five-Act Race Timeline

- [ ] **ACT-01**: System maps Bouzarth et al.'s five dramatic acts to specific pitlane-agent commands via static Python config (act 1: qualifying/grid → `session-info` + `qualifying-results`; act 2: lap-1 chaos → `race-control` + `position-changes`; act 3: pit window → `tyre-strategy` + `race-control`; act 4: final stint → `lap-times` + `position-changes`; act 5: implications → `standings`). Note: act 1 uses `qualifying-results` (not `position-changes`) per CONTEXT.md D-12 — qualifying grid context is more relevant to act 1 than position changes, which belong in acts 2 and 4.
- [ ] **ACT-02**: System fetches and caches act-specific data on race load; data is available as grounding context when generating outline and beat prose
- [ ] **ACT-03**: User sees an always-visible five-act sidebar in the co-authoring UI showing act labels, mapped data sources, and key data points per act

### Plan-Then-Write Pipeline

- [ ] **PTW-01**: System generates a structured article outline (5 beat dicts: beat title, data anchors, suggested angle framing, placeholder types required) via a single non-streaming LLM call after user selects an angle
- [ ] **PTW-02**: User must explicitly approve the outline before any beat prose is generated; the approval action is a hard gate — there is no way to skip it
- [ ] **PTW-03**: After outline approval, system generates prose for each of the 5 beats via 5 separate streaming LLM calls (one per act/beat); the full approved outline is injected into every beat's prompt
- [ ] **PTW-04**: Each generated beat contains enforced placeholder hooks for journalist-only content (at minimum: one quote placeholder, one contextual explanation placeholder, one causal reasoning placeholder per beat); the tool does not generate content to fill these slots

### Co-Authoring UI

- [ ] **UI-01**: User can select a race from a race selector, view 4–6 angle cards (each showing: angle name, signal type, confidence level, brief data rationale), and choose 1–2 angles to develop into an article
- [ ] **UI-02**: User can read and edit each beat's AI-generated prose in a TipTap block editor, with placeholder hooks rendered as visually distinct unfilled blocks
- [ ] **UI-03**: User can review the full 5-beat outline in a panel before prose generation begins, and can edit beat titles or data anchors before approving

### Export

- [ ] **XPRT-01**: User can copy a clean markdown export of the full article draft at any time, with placeholder hooks rendered as `[JOURNALIST: <type>]` markers visible in the output

## v2 Requirements

### Export

- **XPRT-02**: Substack unofficial API draft export (POST to `/api/v1/drafts` with cookie auth; TipTap JSON payload)
- **XPRT-03**: Substack export health check (validate cookie auth before showing export option; degrade to markdown if check fails)

### Content Management

- **CM-01**: Article draft list — user can see and resume all saved drafts per race
- **CM-02**: Draggable beat reordering between acts in the timeline view

### Writing Experience

- **WE-01**: Audience framing control (casual fan / enthusiast / technical) adjusts prose depth across all beats
- **WE-02**: Character arc detection — flag narratively significant multi-race driver arcs (comeback, consistent underperformance, gamble pattern)
- **WE-03**: Multimodal pairing — auto-suggest which pitlane chart pairs with each narrative beat

### Platform

- **PLAT-01**: Live in-race mode — angle detection triggered by session data as race progresses

## Out of Scope

| Feature | Reason |
|---------|--------|
| Official Substack API | Does not exist |
| One-shot full article generation | Violates Wang et al. quality findings; defeats plan-then-write purpose |
| Chat box as primary interface | Sánchez-López: structured choices outperform open-ended prompting |
| Auto-publish / direct publish | Always export to draft; journalist reviews before any post goes live |
| Generic template library | Angles come from ELO data, not sports writing templates |
| Multi-user access / authentication | Personal tool; no auth needed |
| Mobile UI | Desktop web only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 1 | Pending |
| PKG-02 | Phase 1 | Pending |
| PKG-03 | Phase 1 | Pending |
| PKG-04 | Phase 1 | Pending |
| ANGL-01 | Phase 2 | Pending |
| ANGL-02 | Phase 2 | Pending |
| ANGL-03 | Phase 2 | Pending |
| ANGL-04 | Phase 2 | Pending |
| ACT-01 | Phase 2 | Pending |
| ACT-02 | Phase 2 | Pending |
| ACT-03 | Phase 3 | Pending |
| PTW-01 | Phase 3 | Pending |
| PTW-02 | Phase 3 | Pending |
| PTW-03 | Phase 3 | Pending |
| PTW-04 | Phase 3 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 3 | Pending |
| XPRT-01 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-02*
*Last updated: 2026-05-02 — traceability confirmed against ROADMAP.md*
