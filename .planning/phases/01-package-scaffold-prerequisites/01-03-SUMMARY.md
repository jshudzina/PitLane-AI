---
phase: 01-package-scaffold-prerequisites
plan: "03"
subsystem: pitlane-elo/studio_api, pitlane-agent/pyproject.toml, pitlane-studio/tests
tags: [pitlane-elo, studio-api, sdk-pin, integration-test, packaging, wave-1]
dependency_graph:
  requires: [01-01]
  provides: [studio_api-boundary, sdk-upper-bound, PKG-02, PKG-03-sdk-half]
  affects: [01-04, Phase-2-AngleService]
tech_stack:
  added: []
  patterns: [public-boundary-module, positional-passthrough, uv-lock-pin]
key_files:
  created:
    - packages/pitlane-elo/src/pitlane_elo/studio_api.py
  modified:
    - packages/pitlane-agent/pyproject.toml
    - packages/pitlane-studio/tests/test_studio_api.py
    - uv.lock
decisions:
  - "Positional call _detect_stories(year, round) avoids TypeError from round vs round_num kwarg mismatch"
  - "round parameter name shadows Python builtin intentionally — # noqa: A002 suppresses flake8-builtins"
  - "StorySignal re-exported as-is from pitlane_elo.stories.signals — no boundary type transformation in Phase 1 (deferred to Phase 2 AngleService)"
  - "SDK pin is metadata-only change; 0.1.47 already satisfies <0.2.0 so no reinstall needed"
metrics:
  duration_seconds: 540
  completed_date: "2026-05-03T00:00:00Z"
  tasks_completed: 3
  files_created: 1
  files_modified: 3
---

# Phase 1 Plan 03: studio_api boundary + SDK pin Summary

**One-liner:** pitlane_elo.studio_api public boundary created with (year, round) positional passthrough; claude-agent-sdk pinned <0.2.0 in uv.lock; integration test passes against live 2026 data.

---

## What Was Built

### Task 3.1 — pitlane_elo.studio_api module (commit: ee4fc12)

Created `packages/pitlane-elo/src/pitlane_elo/studio_api.py` as the stable cross-package boundary between pitlane-elo and pitlane-studio.

Key implementation choices:
- Public signature: `detect_stories(year: int, round: int) -> list[StorySignal]` per D-01
- Internal pass-through: `_detect_stories(year, round)` positionally — avoids TypeError from the `round_num` kwarg name mismatch in `pitlane_elo.stories.signals.detect_stories`
- `__all__ = ["StorySignal", "detect_stories"]` published
- `StorySignal` re-exported from `pitlane_elo.stories.signals` with no wrapping — Phase 2 AngleService owns any boundary-type transformation

The module is auto-discovered by pitlane-elo's existing hatchling build config (`packages = ["src/pitlane_elo"]`) — no pyproject.toml changes required.

### Task 3.2 — claude-agent-sdk upper-bound pin (commit: eb53588)

Updated `packages/pitlane-agent/pyproject.toml`:
- Before: `"claude-agent-sdk>=0.1.40"`
- After: `"claude-agent-sdk>=0.1.40,<0.2.0"`

Ran `uv lock` — resolved in 20ms (0.1.47 already satisfies the new constraint). The PKG-03 SDK-pin blocker listed in STATE.md is now closed. The bleach half of PKG-03 (XSS sanitization) is deferred to Plan 04.

### Task 3.3 — Activate test_studio_api.py (commit: 6b9dcae)

Removed the module-level `pytestmark = pytest.mark.xfail(...)` block from `packages/pitlane-studio/tests/test_studio_api.py`.

Test run outcome (2026 data cached locally):
- `test_studio_api_exports` — PASSED (unconditional __all__ membership check)
- `test_detect_stories_latest_2026_race` — PASSED (real 2026 data found; 7.85s)

Both tests ran against real data with no mocks. PKG-02 integration gate closed.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None. All three tasks are fully implemented with no placeholder values, hardcoded empty returns, or TODO comments in production code.

Note: Plan 04 closes the bleach half of PKG-03 (`pitlane_studio.filters.safe_html`) and PKG-04 (ArticleStore).

---

## Threat Surface Scan

No new network endpoints, auth paths, or external trust boundaries introduced. The studio_api module is an internal Python import boundary (not an HTTP route). Threat mitigations per STRIDE register:

- **T-1-03-T1 (Tampering):** Positional call `_detect_stories(year, round)` passes explicit ints with no kwarg unpacking — implemented as specified.
- **T-1-03-S1 (Supply chain):** `<0.2.0` upper bound in pyproject.toml and uv.lock — implemented.
- **T-1-03-I1 (Information Disclosure):** Internal function returns `[]` on missing snapshots, not a stack trace — unchanged behavior, accepted.
- **T-1-03-E1 (Elevation of Privilege):** `studio_api` is the conventional boundary — conventional only, not enforced. Accepted per plan.

---

## Self-Check

### Created files exist

```
[ -f packages/pitlane-elo/src/pitlane_elo/studio_api.py ] → FOUND
```

### Commits exist

- ee4fc12 — feat(01-03): create pitlane_elo.studio_api public boundary module
- eb53588 — chore(01-03): pin claude-agent-sdk<0.2.0 in pitlane-agent and refresh uv.lock
- 6b9dcae — feat(01-03): activate test_studio_api.py — remove xfail, both tests pass

### Verification run

- `uv run python -c "from pitlane_elo.studio_api import detect_stories, StorySignal"` — OK
- `uv run --directory packages/pitlane-studio pytest tests/test_studio_api.py -x` — 2 passed
- `grep 'claude-agent-sdk' packages/pitlane-agent/pyproject.toml` — `>=0.1.40,<0.2.0`
- `uv.lock` claude-agent-sdk version = "0.1.47" (satisfies <0.2.0)

## Self-Check: PASSED
