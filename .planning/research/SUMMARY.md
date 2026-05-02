# Research Summary: PitLane Studio

**Synthesized from:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Date:** 2026-05-02

---

## Executive Summary

PitLane Studio is a structured co-authoring tool, not a general AI writer. Four academic papers (Wang 2025, Wölker & Powell 2018, Sánchez-López 2025, Bouzarth 2021) all converge on the same design principle: effective journalist tools encode intent through structured choices, gate prose generation behind plan approval, and preserve explicit space for human-only content. The product differentiator is ELO-grounded story angle detection — angles surfaced from quantified signals (SurpriseScore, ΔR̂, teammate ΔR̂ crossing), not generic sports LLM knowledge. A generic LLM cannot produce this; it requires the pitlane-elo stack that is already built and tested.

The architecture is constrained and clear. pitlane-studio is a fourth package in the uv monorepo following the pitlane-web pattern: FastAPI + uvicorn, direct Python imports from pitlane-agent and pitlane-elo (no subprocess), SQLite for article state, SSE for beat prose streaming. The frontend requires a real SPA (Svelte 5 + TipTap) rather than HTMX because drag-and-drop beat timeline and per-block prose editor require client-side state HTMX cannot cleanly manage. Substack export uses the unofficial cookie-based API with mandatory markdown fallback — LOW confidence on API stability, HIGH confidence the adapter architecture is correct.

Critical risks are front-loaded: signal noise (angle detection must rank and filter, not just threshold), DNF-driven false slump signals (existing known data quality issue in CONCERNS.md), and Substack API cookie expiry causing silent publish failure. All are addressable early if mitigation patterns are built in from the start.

---

## Stack

**Backend — HIGH confidence**
- FastAPI + uvicorn + stdlib `sqlite3` — follows pitlane-web exactly, no new patterns
- Direct Anthropic SDK (not F1Agent) — studio owns its own pipeline; no Bash tool, no workspace sandbox
- Custom `SubstackExporter` via `httpx` — no authoritative Python Substack library exists; ~50 lines of httpx beats any third-party wrapper
- Pin `claude-agent-sdk<0.2.0` immediately — pre-1.0 minor versions may break without warning

**Frontend — MEDIUM confidence**
- Svelte 5 + SvelteKit static adapter + TipTap 2.x
- TipTap's ProseMirror JSON natively matches Substack's internal format — strongest technical reason to use it
- SvelteKit static build served via FastAPI `StaticFiles` — no Node server in production

**Do NOT use:** HTMX (wrong interaction model for a document editor), `requests` (sync/blocks event loop), F1Agent (wrong abstraction for studio's direct-import pattern)

**Substack API — LOW confidence**
- Cookie-based auth (`substack.sid` + `substack.sid.sig`); POST to `/api/v1/drafts`
- Session expiry is silent; schema changes without notice
- Markdown fallback is not optional — it is the production path until API stability is validated

---

## Features

**Table stakes (must work or the tool is unusable):**
- Angle cards surface automatically on race load — no blank page
- Outline approval gate (hard gate — prose generation blocked until approved)
- Beat-by-beat prose editor with enforced placeholder hooks (journalist-only: quotes, context, causal reasoning)
- Persistent article drafts (survive browser close)
- Substack draft export + clipboard markdown fallback

**Core differentiators:**
- ELO-grounded angles with confidence signal and contextual explainability (Pasz situational downgrade)
- Five-act spine linked to FastF1 data sources (always-visible sidebar)
- Enforced placeholder hooks — the tool refuses to fill these slots, not merely invites the journalist
- Teammate battle and car/driver decoupling as first-class angle types
- Novelty filter (suppresses same driver+signal repeated from prior 2 races)

**Hard anti-features (traps that look like features):**
- One-shot full-article generation — violates Wang et al. quality findings; defeats the plan-then-write purpose
- Chat box as primary interface — Sánchez-López: structured choices outperform open-ended prompting
- Direct publish (auto-publish without review) — always export to draft, never publish directly
- Template library — angles come from ELO data, not generic sports templates
- Audience framing controls in v1 — adds complexity before core loop is validated

**Defer to v2+:** Live in-race mode, audience framing, chart auto-generation, character arc detection, multimodal pairing

---

## Architecture

**5-component service layer:**

| Service | Responsibility |
|---------|----------------|
| `AngleService` | Calls `pitlane_elo.stories.signals` + ranking/novelty/DNF filters → returns top 4–6 angle candidates |
| `FiveActMapper` | Static Python dict mapping Bouzarth acts 1–5 to specific pitlane-agent command functions |
| `PipelineOrchestrator` | Outline generation → approval gate enforcement → per-beat prose via SSE |
| `ArticleStore` | SQLite at `~/.pitlane/studio/articles.db`; status machine (draft → outline_approved → published) |
| `SubstackExporter` | Adapter interface (`export(draft) → ExportResult`); swappable; health-check before every call |

**Build order (dependency-determined):**
1. ArticleStore (no dependencies)
2. AngleService + FiveActMapper (depend on pitlane-elo imports only)
3. PipelineOrchestrator (depends on ArticleStore + Anthropic SDK)
4. FastAPI app (depends on all services)
5. SubstackExporter (depends on ArticleStore only — can parallel-track with FastAPI)
6. Svelte frontend (depends on FastAPI routes being defined)

**Key architecture decisions:**
- Import pattern, not subprocess — pitlane-agent `commands/` layer is pure Python, designed to be importable
- SQLite, not the workspace system — workspaces are ephemeral UUID scratch dirs; articles need stable identity and status transitions
- FiveActMapper is static config, not AI — act→data mapping is a design choice, not a reasoning task
- Per-beat API calls only — one call per act; inject approved outline into every beat prompt to prevent outline drift

---

## Pitfalls

| # | Pitfall | Severity | Phase |
|---|---------|----------|-------|
| 1 | Substack cookie expiry fails silently | HIGH | Phase 4 |
| 2 | Angle signal noise / fatigue (too many candidates) | HIGH | Phase 2 |
| 3 | DNF false slump signals (2023+ DNFs all "retired") | HIGH | Phase 2 |
| 4 | Outline drift (prose ignores approved outline) | HIGH | Phase 3 |
| 5 | FastF1 data incomplete 2–4h post-race | MEDIUM | Phase 2 |
| 6 | uv API drift on claude-agent-sdk | MEDIUM | Phase 1 |
| 7 | XSS via `| safe` template pattern (inherited) | MEDIUM | Phase 1 |
| 8 | Workspace disk accumulation (inherited) | LOW | Phase 1 |

**Top mitigations:**
- Substack: adapter interface from day one; health-check + `Content-Type` validation before every call; markdown as co-equal export path
- Angles: field-relative ranking (top 2 per signal type); novelty filter; cross-check DNF record before surfacing driver crisis angle
- Outline drift: 5 separate API calls (one per beat/act), not one long call with outline prepended
- Phase 1 prerequisites: pin `claude-agent-sdk<0.2.0`, add `bleach.clean()` sanitization, define `pitlane_elo.studio_api` interface module

---

## Roadmap Implications

**Suggested 4-phase structure:**

**Phase 1 — Package Scaffold + Prerequisites**
Fix inherited tech debt and establish cross-package integration surface before business logic. ArticleStore built and tested. Deliverable: installable `pitlane-studio` package with SQLite store and FastAPI skeleton.

**Phase 2 — Story Angle Detection + Signal Quality**
The core differentiator. AngleService with ranking/novelty/Pasz filters, DNF cross-check, FastF1 completeness gate, FiveActMapper. Must precede UI — signal problems are invisible once card selection UI exists. Also: Substack API live endpoint validation (determines v1 export path).

**Phase 3 — Plan-Then-Write Pipeline + Co-Authoring UI**
PipelineOrchestrator (outline → approval gate → per-beat SSE prose), FastAPI routes, Svelte frontend (AngleCard, Timeline, BeatEditor via TipTap, ExportPanel). Single coherent phase because outline is not useful without the approval gate or the UI to interact with it.

**Phase 4 — Substack Export + Publishing Path**
SubstackExporter with cookie health-check, adapter interface, markdown serializer. Can be parallel-tracked with Phase 3 since its only dependency is ArticleStore.

---

## Research Flags

**Must validate before Phase 2:** Substack API live endpoint test — POST `/api/v1/drafts` with real cookies; confirm `draft_body` format; confirm required cookie names. Determines whether "Export to Substack" exists in v1 or markdown becomes primary.

**Must validate before Phase 3:** TipTap + Svelte 5 headless integration — TipTap is React-primary in its docs; verify `onMount` pattern and `getJSON()` output compatibility with Substack's ProseMirror variant.

**Ongoing:** ELO threshold recalibration after 6 races of 2026 data (`ΔR̂_3race > 0.5` may need tuning); DNF reclassification pipeline progress.

---

## Confidence Summary

| Area | Confidence |
|------|------------|
| Backend stack | HIGH |
| Frontend stack (Svelte/TipTap) | MEDIUM |
| Substack API | LOW |
| Features scope | HIGH |
| Architecture | HIGH |
| Pitfalls | HIGH |
| ELO thresholds for 2026 | MEDIUM |

**Overall: MEDIUM-HIGH** — backend, architecture, and features are well-grounded; Substack API and TipTap/Svelte integration need live validation in early phases.
