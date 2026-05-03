# PitLane Studio

## What This Is

PitLane Studio is a web-based co-authoring interface for F1 journalism, built as a new `pitlane-studio` package inside the existing uv monorepo. It consumes the ELO signal data and FastF1 race telemetry already produced by pitlane-agent and pitlane-elo, and transforms them into structured narrative story angles, five-act race timelines, and plan-then-write prose drafts that can be exported to Substack. The user is the sole writer; this is a personal productivity tool, not a multi-tenant product.

## Core Value

Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

## Requirements

### Validated

These capabilities already exist in the codebase and are the foundation the new interface builds on.

- ✓ ELO rating engine (EndureElo + SpeedElo) — existing, tested
- ✓ Story signal detection (`pitlane_elo/stories/signals.py`) — hot streaks, teammate shifts, slumps, ELO deltas
- ✓ FastF1 data access — lap times, telemetry, tyre strategy, race control messages, standings, session info
- ✓ Claude Agent SDK integration — the AI reasoning layer is wired up
- ✓ Workspace management — `~/.pitlane/workspaces/<uuid>/` file-based state
- ✓ FastAPI web server infrastructure — pitlane-web package pattern available to follow

### Validated in Phase 1 (2026-05-03)

- ✓ `pitlane-studio` package — uv workspace member, FastAPI /health, click CLI on port 8001
- ✓ `pitlane_elo.studio_api` public boundary — `detect_stories(year, round) -> list[StorySignal]`, tested against live 2026 data
- ✓ `claude-agent-sdk<0.2.0` pin — supply chain drift risk eliminated
- ✓ `safe_html()` Jinja2 filter — two-pass XSS sanitizer (regex + bleach) returning `markupsafe.Markup`
- ✓ `ArticleStore` — SQLAlchemy Core, strict state machine (draft→outline_generated→outline_approved→published), SQLite persistence

### Active

- [ ] Story angle detection layer — maps race ELO signals + telemetry outputs to 4–6 narrative frames per race (e.g. "Dominant Tyre Management," "Comeback Narrative," "Strategic Gamble That Backfired")
- [ ] Five-act race timeline spine — maps existing pitlane commands to Bouzarth et al.'s five dramatic acts: qualifying/grid (inciting incident), lap-1 chaos (complications), pit window (crisis), final stint (climax), championship implications (resolution)
- [ ] Plan-then-write pipeline — outline approval step before any prose generation; AI generates beat-by-beat prose only after journalist approves structure
- [ ] Structured co-authoring UI — story angle cards (select, not blank page); race timeline with draggable beats; beat-by-beat prose editor with placeholder hooks for journalist-only content (quotes, context, causal reasoning)
- [ ] Substack export — unofficial Substack API integration with markdown copy/paste fallback when API is unavailable

### Out of Scope

- Character arc detection (Direction 5) — v2; angle detection covers the most important cases first
- Multimodal chart pairing (Direction 6) — v2; manual chart insertion is sufficient for v1
- Audience framing controls (Direction 7) — v2; single writing voice for now
- Multi-user access, authentication — personal tool, no auth needed
- Official Substack API — does not exist yet; unofficial API is best available option
- Mobile UI — desktop web only

## Context

This project evolves the existing PitLane CLI/agent into a purpose-built writing interface. The research document (`pitlane-research-summary.md`) grounds the design in four papers:

- **Wölker & Powell (2018)** — algorithmic sports content is credible; the journalist's differentiated value is context, causality, and interviews. Design consequence: always include structured placeholder hooks for human-only content.
- **Bouzarth et al. (2021)** — five-act dramatic structure applies to sports analytics; named archetypes make data emotionally accessible. Design consequence: story angles are named narrative frames, not raw stats.
- **Sánchez-López et al. (2025)** — effective tools encode journalist intent through structured choices, not free-text prompting. Design consequence: story angle cards + outline approval, not a chat box.
- **Wang et al. (2025)** — LLMs degrade after the first 40–60% of long output; plan-then-write pipelines consistently outperform streaming full-text. Design consequence: never generate a full article in one pass.

The existing ELO system design document (`docs/F1_ELO_Story_Detection_System_Design.md`) establishes that endure-Elo outperforms speed-Elo and the Bayesian model for prediction; this is the signal source for story angle detection.

## Constraints

- **Tech stack**: Python uv monorepo — new `pitlane-studio` package follows the same pattern as pitlane-web. No separate repo.
- **Integration**: Must call into pitlane-agent and pitlane-elo packages; no duplicating data access or ELO logic.
- **Export**: Substack is the publishing destination. Unofficial API is acceptable; markdown fallback is required.
- **Scope**: Personal tool — no auth, no multi-tenancy, no SLA.
- **Frontend**: Modern enough to support card-based selection UI and a structured editor; Jinja2 + HTMX or a lightweight SPA are both acceptable.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate package (`pitlane-studio`) vs. extending pitlane-web | Co-authoring UI has a fundamentally different interaction model than the chat interface; mixing them creates a confusing product | ✓ Validated in Phase 1 |
| Unofficial Substack API with markdown fallback | No official API exists; unofficial is best available; markdown fallback prevents publisher lock-in | — Pending |
| v1 = 3 directions only (angle detection, plan-then-write, five-act) | Research doc explicitly prioritizes these; shipping fewer things lets the core loop get validated before adding audience framing, chart pairing, etc. | — Pending |
| EndureElo as the signal source for story angles | Empirically outperforms speed-Elo and Bayesian model; already implemented and tested | ✓ Good |
| Two-pass XSS sanitization (regex pre-pass + bleach) | bleach strip=True keeps inner text of script tags; regex pre-pass removes inner content before bleach runs | ✓ Validated in Phase 1 |
| ArticleStore uses SQLAlchemy Core only (no ORM) | State machine is simple and explicit; ORM adds no value over Core for a 3-field state table | ✓ Validated in Phase 1 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-03 after Phase 1 completion*
