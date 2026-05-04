---
phase: 02-story-angle-detection-five-act-data-layer
reviewed: 2026-05-04T12:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - packages/pitlane-studio/src/pitlane_studio/services/angles.py
  - packages/pitlane-studio/tests/test_angle_service.py
  - packages/pitlane-studio/tests/test_five_act_mapper.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 02: Gap-Closure Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

This is a gap-closure review targeting the two CRs from the prior pass (CR-01: DNF fallback not implemented; CR-02: lazy imports in test file). Both critical issues have been correctly resolved. CR-01 is fixed with an accurate retry loop using `BadRequestError` catch-and-continue semantics. CR-02 is fixed with all imports moved to module level and `pytest.importorskip` used at module scope. However, the CR-02 fix introduced a new regression: placing `pytest.importorskip` at module scope causes the entire test module to be skipped when `pitlane_elo.data` is unavailable, not just the integration test that requires it. Six pre-existing warnings from the prior review remain unaddressed (WR-01 through WR-06); those are carried forward and not re-raised here.

---

## Critical Issues

None.

---

## Warnings

### WR-01: `pytest.importorskip` at module scope skips all tests when `pitlane_elo.data` is absent

**File:** `packages/pitlane-studio/tests/test_angle_service.py:14-16`

**Issue:** The CR-02 fix moved `pytest.importorskip("pitlane_elo.data", ...)` to module scope, which is the correct pattern for avoiding lazy imports. However, `pytest.importorskip` at module scope causes pytest to skip the **entire module** when the import fails — not just `TestGetAnglesIntegration` (the only class that calls `get_race_entries`). All unit tests in the file (`TestAngleCandidateSchema`, `TestDataGate`, `TestEloTypeCap`, `TestNoveltyFilter`, `TestDnfCheck`) would be silently skipped on any system where `pitlane_elo` is not installed. These unit tests mock all external dependencies and have no actual need for `pitlane_elo.data`. This is a regression from the original implementation, which at least ran the unit tests in all environments.

**Fix:** Use a module-level `try/except ImportError` assignment and a conditional `pytest.skip` guard inside the integration test. Since CLAUDE.md prohibits lazy imports *inside functions or blocks*, the correct pattern is an explicit conditional at the integration test level using a module-level sentinel:

```python
# At module top level — CLAUDE.md compliant: this is not a lazy import,
# it is a conditional assignment that remains at module scope.
try:
    from pitlane_elo.data import get_race_entries as _get_race_entries
except ImportError:
    _get_race_entries = None  # type: ignore[assignment]

# Inside TestGetAnglesIntegration.test_get_angles_returns_candidates:
def test_get_angles_returns_candidates(self):
    if _get_race_entries is None:
        pytest.skip("pitlane_elo not available")
    entries = _get_race_entries(2026, session_type="R")
    ...
```

Alternatively, if the project decides `pitlane_elo` is always required in the test environment, the current `pytest.importorskip` at module scope is acceptable — but that decision should be documented in the test file so the skip behavior is intentional, not accidental.

---

## Pre-existing Issues (Carried Forward, Not Re-raised)

The following findings from the prior review (02-REVIEW.md) remain unaddressed. They are not re-raised as new findings in this gap-closure pass but are listed for tracking:

- **WR-01 (prior):** `test_dnf_check_only_for_crisis_types` makes no meaningful assertion — calls `_check_dnf` directly and only asserts `isinstance(result, bool)`.
- **WR-02 (prior):** Gate 2 silently skips with no log when `total_laps` is absent from session_info.
- **WR-03 (prior):** `_resolve_cmd` raises unhandled `AttributeError` if `getattr(module, cmd.__name__)` fails (five_act.py — out of this review's file scope).
- **WR-04 (prior):** `AngleCandidate.dnf_suppressed` is never set `True`; the field is dead.
- **WR-05 (prior):** `_apply_elo_type_cap` is called with only ELO candidates but contains a `non_elo` branch that is always empty at the call site.
- **WR-06 (prior):** `pytest` itself is not pinned in `[project.optional-dependencies] test` (pyproject.toml — out of this review's file scope).

---

## CR-01 Verification: DNF Fallback Now Correctly Implemented

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:554-587`

The fix is correct. `tool_types = ["web_search_20250305", "web_search"]` drives a `for` loop where `BadRequestError` triggers `continue` (advances to the next tool type) and success triggers `break`. `AuthenticationError` and other exceptions still `break` conservatively. The new test `test_dnf_check_falls_back_to_web_search_on_bad_request` correctly validates both the retry count (2 API calls) and the fallback tool type used in the second call.

One non-blocking observation: `json.loads(text[start:end])` at line 569 can raise `json.JSONDecodeError`, which is caught by `except Exception` and breaks the loop — meaning a malformed LLM response on the first tool type prevents the fallback from being tried. This is conservative behavior (defaults to `False`, does not suppress the candidate), but the fallback designed for tool-type rejection does not activate for parse failures. This behavior is consistent with the intent and is not a blocker.

---

## CR-02 Verification: Imports Moved to Module Level

**File:** `packages/pitlane-studio/tests/test_angle_service.py:1-16`

The fix is correct in spirit. `json`, `datetime`, `UTC`, `date`, `timedelta`, `anthropic`, `pytest`, `StorySignal`, `AngleCandidate`, `AngleService`, and `DataNotReadyError` are all at module scope. `pytest.importorskip` replaces the prior `try/except ImportError` inside a test method. The CLAUDE.md rule is satisfied. However, this introduces the regression documented in WR-01 above.

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
