# Roadmap: PitLane Studio

**Project:** PitLane Studio
**Milestone:** v1 — F1 journalism co-authoring interface
**Created:** 2026-05-02
**Granularity:** Standard (5–8 phases)

---

## Phases

- [x] **Phase 1: Package Scaffold + Prerequisites** - Install pitlane-studio into the monorepo, resolve inherited tech debt, and establish the SQLite article store as the foundation every downstream service depends on (completed 2026-05-03)
- [x] **Phase 2: Story Angle Detection + Five-Act Data Layer** - Build AngleService with ranking, novelty, and DNF filters; build FiveActMapper; wire PKG-02 cross-package integration surface; validate all signal quality concerns before UI conceals them (completed 2026-05-04)
- [ ] **Phase 3: Plan-Then-Write Pipeline + Co-Authoring UI** - Build PipelineOrchestrator (outline → hard approval gate → per-beat SSE prose), FastAPI routes, and Svelte/TipTap frontend; integrate five-act sidebar and markdown export

---

## Phase Details

### Phase 1: Package Scaffold + Prerequisites
**Goal**: A developer can install `pitlane-studio` as a uv workspace package with a working FastAPI skeleton, a tested SQLite article store, a pinned SDK dependency, and sanitized template outputs — so all subsequent phases build on a clean, stable foundation
**Depends on**: Nothing (first phase)
**Requirements**: PKG-01, PKG-02, PKG-03, PKG-04
**Success Criteria** (what must be TRUE):
  1. `pitlane-studio` installs cleanly via `uv sync --all-packages` alongside pitlane-agent, pitlane-elo, and pitlane-web with no dependency conflicts
  2. `pitlane-studio` CLI entry point starts a FastAPI/uvicorn server; health endpoint responds 200
  3. `pitlane_elo.studio_api` module exists and exposes `detect_stories()`; a cross-package integration test calls it with real (non-mock) data and passes under `uv run --directory packages/pitlane-studio pytest`
  4. `claude-agent-sdk` is pinned to `<0.2.0` in pyproject.toml and any Jinja2 `| safe` outputs pass through `bleach.clean()` — verifiable by code inspection and a unit test asserting sanitization
  5. An article record can be created, transitioned through all four states (`draft` → `outline_generated` → `outline_approved` → `published`), and persisted at `~/.pitlane/studio/articles.db` — verified by a pytest integration test against a real SQLite file
**Plans**: 4 plans
  - [x] 01-01-PLAN.md — Wave 0 test scaffold (xfail stubs for all four PKG-* tests + conftest fixtures)
  - [x] 01-02-PLAN.md — Wave 1 pitlane-studio package scaffold (pyproject, src layout, FastAPI app + /health, click CLI on port 8001, root workspace registration) [PKG-01]
  - [x] 01-03-PLAN.md — Wave 1 pitlane_elo.studio_api boundary module + claude-agent-sdk <0.2.0 pin in pitlane-agent [PKG-02, PKG-03 SDK half]
  - [x] 01-04-PLAN.md — Wave 2 bleach safe_html Jinja2 filter + ArticleStore (SQLAlchemy Core + Pydantic + strict state machine) [PKG-03 bleach half, PKG-04]

### Phase 2: Story Angle Detection + Five-Act Data Layer
**Goal**: The system surfaces 4–6 ranked, filtered, novel story angle candidates from any completed race using ELO signals, cross-checks driver crisis angles against actual DNF records, gates on data completeness, and has all five-act data fetched and cached — so angle quality is validated independently before the UI makes problems invisible
**Depends on**: Phase 1
**Requirements**: ANGL-01, ANGL-02, ANGL-03, ANGL-04, ACT-01, ACT-02
**Success Criteria** (what must be TRUE):
  1. Given a completed race, the system returns between 4 and 6 angle candidates derived from ELO signals (SurpriseScore, ΔR̂, teammate ΔR̂ crossing, hot/cold streaks) — verifiable via a pytest test against real 2025/2026 race data
  2. Angle candidates are ranked by field-relative significance (top 2 per signal type) and the same driver+signal combination does not appear if it was surfaced in either of the prior 2 races — verifiable by a novelty filter unit test
  3. A driver crisis angle (slump, underperformance) is suppressed and replaced with a user-facing message when a web search confirms the driver DNF/retired that race — FastF1 DNF classification is explicitly not used for this check
  4. Attempting to load angle candidates for a race session less than 2 hours old or with an incomplete lap count returns a clear blocking message and generates no angle candidates
  5. All five-act data (qualifying/grid, lap-1 chaos, pit window, final stint, championship implications) is fetched from pitlane-agent commands and cached on race load; each act's data is accessible as a Python dict keyed by act number — verifiable by a unit test against the static act→command config
**Plans**: 4 plans
  - [x] 02-01-PLAN.md — Wave 0: test stubs (xfail) for ANGL-01..04 and ACT-01..02 + anthropic dep + services/ package init [ANGL-01, ANGL-02, ANGL-03, ANGL-04, ACT-01, ACT-02]
  - [x] 02-02-PLAN.md — Wave 1: FiveActMapper + ACT_CONFIG static dict (5 acts × pitlane-agent commands, workspace_dir for chart commands, in-memory cache) [ACT-01, ACT-02]
  - [x] 02-03-PLAN.md — Wave 1: AngleService pipeline (AngleCandidate schema, DataNotReadyError gate, ELO cap, novelty filter, DNF cross-check, ranking) [ANGL-01, ANGL-02, ANGL-03, ANGL-04]
  - [x] 02-04-PLAN.md — Wave 2 (gap closure): DNF fallback retry loop + ACT-01 spec alignment + CLAUDE.md import fixes [ANGL-03, ACT-01]

### Phase 3: Plan-Then-Write Pipeline + Co-Authoring UI
**Goal**: A journalist can select a race, choose an angle, review and approve a structured outline, receive beat-by-beat AI prose with enforced placeholder hooks, edit in a block editor, see the five-act sidebar, and copy a clean markdown export — so the complete writing workflow is usable end to end
**Depends on**: Phase 2
**Requirements**: ACT-03, PTW-01, PTW-02, PTW-03, PTW-04, UI-01, UI-02, UI-03, XPRT-01
**Success Criteria** (what must be TRUE):
  1. A journalist can open the UI, select a race from the race selector, and see 4–6 angle cards each showing angle name, signal type, confidence level, and a brief data rationale — without any blank page or free-text prompt
  2. After selecting an angle, the journalist sees a 5-beat outline panel; can edit beat titles and data anchors; and must explicitly click an approve action before any prose is generated — there is no route to prose generation that bypasses this gate
  3. After outline approval, prose for each of 5 beats is generated via 5 separate streaming LLM calls; each beat's prompt includes the full approved outline; the journalist can observe prose appearing beat by beat in the editor
  4. Every generated beat contains at minimum one quote placeholder, one contextual explanation placeholder, and one causal reasoning placeholder rendered as visually distinct unfilled blocks in the TipTap editor — the tool generates no content to fill these slots
  5. The always-visible five-act sidebar shows act labels, mapped pitlane-agent data sources, and key data points for each act throughout the drafting session
  6. The journalist can click a copy/export action at any time and receive clean markdown with placeholder hooks rendered as `[JOURNALIST: <type>]` markers
**Plans**: TBD
**UI hint**: yes

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Package Scaffold + Prerequisites | 4/4 | Complete | 2026-05-03 |
| 2. Story Angle Detection + Five-Act Data Layer | 4/4 | Complete | 2026-05-04 |
| 3. Plan-Then-Write Pipeline + Co-Authoring UI | 0/? | Not started | - |

---

## Coverage

**v1 requirements:** 19 total
**Mapped:** 19/19

| Requirement | Phase |
|-------------|-------|
| PKG-01 | Phase 1 |
| PKG-02 | Phase 1 |
| PKG-03 | Phase 1 |
| PKG-04 | Phase 1 |
| ANGL-01 | Phase 2 |
| ANGL-02 | Phase 2 |
| ANGL-03 | Phase 2 |
| ANGL-04 | Phase 2 |
| ACT-01 | Phase 2 |
| ACT-02 | Phase 2 |
| ACT-03 | Phase 3 |
| PTW-01 | Phase 3 |
| PTW-02 | Phase 3 |
| PTW-03 | Phase 3 |
| PTW-04 | Phase 3 |
| UI-01 | Phase 3 |
| UI-02 | Phase 3 |
| UI-03 | Phase 3 |
| XPRT-01 | Phase 3 |

---

*Roadmap created: 2026-05-02*
