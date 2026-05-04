# Phase 2: Story Angle Detection + Five-Act Data Layer - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 4 (2 service modules + 2 test files)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/pitlane-studio/src/pitlane_studio/services/angles.py` | service | request-response (pipeline) | `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` | role-match (same Pydantic+class pattern; no SQLite) |
| `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` | service | request-response (dispatch) | `packages/pitlane-elo/src/pitlane_elo/studio_api.py` + `article_store.py` | role-match (thin dispatch; module-level constant + class with in-memory cache) |
| `packages/pitlane-studio/tests/test_angle_service.py` | test | — | `packages/pitlane-studio/tests/test_article_store.py` | exact (same framework, same fixture pattern, same class-per-feature grouping) |
| `packages/pitlane-studio/tests/test_five_act_mapper.py` | test | — | `packages/pitlane-studio/tests/test_article_store.py` | exact |

---

## Pattern Assignments

### `packages/pitlane-studio/src/pitlane_studio/services/angles.py` (service, pipeline)

**Primary analog:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py`
**Secondary analog:** `packages/pitlane-elo/src/pitlane_elo/stories/signals.py` (signal dataclass + pipeline structure)

**Imports pattern** — copy from `article_store.py` lines 11–18, adapted:
```python
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime, timedelta

import anthropic
from pydantic import BaseModel

from pitlane_elo.studio_api import detect_stories
from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_agent.commands.fetch.season_summary import get_season_summary
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart

logger = logging.getLogger(__name__)
```

Key rules: `from __future__ import annotations` first (line 1 of `article_store.py`); all imports at top — no lazy imports anywhere in the file (CLAUDE.md + project memory).

**Pydantic BaseModel pattern** — copy from `article_store.py` lines 32–42, adapted:
```python
class AngleCandidate(BaseModel):
    """Ranked story angle candidate derived from ELO and race-level signals."""

    angle_id: str          # deterministic hash: sha256(f"{year}:{round}:{signal_type}:{driver_id}")[:16]
    name: str              # human-readable angle title
    signal_type: str       # hot_streak|slump|surprise_over|surprise_under|teammate_shift|
                           # wildness|standings_shift|lap1_chaos
    confidence: float      # 0–1 normalized signal magnitude
    data_rationale: str    # narrative string
    dnf_suppressed: bool   # True if suppressed by DNF check (excluded from results; for logging)
```

No SQLAlchemy table needed. `AngleCandidate` is in-memory only — contrast with `ArticleRecord` which has a corresponding `articles_table`.

**Custom exception pattern** — no direct analog in codebase; use Python convention:
```python
class DataNotReadyError(Exception):
    """Raised by AngleService.get_angles() when session data is not yet reliable.

    Attributes:
        message: User-facing explanation suitable for the 422 response body.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
```

**Service class pattern** — copy from `article_store.py` lines 74–148 (class structure with `__init__` + public methods + `_now_iso`-style private helpers):
```python
class AngleService:
    """Detects and ranks story angle candidates for a completed race."""

    def __init__(self) -> None:
        self._dnf_cache: dict[tuple[int, int, str], bool] = {}
        # Optional: cache prior-round novelty signals to avoid triple DuckDB scan
        self._signal_cache: dict[tuple[int, int], list] = {}

    def get_angles(self, year: int, round_num: int) -> list[AngleCandidate]:
        """Run the full pipeline; raises DataNotReadyError if data gate blocks."""
        ...
```

Note: `article_store.py` uses `self._engine` as internal state; `AngleService` uses `self._dnf_cache` and optionally `self._signal_cache` — same private attribute convention.

**In-memory cache pattern** — copy from `article_store.py` line 79 (`metadata.create_all(self._engine)` pattern for initializing state in `__init__`), adapted to dict:
```python
def __init__(self) -> None:
    self._dnf_cache: dict[tuple[int, int, str], bool] = {}
```

**Error handling pattern** — copy from `article_store.py` lines 107–110 (raise `ValueError` on not-found; same pattern for `DataNotReadyError`):
```python
# From article_store.py lines 107–110
if row is None:
    raise ValueError(f"Article {article_id!r} not found")
```
Adapted: raise `DataNotReadyError` with a journalist-facing message string as `self.message`.

**Datetime UTC pattern** — copy from `article_store.py` line 71:
```python
# article_store.py line 71
from datetime import UTC, datetime

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
```
Adapted for data gate: `datetime.now(UTC)` for session age comparison.

**hashlib deterministic ID pattern** — same as `article_store.py` import; use `hashlib.sha256`:
```python
# From RESEARCH.md verified pattern
hash_input = f"{year}:{round_num}:{signal_type}:{driver_id}"
angle_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
```

**`__all__` export pattern** — copy from `article_store.py` line 148:
```python
__all__ = ["AngleCandidate", "AngleService", "DataNotReadyError"]
```

---

### `packages/pitlane-studio/src/pitlane_studio/services/five_act.py` (service, dispatch)

**Primary analog:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` (class with `__init__` + in-memory cache dict)
**Secondary analog:** `packages/pitlane-elo/src/pitlane_elo/studio_api.py` (module-level constant + thin dispatch)

**Imports pattern** — ALL imports at top (CLAUDE.md rule; same as `article_store.py` lines 11–18). The `ACT_CONFIG` dict references callables imported here:
```python
from __future__ import annotations

import logging
from pathlib import Path

from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_agent.commands.fetch.race_control import get_race_control_messages
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart
from pitlane_agent.commands.analyze.lap_times import generate_lap_times_chart
from pitlane_agent.commands.analyze.qualifying_results import generate_qualifying_results_chart
from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart

logger = logging.getLogger(__name__)
```

**Module-level constant pattern** — `studio_api.py` uses module-level `__all__` and re-export; here use a module-level dict (no direct analog in codebase — this is a new pattern, but follows the `_TRANSITIONS` dict in `article_store.py` lines 24–28 for module-level constants):
```python
# From article_store.py lines 24–28 — module-level constant dict pattern
_TRANSITIONS: dict[str, str] = {
    "draft": "outline_generated",
    ...
}
```
Adapted:
```python
# Module-level constant — not a class attribute
_CHART_DIR: Path = Path.home() / ".pitlane" / "studio" / "charts"

ACT_CONFIG: dict[int, dict] = {
    1: {
        "label": "Qualifying / Grid",
        "commands": [get_session_info, generate_qualifying_results_chart],
    },
    2: {
        "label": "Lap 1 Chaos",
        "commands": [get_race_control_messages, generate_position_changes_chart],
    },
    3: {
        "label": "Pit Window",
        "commands": [generate_tyre_strategy_chart, get_race_control_messages],
    },
    4: {
        "label": "Final Stint",
        "commands": [generate_lap_times_chart, generate_position_changes_chart],
    },
    5: {
        "label": "Championship Implications",
        "commands": [get_driver_standings],
    },
}
```

**In-memory cache + `mkdir` pattern** — copy from `article_store.py` lines 65–67 (`path.parent.mkdir(parents=True, exist_ok=True)`) and `__init__` state initialization:
```python
# From article_store.py lines 65–67
path.parent.mkdir(parents=True, exist_ok=True)
```
Adapted:
```python
class FiveActMapper:
    """Fetches and caches act-specific data for a race."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int], dict] = {}
        _CHART_DIR.mkdir(parents=True, exist_ok=True)
```

**`generate_position_changes_chart` signature** — confirmed at `position_changes.py` lines 161–170:
```python
def generate_position_changes_chart(
    year: int,
    gp: str,          # accepts str; round number as int also works per FastF1
    session_type: str,
    drivers: list[str] | None = None,
    top_n: int | None = None,
    workspace_dir: Path | None = None,  # MUST supply — None crashes at line 201
    ...
) -> dict:
```
`workspace_dir` default is `None` but line 201 does `workspace_dir / "charts" / filename` — always pass `_CHART_DIR`.

**`__all__` export pattern** — copy from `article_store.py` line 148:
```python
__all__ = ["ACT_CONFIG", "FiveActMapper"]
```

---

### `packages/pitlane-studio/tests/test_angle_service.py` (test)

**Analog:** `packages/pitlane-studio/tests/test_article_store.py` (exact match — same test class grouping, same `pytest.raises` pattern, same fixture injection)

**File header pattern** — copy from `test_article_store.py` lines 1–12:
```python
"""PKG-XX integration/unit tests — AngleService and AngleCandidate."""

from __future__ import annotations

import pytest

from pitlane_studio.services.angles import AngleCandidate, AngleService, DataNotReadyError
```

**Test class grouping pattern** — copy from `test_article_store.py` lines 13–58 (one class per feature/requirement):
```python
class TestAngleCandidateSchema:
    def test_valid_fields_accepted(self): ...

class TestDataGate:
    def test_data_gate_too_fresh(self): ...
    def test_data_gate_incomplete_laps(self): ...

class TestEloTypeCap:
    def test_top_2_per_elo_signal_type(self): ...

class TestNoveltyFilter:
    def test_novelty_filter_suppresses_repeated_driver_signal(self): ...

class TestDnfCheck:
    def test_dnf_check_only_for_crisis_types(self): ...
    def test_dnf_cache_prevents_duplicate_calls(self): ...

class TestGetAnglesIntegration:
    """Integration tests — require real ELO snapshots; skip if absent."""
    def test_get_angles_returns_candidates(self): ...
```

**`pytest.raises` pattern** — copy from `test_article_store.py` lines 33–34:
```python
with pytest.raises(ValueError):
    tmp_store.transition_status(article_id, "published")
```
Adapted:
```python
with pytest.raises(DataNotReadyError):
    service.get_angles(year=2026, round_num=5)
```

**`pytest.mark.skip` pattern for integration tests** — no direct analog; use standard pytest:
```python
pytest.importorskip("pitlane_elo")  # or:
@pytest.mark.skipif(not elo_snapshots_exist(), reason="No ELO snapshots available")
```

**Fixture usage pattern** — `conftest.py` lines 12–21 shows `tmp_path` injection via `pytest.fixture`. New tests can add fixtures in `conftest.py` following the same `@pytest.fixture()` decorator style:
```python
# conftest.py pattern (lines 12–21)
@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "articles.db"

@pytest.fixture()
def tmp_store(tmp_db_path: Path) -> ArticleStore:
    return ArticleStore(db_path=tmp_db_path)
```
Adapted for angles: a fixture providing a fresh `AngleService()` instance (no db path needed).

---

### `packages/pitlane-studio/tests/test_five_act_mapper.py` (test)

**Analog:** `packages/pitlane-studio/tests/test_article_store.py` (exact match)

**File header pattern** — copy from `test_article_store.py` lines 1–12:
```python
"""Unit and integration tests — FiveActMapper and ACT_CONFIG."""

from __future__ import annotations

import pytest

from pitlane_studio.services.five_act import ACT_CONFIG, FiveActMapper
```

**Test class grouping pattern** — one class per requirement (ACT-01, ACT-02):
```python
class TestActConfigStructure:
    """ACT-01: static config dict maps acts 1–5 with correct callables."""
    def test_all_five_acts_present(self): ...
    def test_each_act_has_label_and_commands(self): ...
    def test_commands_are_callable(self): ...

class TestFetchActData:
    """ACT-02: fetch_act_data returns data and caches subsequent calls."""
    def test_cache_returns_same_object_on_second_call(self): ...
    # Integration test (real FastF1, skippable):
    def test_fetch_act1_returns_dict(self): ...
```

**Assert pattern** — copy from `test_article_store.py` lines 16–19:
```python
record = tmp_store.get(article_id)
assert record.status == "draft"
assert record.race_year == 2026
```
Adapted:
```python
assert 1 in ACT_CONFIG
assert "label" in ACT_CONFIG[1]
assert callable(ACT_CONFIG[1]["commands"][0])
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` line 11
**Apply to:** All new `.py` source files and test files
```python
from __future__ import annotations
```

### Pydantic BaseModel (in-memory data object)
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` lines 32–42
**Apply to:** `angles.py` (`AngleCandidate`)
```python
from pydantic import BaseModel

class ArticleRecord(BaseModel):
    """Pydantic representation of an article row (D-04)."""
    id: str
    race_year: int
    race_round: int
    angle_id: str | None
    status: str
    created_at: str
    updated_at: str
```

### Module-level `__all__`
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` line 148
**Apply to:** `angles.py`, `five_act.py`
```python
__all__ = ["ArticleRecord", "ArticleStore", "get_engine"]
```

### `Path.mkdir(parents=True, exist_ok=True)` for filesystem setup
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` lines 65–67
**Apply to:** `five_act.py` (`_CHART_DIR.mkdir(...)` in `FiveActMapper.__init__`)
```python
def get_engine(db_path: Path | None = None) -> Engine:
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")
```

### `datetime.now(UTC)` pattern
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` lines 13, 71
**Apply to:** `angles.py` data completeness gate
```python
from datetime import UTC, datetime

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
```

### In-memory dict cache on class instance
**Source:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py` lines 77–79 (engine stored as `self._engine` in `__init__`)
**Apply to:** `angles.py` (`self._dnf_cache`), `five_act.py` (`self._cache`)
```python
def __init__(self, db_path: Path | None = None) -> None:
    self._engine: Engine = get_engine(db_path)
    metadata.create_all(self._engine)
```

### `pytest.raises` for custom exceptions
**Source:** `packages/pitlane-studio/tests/test_article_store.py` lines 33–34
**Apply to:** `test_angle_service.py` (DataNotReadyError tests)
```python
with pytest.raises(ValueError):
    tmp_store.transition_status(article_id, "published")
```

### Fixture injection via `conftest.py`
**Source:** `packages/pitlane-studio/tests/conftest.py` lines 12–21
**Apply to:** `test_angle_service.py`, `test_five_act_mapper.py` — add new fixtures to the same `conftest.py` file
```python
@pytest.fixture()
def tmp_store(tmp_db_path: Path) -> ArticleStore:
    """ArticleStore backed by a temporary SQLite file."""
    return ArticleStore(db_path=tmp_db_path)
```

### Direct import boundary pattern (public API re-export)
**Source:** `packages/pitlane-elo/src/pitlane_elo/studio_api.py` lines 1–34
**Apply to:** `services/__init__.py` (optional) — thin re-export of `AngleService`, `AngleCandidate`, `DataNotReadyError`, `FiveActMapper`, `ACT_CONFIG` if needed by Phase 3 routes
```python
from pitlane_elo.stories.signals import StorySignal
from pitlane_elo.stories.signals import detect_stories as _detect_stories

def detect_stories(year: int, round: int) -> list[StorySignal]:
    return _detect_stories(year, round)

__all__ = ["StorySignal", "detect_stories"]
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `services/__init__.py` | config | — | Package init — boilerplate only; no logic analog needed |
| `DataNotReadyError` exception class | utility | — | No custom exception classes exist in the codebase yet; use standard Python `Exception` subclass pattern |
| DNF cross-check via `anthropic` SDK | service | request-response | No Anthropic SDK calls exist in any package; follow RESEARCH.md Pattern 6 for tool call structure |

---

## Key Signals Confirmed from Source

| Signal | Source File | Verified Field |
|---|---|---|
| `StorySignal.signal_type` | `signals.py` line 48 | `hot_streak | slump | surprise_over | surprise_under | teammate_shift` |
| `StorySignal.driver_id` | `signals.py` line 51 | Ergast driverId slug |
| `StorySignal.value` | `signals.py` line 53 | Raw signal magnitude |
| `StorySignal.threshold` | `signals.py` line 55 | Threshold crossed |
| `StorySignal.narrative` | `signals.py` line 56 | Ready-to-use string → `AngleCandidate.data_rationale` |
| `SeasonRaceSummary.wildness_score` | `season_summary.py` line 53 | `float` (0–1 already normalized) |
| `SeasonRaceSummary.round` | `season_summary.py` line 41 | `int` — filter by this |
| `get_driver_standings` signature | `driver_standings.py` line 12 | `(year: int, round_number: int \| None = None) -> dict` |
| `SessionInfo.date` | `session_info.py` line 94 | `str \| None` — date-only string e.g. `"2026-03-16"` |
| `SessionInfo.total_laps` | `session_info.py` line 95 | `int \| None` — actual laps completed, NOT scheduled |
| `SessionInfo.drivers[*].grid_position` | `session_info.py` line 38 | `int \| None` — use for lap-1 chaos signal |
| `generate_position_changes_chart` workspace_dir | `position_changes.py` line 201 | `workspace_dir / "charts" / filename` — crashes if `None` |

---

## Metadata

**Analog search scope:** `packages/pitlane-studio/`, `packages/pitlane-elo/`, `packages/pitlane-agent/commands/`
**Files read:** 10 source files
**Pattern extraction date:** 2026-05-03
