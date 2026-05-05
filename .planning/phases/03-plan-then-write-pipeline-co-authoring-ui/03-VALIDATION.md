---
phase: 3
slug: plan-then-write-pipeline-co-authoring-ui
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `packages/pitlane-studio/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --directory packages/pitlane-studio pytest tests/test_beat_store.py tests/test_pipeline.py tests/test_routes.py -x` |
| **Full suite command** | `uv run --directory packages/pitlane-studio pytest` |
| **Estimated runtime** | ~30 seconds (Python only; frontend spike is manual) |

---

## Sampling Rate

- **After every task commit:** Run quick run command above
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| beat-store-01 | beat_store | 0 | D-06, D-07 | — | N/A | unit | `pytest tests/test_beat_store.py::test_save_beat -x` | ❌ W0 | ⬜ pending |
| beat-store-02 | beat_store | 0 | D-07 | — | N/A | unit | `pytest tests/test_beat_store.py::test_save_outline_beats -x` | ❌ W0 | ⬜ pending |
| pipeline-01 | pipeline | 0 | PTW-01 | — | N/A | unit | `pytest tests/test_pipeline.py::test_generate_outline -x` | ❌ W0 | ⬜ pending |
| pipeline-02 | pipeline | 0 | PTW-03 | — | N/A | unit | `pytest tests/test_pipeline.py::test_stream_beat_events -x` | ❌ W0 | ⬜ pending |
| pipeline-03 | pipeline | 0 | PTW-03 | — | `data: {...}\n\n` format correct | unit | `pytest tests/test_pipeline.py::test_sse_format -x` | ❌ W0 | ⬜ pending |
| pipeline-04 | pipeline | 0 | PTW-04 | T: LLM injection | Placeholder nodes not raw HTML | unit | `pytest tests/test_pipeline.py::test_placeholder_detection -x` | ❌ W0 | ⬜ pending |
| pipeline-05 | pipeline | 0 | PTW-04 | — | N/A | unit | `pytest tests/test_pipeline.py::test_beat_done_payload -x` | ❌ W0 | ⬜ pending |
| routes-01 | routes | 0 | ACT-03 | — | N/A | unit | `pytest tests/test_routes.py::test_acts_route -x` | ❌ W0 | ⬜ pending |
| routes-02 | routes | 0 | UI-01 | — | N/A | unit | `pytest tests/test_routes.py::test_angles_route -x` | ❌ W0 | ⬜ pending |
| routes-03 | routes | 0 | PTW-02 | T: EoP gate bypass | 409 before SSE body starts | unit | `pytest tests/test_routes.py::test_stream_beat_gate_409 -x` | ❌ W0 | ⬜ pending |
| routes-04 | routes | 0 | PTW-02 | — | N/A | unit | `pytest tests/test_routes.py::test_approve_outline -x` | ❌ W0 | ⬜ pending |
| routes-05 | routes | 0 | UI-03 | — | N/A | unit | `pytest tests/test_routes.py::test_patch_outline -x` | ❌ W0 | ⬜ pending |
| frontend-spike | spike | 0 | D-10 | — | N/A | manual | Browser console — TipTap onMount + getJSON round-trip | ❌ W0 | ⬜ pending |
| xprt-01 | export | 2 | XPRT-01 | — | N/A | manual | Browser console — export serializes placeholder nodes | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_beat_store.py` — stubs for D-06, D-07 (beats + outline_beats tables)
- [ ] `tests/test_pipeline.py` — stubs for PTW-01, PTW-03, PTW-04 (PipelineOrchestrator mocked)
- [ ] `tests/test_routes.py` — stubs for ACT-03, UI-01, UI-03, PTW-02 gate
- [ ] `src/pitlane_studio/store/beat_store.py` — BeatStore skeleton
- [ ] `src/pitlane_studio/services/pipeline.py` — PipelineOrchestrator skeleton
- [ ] `src/pitlane_studio/routers/` — router package directory
- [ ] `frontend/` — SvelteKit app directory + TipTap spike file (D-10)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TipTap onMount instantiation + getJSON round-trip | D-10 | JS/browser interaction; no pytest equivalent | Wave 0 spike: open browser, run spike Svelte component, verify editor initializes and `editor.getJSON()` returns custom node JSON |
| Placeholder hook nodes render visually distinct | PTW-04, UI-02 | Visual/CSS verification | Stage 3: load beat editor, confirm green/blue/yellow inline node styling per UI-SPEC |
| Markdown export serializes placeholder nodes | XPRT-01 | Client-side clipboard; no server involved | Click "Copy Markdown"; paste into text editor; confirm `[JOURNALIST: quote]` etc. appear |
| SSE beats stream sequentially in browser | PTW-03 | Network timing / UX behavior | Open DevTools Network tab; approve outline; confirm 5 sequential SSE requests, each with `beat_start`/`token`/`beat_done` events |
| Approve Outline button is absent before outline generated | PTW-02 | UI gate — browser state | Load app before outline generation; confirm approve button not rendered in DOM |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
