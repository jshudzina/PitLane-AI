---
phase: 2
slug: story-angle-detection-five-act-data-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `packages/pitlane-studio/pyproject.toml` (pytest section) |
| **Quick run command** | `uv run --directory packages/pitlane-studio pytest tests/ -x -q` |
| **Full suite command** | `uv run --directory packages/pitlane-studio pytest` |
| **Estimated runtime** | ~30–60 seconds (FastF1 cache warmup on first run) |

---

## Sampling Rate

- **After every task commit:** Run `uv run --directory packages/pitlane-studio pytest tests/ -x -q`
- **After every plan wave:** Run `uv run --directory packages/pitlane-studio pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | ANGL-01 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | ANGL-02 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py::test_novelty_filter -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | ANGL-03 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py::test_dnf_suppression -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | ANGL-04 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py::test_data_not_ready -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | ACT-01 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_five_act_mapper.py -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | ACT-02 | — | N/A | unit (xfail stub) | `uv run --directory packages/pitlane-studio pytest tests/test_five_act_mapper.py::test_fetch_act_data -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_angle_service.py` — xfail stubs for ANGL-01 through ANGL-04
- [ ] `tests/test_five_act_mapper.py` — xfail stubs for ACT-01 and ACT-02
- [ ] `packages/pitlane-studio/pyproject.toml` — add `anthropic` dependency (missing; required for DNF cross-check)

*Existing infrastructure (conftest.py, pytest config) may carry over from Phase 1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DNF web search returns correct JSON | ANGL-03 | Requires live Claude API + web search tool call | Call `AngleService.get_angles()` for a race with a confirmed DNF driver; verify suppressed candidate has `dnf_suppressed=True` in debug output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
