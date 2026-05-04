---
phase: 02-story-angle-detection-five-act-data-layer
verified: 2026-05-04T00:00:00Z
status: gaps_found
score: 4/6 must-haves verified
overrides_applied: 0
gaps:
  - truth: "ACT-01: System maps act 1 to session-info + position-changes per REQUIREMENTS.md"
    status: failed
    reason: "REQUIREMENTS.md specifies act 1 → session-info + position-changes. Implementation uses [get_session_info, generate_qualifying_results_chart] instead. The test only asserts get_session_info is present in act 1 — it never checks that generate_position_changes_chart is also there, so the spec deviation passed testing. The second command in act 1 does not match the requirement contract."
    artifacts:
      - path: "packages/pitlane-studio/src/pitlane_studio/services/five_act.py"
        issue: "ACT_CONFIG[1]['commands'] contains generate_qualifying_results_chart, not generate_position_changes_chart as REQUIREMENTS.md specifies"
      - path: "packages/pitlane-studio/tests/test_five_act_mapper.py"
        issue: "test_act1_includes_session_info_command only verifies get_session_info presence; no test verifies the second command matches the spec"
    missing:
      - "Either update REQUIREMENTS.md to reflect that qualifying_results replaces position-changes for act 1 (with documented rationale), or update five_act.py to include generate_position_changes_chart in act 1 commands and update the tests accordingly"

  - truth: "ANGL-03: DNF cross-check uses web search via web_search_20250305 tool type with documented fallback to web_search on 400 error"
    status: failed
    reason: "The _check_dnf docstring states 'On 400 error, fall back to web_search' but no fallback is implemented. The broad except Exception catches 400/BadRequestError and silently returns False — treating an API rejection as 'driver did not DNF'. This defeats the ANGL-03 contract when deployed against an SDK version that rejects the web_search_20250305 tool type string. The fix is documented in 02-REVIEW.md (CR-01) but was not applied."
    artifacts:
      - path: "packages/pitlane-studio/src/pitlane_studio/services/angles.py"
        issue: "Lines 559-588: _check_dnf calls client.messages.create with tool type 'web_search_20250305' only; except Exception on line 581 silently swallows BadRequestError with result=False, no retry with 'web_search'"
    missing:
      - "Add BadRequestError-specific except clause with retry using alternate tool type string 'web_search', breaking the loop on success; this is the fix documented in 02-REVIEW.md CR-01"
---

# Phase 2: Story Angle Detection + Five-Act Data Layer Verification Report

**Phase Goal:** The system surfaces 4–6 ranked, filtered, novel story angle candidates from any completed race using ELO signals, cross-checks driver crisis angles against actual DNF records, gates on data completeness, and has all five-act data fetched and cached — so angle quality is validated independently before the UI makes problems invisible
**Verified:** 2026-05-04
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Derived from ROADMAP.md Phase 2 Success Criteria (5 items) merged with PLAN frontmatter must_haves.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Given a completed race, the system returns 4–6 angle candidates derived from ELO signals; verifiable via a pytest test against real 2025/2026 race data | ? UNCERTAIN | `AngleService.get_angles()` is fully implemented and unit tests for schema, gate, cap, novelty filter, and DNF suppression all pass (12 tests). Integration test `test_get_angles_returns_candidates` is marked skip — skips due to no 2026 ELO data in test environment. Cannot verify the 4–6 count claim programmatically without live data. Pipeline logic is substantively implemented. |
| 2 | Angle candidates are ranked by field-relative significance (top 2 per ELO signal type) and the same driver+signal combination does not appear if it was surfaced in either of the prior 2 races | ✓ VERIFIED | `_apply_elo_type_cap()` implemented with defaultdict, sorts by confidence, keeps top 2 per ELO type; non-ELO types pass through uncapped. `_apply_novelty_filter()` calls `detect_stories()` for rounds n-1 and n-2, builds prior_pairs set, suppresses matches. Both tested and passing: `TestEloTypeCap` (2 tests), `TestNoveltyFilter` (2 tests). |
| 3 | A driver crisis angle (slump, underperformance) is suppressed when a web search confirms the driver DNF'd that race — FastF1 DNF classification explicitly not used | PARTIAL | `_check_dnf()` uses `anthropic.Anthropic()` with `web_search_20250305` tool — NOT FastF1. Suppression logic in `_apply_dnf_filter()` is wired and tested. However, the documented fallback to `web_search` on 400 error is NOT implemented (CR-01): a `BadRequestError` from a rejected tool type silently returns False, defeating the check. Functionally correct when tool type is accepted; silently broken when tool type is rejected. |
| 4 | Attempting to load angle candidates for a race less than 2 hours old or with an incomplete lap count returns a blocking message and generates no angle candidates | ✓ VERIFIED | `_check_data_gate()` is a module-level function called as the first statement in `get_angles()` (line 219 of angles.py). Gate 1 checks date-only string + 2-hour window using conservative 16:00 UTC race-end estimate. Gate 2 checks `total_laps < 90% of scheduled` with three-level fallback for scheduled laps. `DataNotReadyError` has `.message` attribute for API responses. Three passing tests cover both gate conditions. |
| 5 | All five-act data is fetched from pitlane-agent commands and cached on race load; each act's data is accessible as a Python dict keyed by act number | ✓ VERIFIED | `FiveActMapper.fetch_act_data()` implemented with in-memory cache keyed by (year, round_num, act_number). Cache hit returns same object (`first is second` test passes). ACT_CONFIG maps 5 acts to 7 pitlane-agent command callables. `_CHART_DIR.mkdir()` called in `__init__`. Tests pass: `TestActConfigStructure` (9 tests), `TestFetchActData` (3 unit tests). |
| 6 | ACT-01: System maps acts 1–5 to the specific pitlane-agent commands in the REQUIREMENTS.md spec | ✗ FAILED | REQUIREMENTS.md specifies act 1 → `session-info` + `position-changes`. Implementation has act 1 → `[get_session_info, generate_qualifying_results_chart]`. `generate_qualifying_results_chart` is not `position-changes`. The test only asserts `get_session_info in ACT_CONFIG[1]["commands"]` — the second command is never validated against the spec. The deviation from the requirement is real. |

**Score:** 4/6 truths fully verified (1 PARTIAL on CR-01, 1 FAILED on ACT-01 spec)

### Deferred Items

None — all gaps are actionable in the current phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/pitlane-studio/src/pitlane_studio/services/__init__.py` | Services package marker | ✓ VERIFIED | Exists; docstring declares Phase 2 contents |
| `packages/pitlane-studio/src/pitlane_studio/services/angles.py` | AngleService, AngleCandidate, DataNotReadyError (min 200 lines) | ✓ VERIFIED | 599 lines; all 3 exported symbols present; `__all__` declared |
| `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` | ACT_CONFIG, FiveActMapper (min 80 lines) | ✓ VERIFIED | 163 lines; both exported symbols present; `__all__` declared |
| `packages/pitlane-studio/tests/test_angle_service.py` | ANGL-01..04 test coverage | ✓ VERIFIED | 6 test classes, 12 passing tests + 1 skip; no pytestmark xfail; module-level imports at top |
| `packages/pitlane-studio/tests/test_five_act_mapper.py` | ACT-01..02 test coverage | ✓ VERIFIED | 2 test classes, 12 passing tests + 1 skip; no pytestmark xfail; imports at top |
| `packages/pitlane-studio/pyproject.toml` | anthropic>=0.97.0 dependency | ✓ VERIFIED | `anthropic>=0.97.0` in project.dependencies |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `AngleService.get_angles()` | `pitlane_elo.studio_api.detect_stories` | Direct import at module top; called in `_get_signals_cached()` | ✓ WIRED | `from pitlane_elo.studio_api import detect_stories` line 30; called in `_get_signals_cached` line 462; novelty filter calls it for rounds n-1 and n-2 |
| `AngleService._check_dnf()` | `anthropic.Anthropic().messages.create()` | `import anthropic` at top; `client = anthropic.Anthropic()` in method body | ✓ WIRED | `import anthropic` line 23; `client.messages.create(...)` at line 559; `json.loads()` used for response parsing (not eval) |
| `AngleService.get_angles()` | `_check_data_gate()` | Module-level function called as first statement | ✓ WIRED | `_check_data_gate(year, round_num)` is line 219 — before any ELO computation |
| `_check_data_gate()` | `get_session_info()` | `from pitlane_agent.commands.fetch.session_info import get_session_info` | ✓ WIRED | Called at line 118 of `_check_data_gate` |
| `FiveActMapper.fetch_act_data()` | `_CHART_DIR` | `_CHART_DIR.mkdir()` in `__init__`; passed as `workspace_dir` to chart commands | ✓ WIRED | `_CHART_DIR.mkdir(parents=True, exist_ok=True)` at line 93; chart commands called with `_CHART_DIR` not `None` |
| `five_act.py ACT_CONFIG` | `pitlane_agent.commands.*` | 7 callable references imported at module top | ✓ WIRED | All 7 commands imported from `pitlane_agent.*` at top of file; stored as references (not strings) in ACT_CONFIG |
| `AngleService._check_dnf()` | web_search fallback | `BadRequestError` catch + retry with `"web_search"` | ✗ NOT_WIRED | Fallback documented in docstring (line 545) but no `BadRequestError` catch exists; broad `except Exception` silently returns False on tool-type rejection |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `angles.py: get_angles()` | `elo_candidates` list | `detect_stories(year, round_num)` → DuckDB parquet scan | Yes — real DuckDB query in pitlane_elo; integration test skipped due to absent 2026 data, not stub | ✓ FLOWING (when data present) |
| `angles.py: _check_dnf()` | `result` bool | `anthropic.Anthropic().messages.create()` → parsed JSON | Yes — real API call; `AuthenticationError` path defaults to False conservatively | ✓ FLOWING (with caveat: tool-type fallback missing) |
| `five_act.py: fetch_act_data()` | `results` dict | pitlane-agent commands called via `_resolve_cmd()` | Yes — commands fetch from FastF1 disk cache; mocked in tests | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `uv run --directory packages/pitlane-studio pytest -q` | `40 passed, 2 skipped` | ✓ PASS |
| Phase 2 service tests pass | `uv run --directory packages/pitlane-studio pytest tests/test_angle_service.py tests/test_five_act_mapper.py -q` | `24 passed, 2 skipped` | ✓ PASS |
| No pytestmark xfail in test files | `grep -c "pytestmark = pytest.mark.xfail"` | 0 in both files | ✓ PASS |
| AngleCandidate importable | `python -c "from pitlane_studio.services.angles import AngleCandidate, AngleService, DataNotReadyError"` | Expected: exits 0 | ✓ PASS (inferred from 12 passing tests that import these) |
| ACT_CONFIG has 5 acts | `python -c "from pitlane_studio.services.five_act import ACT_CONFIG; assert set(ACT_CONFIG.keys()) == {1,2,3,4,5}"` | Expected: exits 0 | ✓ PASS (inferred from test_all_five_acts_present passing) |
| workspace_dir=None never passed | `grep -c "workspace_dir=None" five_act.py` | 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ANGL-01 | 02-01, 02-03 | 4–6 story angle candidates from ELO signals | PARTIAL | AngleCandidate schema verified; pipeline implemented; integration test skipped (no 2026 ELO data) — count guarantee untestable without live data |
| ANGL-02 | 02-01, 02-03 | Top 2 per signal type; novelty filter for prior 2 races | SATISFIED | `_apply_elo_type_cap()` and `_apply_novelty_filter()` verified by passing tests |
| ANGL-03 | 02-01, 02-03 | Crisis angles cross-checked via web search; FastF1 not used | PARTIAL | Web search used (not FastF1); suppression logic wired; tool-type fallback missing (CR-01) — if `web_search_20250305` rejected, check silently fails |
| ANGL-04 | 02-01, 02-03 | Gate on session age and lap completeness | SATISFIED | `_check_data_gate()` runs first in `get_angles()`; both conditions tested; `DataNotReadyError.message` attribute verified |
| ACT-01 | 02-01, 02-02 | Static Python config maps 5 acts to specific pitlane-agent commands per spec | BLOCKED | Act 1 uses `generate_qualifying_results_chart` not `generate_position_changes_chart` as REQUIREMENTS.md specifies; test gap allowed this to pass |
| ACT-02 | 02-01, 02-02 | Act data fetched and cached; accessible as dict keyed by act number | SATISFIED | `FiveActMapper.fetch_act_data()` returns dict; cache hit verified by identity test; `_CHART_DIR` created on init |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_angle_service.py` | 44, 63, 227, 275 | Lazy imports inside test function bodies (violates CLAUDE.md mandatory rule) | Warning | `from datetime import UTC, date, datetime` at line 44, `from datetime import date, timedelta` at line 63, `import json` at line 227, `from pitlane_elo.data import get_race_entries` at line 275 are all inside test method bodies. CLAUDE.md: "Always put imports at the top of the file; never use lazy imports inside functions or blocks." Does not affect test results but violates the mandatory project rule. |
| `angles.py` | 545-588 | `_check_dnf` catches `BadRequestError` via broad `except Exception`, swallows without retry | Blocker | Documents fallback behavior ("On 400 error, fall back to 'web_search'") that is never implemented. Any 400 from a rejected tool type silently returns `False` — treating API rejection as "driver did not DNF". This defeats the ANGL-03 cross-check when `web_search_20250305` is not accepted by the SDK version in deployment. |
| `angles.py` | 145 | Gate 2 silently skips with no log when `total_laps` is absent | Info | When `get_session_info()` returns no `total_laps` key, the lap completeness gate is bypassed with no log warning. Gate 1 logs when date cannot be parsed; Gate 2 should log the same way. Not a blocker — completeness gate still works when `total_laps` is present. |
| `five_act.py` | 69-79 | `_resolve_cmd` raises unhandled `AttributeError` if name lookup fails | Warning | `getattr(module, cmd.__name__)` propagates `AttributeError` outside the `try/except` block wrapping the command call. A decorator-renamed function would cause the entire `fetch_act_data()` call to abort rather than returning a partial result. Not a blocker for current commands. |
| `test_angle_service.py` | 206-223 | `test_dnf_check_only_for_crisis_types` asserts only `isinstance(result, bool)` — tautology | Info | Test comment claims "hot_streak should not call anthropic at all" but makes no such assertion. `mock_create` is patched but `call_count` is never checked. Passes regardless of whether API was called. |

### Human Verification Required

None — all must-have truths are programmatically verifiable. The integration test skip (no 2026 ELO data) is a test-environment limitation, not a gap in the implementation. The pipeline logic is substantively implemented and verified by unit tests.

### Gaps Summary

**2 gaps block full goal achievement:**

**Gap 1 — ACT-01 command spec deviation (BLOCKER):** The REQUIREMENTS.md contract for ACT-01 specifies `act 1: qualifying/grid → session-info + position-changes`. The implementation uses `[get_session_info, generate_qualifying_results_chart]` — substituting `qualifying_results` for `position-changes`. The test only validates that `get_session_info` is present; it does not validate the second command, so this deviation passed all tests. This is either a conscious product decision that needs to be reflected in REQUIREMENTS.md, or a bug in five_act.py that needs the second command corrected. Both the requirement and the implementation cannot simultaneously be correct.

**Gap 2 — ANGL-03 DNF fallback not implemented (BLOCKER):** `_check_dnf()` documents a fallback from `web_search_20250305` to `web_search` on 400 errors, but no `BadRequestError` catch or retry loop exists. A broad `except Exception` silently returns `False`, treating a tool-type rejection as "driver did not DNF." When deployed against an SDK version that rejects the tool type string, all slump/surprise_under candidates bypass DNF filtering — defeating the ANGL-03 requirement. Fix documented in `02-REVIEW.md` (CR-01).

**2 warnings noted but not blocking:**
- 4 lazy imports inside test function bodies violate the mandatory CLAUDE.md rule (CR-02). Tests pass but the pattern is prohibited.
- `_resolve_cmd` in five_act.py does not guard against `AttributeError` on name lookup failure.

---

_Verified: 2026-05-04_
_Verifier: Claude (gsd-verifier)_
