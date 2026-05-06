---
plan: 03-04
phase: 03-plan-then-write-pipeline-co-authoring-ui
status: complete
completed: 2026-05-05
---

# 03-04: FastAPI Pipeline Routes + Tests — Summary

## What Was Built

- `packages/pitlane-studio/src/pitlane_studio/routers/__init__.py` — package marker
- `packages/pitlane-studio/src/pitlane_studio/routers/acts.py` — `GET /acts/{year}/{round_num}` returns all 5 acts with label + data keys
- `packages/pitlane-studio/src/pitlane_studio/routers/races.py` — `GET /races/years`, `GET /races/{year}/rounds`
- `packages/pitlane-studio/src/pitlane_studio/routers/articles.py` — full /articles/* pipeline:
  - `POST /articles` — create article
  - `GET /articles/{id}/angles` — 422 on DataNotReadyError
  - `POST /articles/{id}/outline` — generates outline via PipelineOrchestrator
  - `PATCH /articles/{id}/outline` — persists beat edits to BeatStore
  - `POST /articles/{id}/approve` — transitions to outline_approved
  - `GET /articles/{id}/beats/{n}/stream` — 409 gate check BEFORE StreamingResponse; SSE proxy to stream_beat()
- `packages/pitlane-studio/src/pitlane_studio/app.py` — routers registered before StaticFiles mount; `/` serves SvelteKit static build
- `packages/pitlane-studio/pyproject.toml` — `pytest-asyncio>=1.3.0` added; `asyncio_mode = "auto"` configured
- All 10 xfail stubs converted to 9 passing tests (some stubs merged into richer tests)

## Self-Check: PASSED

- [x] GET /health returns 200
- [x] GET /acts/{year}/{round} returns dict with 5 acts, each having label + data keys
- [x] GET /races/years returns list of integer years
- [x] POST /articles creates article and returns article_id
- [x] POST /articles/{id}/approve transitions to outline_approved
- [x] GET /articles/{id}/beats/{n}/stream returns 409 when status != outline_approved
- [x] PATCH /articles/{id}/outline persists beats (save_outline_beats position fallback fix)
- [x] No xfail markers remain in test_pipeline.py or test_routes.py
- [x] Full suite: 59 passed, 2 skipped — no regressions

## Deviations

- `BeatStore.save_outline_beats()` had `position=beat["position"]` (KeyError when called from `generate_outline` via `OutlineBeat.model_dump()` which has no `position` field). Fixed to `beat.get("position", beat["beat_number"])`.
- Test count: 9 tests (not 10 stubs → 10 tests) — `test_sse_format` and `test_beat_done_payload` stubs merged into the more thorough `test_stream_beat_yields_correct_sse_events`.

## key-files

created:
  - packages/pitlane-studio/src/pitlane_studio/routers/__init__.py
  - packages/pitlane-studio/src/pitlane_studio/routers/acts.py
  - packages/pitlane-studio/src/pitlane_studio/routers/articles.py
  - packages/pitlane-studio/src/pitlane_studio/routers/races.py
modified:
  - packages/pitlane-studio/src/pitlane_studio/app.py
  - packages/pitlane-studio/src/pitlane_studio/store/beat_store.py
  - packages/pitlane-studio/tests/test_pipeline.py
  - packages/pitlane-studio/tests/test_routes.py
  - packages/pitlane-studio/pyproject.toml
