# PitLane Studio — Project Guide

## Project

PitLane Studio is a web-based F1 journalism co-authoring interface, added as a new `pitlane-studio` package to the existing uv monorepo (pitlane-agent + pitlane-elo + pitlane-web). It transforms ELO signal data and FastF1 race telemetry into story angle cards, five-act race timelines, and plan-then-write prose drafts with Substack markdown export.

**Core value:** Surface 4–6 data-grounded story angles from any race and guide the journalist through an outline-first drafting pipeline, so writing time goes entirely to voice, context, and quotes — not finding the story.

**Planning:** `.planning/` — see `ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`

## Current Phase

Phase 1: Package Scaffold + Prerequisites (Not started)

Run `/gsd-progress` to check current state.

## GSD Workflow

This project uses the GSD (Get Shit Done) workflow. Always follow these rules:

- **Before starting work:** Check `.planning/STATE.md` for current phase and context
- **Before planning a phase:** Run `/gsd-discuss-phase <N>` to gather context
- **Before executing:** Run `/gsd-plan-phase <N>` to create the execution plan
- **After executing:** Run `/gsd-verify-work` to confirm requirements are met
- **Mode:** Interactive — confirm at each major step

## Monorepo Rules

- **Package manager:** `uv` only — never use `pip` directly
- **Install all packages:** `uv sync --all-packages`
- **Run tests:** `uv run --directory packages/<package-name> pytest`
- **Add dependency:** `uv add --directory packages/<package-name> <dep>`
- **New package follows:** the pattern in `packages/pitlane-web/` (FastAPI + uvicorn)

## Architecture

```
pitlane-studio (new)
  └── imports from: pitlane-agent (commands/), pitlane-elo (studio_api)
  └── does NOT use: F1Agent, workspace system, Bash tool sandboxing
  └── own state: SQLite at ~/.pitlane/studio/articles.db
  └── frontend: Svelte 5 + TipTap 2.x (SvelteKit static build)
  └── API: FastAPI + uvicorn on port 8001
```

Key services to build (in dependency order):
1. `ArticleStore` — SQLite state machine
2. `AngleService` — ELO signals → ranked angle candidates
3. `FiveActMapper` — static dict: acts 1-5 → pitlane-agent commands
4. `PipelineOrchestrator` — outline → approval gate → per-beat SSE prose
5. `SubstackExporter` — v2; adapter interface only in v1

## Key Constraints

- **DNF cross-check:** Use web search, NOT FastF1 classification (FastF1 DNF data unreliable)
- **Plan-then-write:** Always 5 separate API calls (one per beat), never one long generation
- **Hard approval gate:** Beat prose generation is blocked until outline is explicitly approved — no bypass
- **Placeholder hooks:** Tool never fills journalist-only slots (quote, context, causal reasoning)
- **Substack API:** LOW confidence; markdown copy/paste is the v1 export path; Substack is v2
- **SDK pin:** `claude-agent-sdk<0.2.0` — enforce in pyproject.toml
- **XSS:** All Jinja2 `| safe` outputs must go through `bleach.clean()`

## Imports & Dependencies

```python
# Correct: import pitlane-agent commands directly
from pitlane_agent.commands.fetch.session import get_session_info
from pitlane_agent.commands.analyze.strategy import get_tyre_strategy

# Correct: use studio_api interface
from pitlane_elo.studio_api import detect_stories

# Wrong: subprocess / CLI invocation
# Wrong: using F1Agent for studio's pipeline
```

## Testing

- Tests in `packages/pitlane-studio/tests/`
- Cross-package integration test must call `detect_stories()` with real data (no mocks)
- ArticleStore integration test must hit a real SQLite file (no mocks)
- Run all tests: `uv run pytest` from repo root
