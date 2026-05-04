---
phase: 02-story-angle-detection-five-act-data-layer
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - packages/pitlane-studio/pyproject.toml
  - packages/pitlane-studio/src/pitlane_studio/services/__init__.py
  - packages/pitlane-studio/src/pitlane_studio/services/angles.py
  - packages/pitlane-studio/src/pitlane_studio/services/five_act.py
  - packages/pitlane-studio/tests/test_angle_service.py
  - packages/pitlane-studio/tests/test_five_act_mapper.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Two services (AngleService, FiveActMapper) are generally well-structured and follow the pipeline ordering documented in CONTEXT.md. The data gate, ELO cap, novelty filter, and DNF suppression all exist and are wired in the correct order. However, two blockers were found: (1) a documented fallback path for `web_search` tool type is described in the docstring but never implemented — meaning API 400 errors silently swallow the fallback, and (2) multiple lazy imports inside test methods directly violate the mandatory CLAUDE.md rule. Six warnings cover a meaningless test assertion, a missing Gate 2 warning log, an unhandled `AttributeError` in `_resolve_cmd`, a dead `non_elo` branch in `_apply_elo_type_cap`, the `dnf_suppressed` field that is never set `True`, and an unconstrained `pytest` version in test dependencies.

---

## Critical Issues

### CR-01: `_check_dnf` web_search fallback described in docstring is never implemented

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:546-588`

**Issue:** The docstring explicitly states: "Initial attempt: 'web_search_20250305'. On 400 error, fall back to 'web_search'." No retry or fallback exists. The broad `except Exception` on line 581 catches the 400 and leaves `result = False`, silently treating a tool-type rejection as "driver did not DNF." A deployment against an SDK version that rejects `web_search_20250305` would cause all slump/surprise_under candidates to be passed through the DNF filter without any actual check — defeating the CLAUDE.md constraint that DNF cross-check uses web search.

**Fix:**
```python
def _check_dnf(self, year: int, round_num: int, driver_id: str, race_name: str) -> bool:
    cache_key = (year, round_num, driver_id)
    if cache_key in self._dnf_cache:
        return self._dnf_cache[cache_key]

    result = False
    client = anthropic.Anthropic()
    prompt = (
        f'Did {driver_id} DNF or retire in the {race_name} {year} Formula 1 race? '
        f'Respond with ONLY valid JSON: {{"dnf": true, "reason": "brief"}} '
        f'or {{"dnf": false, "reason": "finished"}}'
    )
    tool_types = ["web_search_20250305", "web_search"]  # fallback per Pitfall 6
    for tool_type in tool_types:
        try:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=150,
                tools=[{"type": tool_type, "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if hasattr(block, "type") and block.type == "text":
                    text = block.text.strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        parsed = json.loads(text[start:end])
                        result = bool(parsed.get("dnf", False))
                    break
            break  # success — stop trying tool types
        except anthropic.BadRequestError:
            logger.warning("web_search tool type %r rejected — trying fallback", tool_type)
            continue
        except anthropic.AuthenticationError:
            logger.warning(
                "ANTHROPIC_API_KEY not set — skipping DNF check for %s %d R%d",
                driver_id, year, round_num,
            )
            break
        except Exception:
            logger.exception(
                "DNF check failed for %s %d R%d — defaulting to False",
                driver_id, year, round_num,
            )
            break

    self._dnf_cache[cache_key] = result
    return result
```

---

### CR-02: Lazy imports inside test methods violate mandatory CLAUDE.md rule

**File:** `packages/pitlane-studio/tests/test_angle_service.py:44-45`, `63-64`, `227`, `275`

**Issue:** CLAUDE.md states: "Always put imports at the top of the file; never use lazy imports inside functions or blocks." Four separate lazy imports appear inside test method bodies:
- Line 44-45: `from datetime import UTC, date, datetime` inside `test_data_gate_too_fresh`
- Line 63-64: `from datetime import date, timedelta` inside `test_data_gate_incomplete_laps`
- Line 227: `import json` inside `test_dnf_cache_prevents_duplicate_calls`
- Line 275: `from pitlane_elo.data import get_race_entries` inside `test_get_angles_returns_candidates`

The line 275 case uses a try/except-ImportError pattern to skip when the package is absent — but per CLAUDE.md this pattern is still prohibited; the correct approach is to use `pytest.importorskip` at module scope or a session-scoped fixture.

**Fix:** Move all imports to the top of `test_angle_service.py`:
```python
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from pitlane_elo.stories.signals import StorySignal

from pitlane_studio.services.angles import AngleCandidate, AngleService, DataNotReadyError

# For optional integration test:
pitlane_elo_data = pytest.importorskip(
    "pitlane_elo.data", reason="pitlane_elo not available"
)
```
Then reference `pitlane_elo_data.get_race_entries` in the integration test body.

---

## Warnings

### WR-01: `test_dnf_check_only_for_crisis_types` makes no meaningful assertion

**File:** `packages/pitlane-studio/tests/test_angle_service.py:206-223`

**Issue:** The test is titled "DNF check only for crisis types" and the comment says "hot_streak should not call anthropic at all." But `_check_dnf` is an internal method that always calls the Anthropic API regardless of signal type — the signal-type gate lives in `_apply_dnf_filter`. The test calls `_check_dnf` directly, which triggers an API call, then asserts only `isinstance(result, bool)` — a tautology. The mock at line 208 patches `anthropic.Anthropic` but never asserts `call_count == 0`. The test passes regardless of whether the API was called or not, giving false confidence about the gating behavior.

**Fix:** Either test the actual gate (the `_apply_dnf_filter` method) or add a `call_count` assertion:
```python
def test_dnf_check_not_triggered_for_hot_streak(self, mocker):
    """hot_streak signal bypasses DNF API entirely — checked in _apply_dnf_filter."""
    mock_check = mocker.patch.object(AngleService, "_check_dnf")
    service = AngleService()
    hot_streak = AngleCandidate(
        angle_id="h1", name="Streak", signal_type="hot_streak",
        confidence=0.9, data_rationale="r", dnf_suppressed=False,
    )
    service._apply_dnf_filter(
        candidates=[hot_streak], year=2026, round_num=5,
        race_name="Bahrain", driver_id_map={"h1": "hamilton"},
    )
    mock_check.assert_not_called()
```

---

### WR-02: Gate 2 silently skips with no log when `total_laps` is absent

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:145`

**Issue:** `if actual_laps is not None:` silently bypasses the lap-count completeness gate when `get_session_info()` returns no `total_laps` key. There is no warning log. A buggy upstream session_info response (or a session type that never populates `total_laps`) would allow incomplete race data to pass the gate with no indication. Gate 1 logs a warning when the date cannot be parsed (line 142); Gate 2 should do the same.

**Fix:**
```python
actual_laps: int | None = info.get("total_laps")
if actual_laps is None:
    logger.warning(
        "Gate 2 skipped for %d R%d — session_info returned no total_laps field",
        year, round_num,
    )
else:
    scheduled_laps = _get_scheduled_laps(year, round_num, info)
    threshold = int(scheduled_laps * 0.90)
    if actual_laps < threshold:
        raise DataNotReadyError(...)
```

---

### WR-03: `_resolve_cmd` raises unhandled `AttributeError` if name lookup fails

**File:** `packages/pitlane-studio/src/pitlane_studio/services/five_act.py:69-79`

**Issue:** `getattr(module, cmd.__name__)` at line 79 will raise `AttributeError` if the function is not accessible by `cmd.__name__` in its source module (e.g., if the function is a wrapper or its `__name__` was overridden by a decorator). This `AttributeError` propagates out of `fetch_act_data` as an uncaught exception — not logged, not wrapped in the per-command `try/except` block (which only wraps the `live_cmd(...)` call at line 121+, not the `_resolve_cmd` call at line 120). A single bad resolution would abort the entire act fetch, returning no data at all rather than a partial result.

**Fix:** Wrap `_resolve_cmd` with a fallback:
```python
def _resolve_cmd(cmd: Any) -> Any:
    try:
        module = importlib.import_module(cmd.__module__)
        return getattr(module, cmd.__name__)
    except (ImportError, AttributeError):
        logger.warning(
            "_resolve_cmd: could not resolve %r from %s — using original reference",
            cmd.__name__, cmd.__module__,
        )
        return cmd
```

---

### WR-04: `dnf_suppressed` field is initialized `False` and never set `True`

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:70`, `529`

**Issue:** `AngleCandidate.dnf_suppressed` is documented as "True if removed by DNF check (excluded from results; for logging)." But suppressed candidates are dropped from the result list entirely at line 529 and the field is never mutated. No caller ever sees an `AngleCandidate` with `dnf_suppressed=True`. The field is dead — it adds schema noise and implies logging behavior that doesn't exist.

**Fix:** Either implement the intended logging behavior (return suppressed candidates in a separate list, set the field, log them) or remove the field entirely. If the field is meant to be an audit trail, `_apply_dnf_filter` should be changed to:
```python
candidate = candidate.model_copy(update={"dnf_suppressed": True})
# then log it, but still exclude from the returned result
```

---

### WR-05: `_apply_elo_type_cap` has a dead `non_elo` branch when called from `get_angles`

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:229`, `456`

**Issue:** `get_angles()` line 229 passes only `elo_candidates` to `_apply_elo_type_cap()`. The function contains a `non_elo` list that accumulates any non-ELO candidates, but since only ELO candidates are ever passed, this branch is always empty. The non-ELO candidates are merged separately at line 232. While not a bug, the function's signature implies it handles mixed input — creating a misleading contract. A future developer could reasonably pass `all_candidates` and expect the cap to be applied correctly, when in fact the function would pass non-ELO candidates through the `non_elo` path (which would be correct, but then they'd be merged twice).

**Fix:** Clarify the contract. Either:
(a) Rename to `_apply_elo_cap_to_elo_only(candidates)` and document it only accepts ELO candidates, or
(b) Pass the full merged list `capped_elo + non_elo_candidates` through `_apply_elo_type_cap` (remove the split at the call site), which works correctly since the `non_elo` branch passes them through untouched.

---

### WR-06: `pytest` base package missing from `[test]` optional dependencies

**File:** `packages/pitlane-studio/pyproject.toml:44-47`

**Issue:** `[project.optional-dependencies] test` lists `pytest-mock>=3.15.1` but not `pytest` itself. While `pytest-mock` declares `pytest` as a dependency, this leaves the minimum required `pytest` version unconstrained in the package's own metadata. The `[tool.pytest.ini_options]` config uses `--strict-markers` and `--strict-config` which require reasonably modern pytest. A fresh install resolving the minimum `pytest-mock` transitive constraint could pull an older pytest that doesn't support these flags, failing CI.

**Fix:**
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-mock>=3.15.1",
    "httpx>=0.27",
]
```

---

## Info

### IN-01: `lap1_chaos` signal name does not match its data source

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:402-434`

**Issue:** The signal is named `lap1_chaos` and the `AngleCandidate.name` is `"Race chaos — {total_changes} position changes across the race"`. The `generate_position_changes_chart` command covers the entire race, not just lap 1. The ACT_CONFIG maps this signal to Act 2 ("Lap 1 Chaos"), creating a semantic mismatch between signal type name, angle name, and actual data. This will be confusing in the UI when the signal type appears in the angle card.

**Fix:** Rename the signal type to `race_chaos` throughout (`signal_type`, `_make_angle_id`, and any downstream consumers), or document in a comment that `lap1_chaos` is a design label (Act 2 = "Lap 1 Chaos" section) rather than a data-scope descriptor.

---

### IN-02: `test_chart_dir_created_on_init` patches module-level constant but does not reload module

**File:** `packages/pitlane-studio/tests/test_five_act_mapper.py:86-93`

**Issue:** The test patches `pitlane_studio.services.five_act._CHART_DIR` using `mocker.patch`. However, `FiveActMapper.__init__` references `_CHART_DIR` by the module-level name, so the patch does take effect. But there is a subtle issue: `_CHART_DIR` is also referenced in `_get_lap1_chaos_candidate` in `angles.py` (separate module), so if both modules share a chart dir and either is patched without the other, integration tests could write to unexpected paths. This is an info-level consistency concern, not a correctness bug for this test.

**Fix:** No immediate change needed — document that `_CHART_DIR` appears in both modules independently and both would need patching for a full integration test isolation.

---

### IN-03: `_get_wildness_candidate` confidence is not bounded if `wildness_score > 1.0`

**File:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py:344`

**Issue:** Line 344 passes `wildness` directly as `confidence` with the comment "already 0–1 normalized (season_summary.py)." This relies on upstream normalization being correct. If `season_summary.py` ever returns a wildness score above 1.0 (e.g., due to a bug or changed normalization formula), the `AngleCandidate.confidence` field would exceed 1.0, breaking the documented `0–1` range invariant checked in the integration test at line 294.

**Fix:** Defensively clamp the value:
```python
confidence=min(wildness, 1.0),
```

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
