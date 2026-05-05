---
phase: 03-plan-then-write-pipeline-co-authoring-ui
plan: "02"
subsystem: pitlane-studio/services
tags: [pipeline, orchestrator, sse, anthropic, async, pydantic]
dependency_graph:
  requires:
    - 03-01 (BeatStore, beat_store.py)
  provides:
    - PipelineOrchestrator service class
    - OutlineBeat Pydantic model
    - _detect_placeholders() placeholder detection
  affects:
    - 03-03 (routers will call generate_outline() and stream_beat())
tech_stack:
  added: []
  patterns:
    - "Module-level AsyncAnthropic singleton (safe at import time per RESEARCH.md Pattern 5)"
    - "SSE format: event: <type>\\ndata: <json>\\n\\n"
    - "INSERT OR REPLACE upsert via BeatStore (parameterized — no string concatenation in SQL)"
    - "max_tokens=1024 cap on streaming calls (DoS mitigation)"
key_files:
  created:
    - packages/pitlane-studio/src/pitlane_studio/services/pipeline.py
  modified: []
decisions:
  - "AsyncAnthropic instantiated at module level — not inside generator — per RESEARCH.md Pattern 5 (Assumption A3)"
  - "Approval gate is NOT enforced in stream_beat() — enforced in route handler (Wave 1 routers)"
  - "Beat streaming model: claude-sonnet-4-5-20250929; outline model: claude-haiku-4-5"
  - "full_prose_parts list declared before async with block — avoids UnboundLocalError in error handler"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-05T23:28:06Z"
  tasks_total: 1
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 3 Plan 02: PipelineOrchestrator Summary

**One-liner:** PipelineOrchestrator with sync outline generation (haiku-4-5), async SSE beat streaming (sonnet-4-5), and regex placeholder detection for [JOURNALIST: quote/context/causal] patterns.

## What Was Built

`packages/pitlane-studio/src/pitlane_studio/services/pipeline.py` — the core plan-then-write service.

### Exports

- `OutlineBeat` — Pydantic model: `beat_number`, `beat_title`, `data_anchors`, `act_number | None`
- `PipelineOrchestrator` — service class with two public methods

### Module-Level Declarations

- `_async_client = AsyncAnthropic()` — singleton instantiated at import time (RESEARCH.md Pattern 5)
- `_detect_placeholders(prose: str) -> list[dict]` — regex scanner for `[JOURNALIST: quote|context|causal]` patterns; returns `[{"type": ..., "offset": ...}]` dicts
- `_build_outline_prompt(...)` — non-streaming prompt builder; includes five act labels from ACT_CONFIG and act data summaries; instructs LLM to return JSON array of 5 beat objects with placeholder references
- `_build_beat_prompt(...)` — per-beat streaming prompt builder; includes full outline context (D-02 compliance) and act data; requires all three placeholder types verbatim in prose

### PipelineOrchestrator.generate_outline()

Sync method. Flow:
1. `FiveActMapper().fetch_act_data()` for acts 1-5
2. `_build_outline_prompt()` with angle metadata
3. `anthropic.Anthropic().messages.create(model="claude-haiku-4-5", max_tokens=2048)`
4. JSON parse → `[OutlineBeat(**b) for b in raw_beats]`
5. `BeatStore().save_outline_beats(article_id, [b.model_dump() for b in outline_beats])`
6. `ArticleStore().transition_status(article_id, "outline_generated")`
7. Return list of OutlineBeat

Error handling: `AuthenticationError` → log warning + re-raise; `JSONDecodeError` → log error + re-raise with message "Outline LLM response was not valid JSON"; `Exception` → log exception + re-raise.

### PipelineOrchestrator.stream_beat()

Async generator. Flow:
1. Load outline from BeatStore, convert to OutlineBeat list
2. Find beat by number — yield `event: error` and return if not found
3. Load act data via FiveActMapper
4. Yield `event: beat_start` with beat metadata
5. Build prompt with full outline context (D-02)
6. `async with _async_client.messages.stream(model="claude-sonnet-4-5-20250929", max_tokens=1024)` — yield `event: token` per chunk
7. After stream: `_detect_placeholders(prose)`, `BeatStore().save_beat(...)`, yield `event: beat_done`
8. Catch Exception → yield `event: error` with `retryable: True`

## Threat Model Compliance

| Threat ID | Mitigation |
|-----------|------------|
| T-03-02-01 | BeatStore uses parameterized SQLAlchemy Core inserts (INSERT OR REPLACE) — no string concatenation in SQL |
| T-03-02-02 | `max_tokens=1024` cap on stream_beat(); FastAPI client disconnect closes async generator |
| T-03-02-03 | Accepted — personal tool, no untrusted external input to prompt builders |
| T-03-02-04 | Accepted — AuthenticationError logs warning only, never logs the key value |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Prerequisite artifacts from 03-01 verified as already committed**
- **Found during:** Pre-execution check
- **Issue:** Plan 02 depends on `beat_store.py` from plan 01. Investigation found that 03-01 was already fully executed (commits `32e7d7f`, `c0c749a`, `f9ad277`).
- **Fix:** Confirmed artifacts exist, verified imports work, proceeded directly to plan 02 tasks.
- **Files modified:** None (no fix required)

### Commit Blocker

**CRITICAL: pipeline.py is created and verified but NOT committed due to sandbox permission denial.**

All `git add` commands were denied by the sandbox permission system during this execution. The file:
- Exists at `packages/pitlane-studio/src/pitlane_studio/services/pipeline.py`
- Imports cleanly: `from pitlane_studio.services.pipeline import PipelineOrchestrator, OutlineBeat` exits 0
- All 50 tests pass (plus 2 skipped, 10 xfailed)

**Manual commit required:**
```bash
git add packages/pitlane-studio/src/pitlane_studio/services/pipeline.py
git commit -m "feat(03-02): add PipelineOrchestrator with outline generation and SSE streaming"
```

## Test Results

```
50 passed, 2 skipped, 10 xfailed in 1.28s
```

- 42 pre-existing tests (Phases 1 + 2): all pass
- 8 new BeatStore tests (03-01): all pass
- 10 xfail stubs (test_pipeline.py + test_routes.py): all XFAIL as expected
- 2 skipped: expected live-data integration skips

## Self-Check

| Check | Result |
|-------|--------|
| pipeline.py exists | FOUND |
| Import test | PASSED (exits 0) |
| class PipelineOrchestrator count | 1 |
| class OutlineBeat count | 1 |
| _async_client = AsyncAnthropic() at module level | 1 |
| generate_outline() method | FOUND at line 196 |
| async def stream_beat() | FOUND at line 288 |
| _detect_placeholders count (def + call) | 2 |
| JOURNALIST references | 10 |
| quote/context/causal pattern coverage | 17 matches |
| All pre-existing tests still pass | 50 passed |
| Commit created | BLOCKED (sandbox permission denial) |

## Self-Check: PARTIAL

Pipeline.py created and verified. Commit blocked by sandbox permissions — requires manual `git add` and `git commit` as documented above.
