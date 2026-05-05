# Phase 3: Plan-Then-Write Pipeline + Co-Authoring UI — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 14 (new/modified files classified)
**Analogs found:** 10 / 14 (4 frontend files have no codebase analog — new tech stack)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/pitlane_studio/store/beat_store.py` | store | CRUD | `store/article_store.py` | exact |
| `src/pitlane_studio/services/pipeline.py` | service | streaming + CRUD | `services/angles.py` | role-match |
| `src/pitlane_studio/routers/articles.py` | router | request-response + streaming | `app.py` | role-match |
| `src/pitlane_studio/routers/acts.py` | router | request-response | `app.py` | role-match |
| `src/pitlane_studio/routers/races.py` | router | request-response | `app.py` | role-match |
| `src/pitlane_studio/routers/__init__.py` | config | — | `services/five_act.py` (module init pattern) | partial |
| `src/pitlane_studio/app.py` (modify) | config | request-response | `app.py` (self) | exact |
| `tests/test_beat_store.py` | test | CRUD | `tests/test_article_store.py` | exact |
| `tests/test_pipeline.py` | test | streaming | `tests/test_angle_service.py` | role-match |
| `tests/test_routes.py` | test | request-response | `tests/test_app.py` | role-match |
| `frontend/svelte.config.js` | config | — | none | none |
| `frontend/vite.config.ts` | config | — | none | none |
| `frontend/src/lib/extensions/placeholder-nodes.ts` | utility | transform | none | none |
| `frontend/src/lib/components/*.svelte` | component | request-response + streaming | none | none |

---

## Pattern Assignments

### `src/pitlane_studio/store/beat_store.py` (store, CRUD)

**Analog:** `packages/pitlane-studio/src/pitlane_studio/store/article_store.py`

**Imports pattern** (lines 1–18):
```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.engine import Engine
```

**Module-level docstring convention** (lines 1–9 of article_store.py):
```python
"""BeatStore — SQLAlchemy Core SQLite persistence for outline_beats and beats tables.

Per CONTEXT.md:
  D-06: beats table: (article_id, beat_number, beat_title, prose, placeholder_markers_json, created_at, updated_at)
  D-07: outline_beats table: (article_id, beat_number, beat_title, data_anchors, act_number, position)
  SQLAlchemy Core only — Table/Column/MetaData; no ORM layer.
"""
```

**MetaData + Table declaration pattern** (lines 44–56 of article_store.py):
```python
metadata = MetaData()

outline_beats_table = Table(
    "outline_beats",
    metadata,
    Column("article_id", String, primary_key=True),   # composite PK (Pitfall 7)
    Column("beat_number", Integer, primary_key=True),  # composite PK (Pitfall 7)
    Column("beat_title", String, nullable=False),
    Column("data_anchors", Text, nullable=True),
    Column("act_number", Integer, nullable=True),
    Column("position", Integer, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

beats_table = Table(
    "beats",
    metadata,
    Column("article_id", String, primary_key=True),   # composite PK (Pitfall 7)
    Column("beat_number", Integer, primary_key=True),  # composite PK (Pitfall 7)
    Column("beat_title", String, nullable=False),
    Column("prose", Text, nullable=True),
    Column("placeholder_markers_json", Text, nullable=True),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)
```

**Engine construction pattern** (lines 59–71 of article_store.py):
```python
def _default_db_path() -> Path:
    return Path.home() / ".pitlane" / "studio" / "articles.db"


def get_engine(db_path: Path | None = None) -> Engine:
    """Construct an engine, creating parent dirs first."""
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
```

**Class __init__ + metadata.create_all pattern** (lines 74–80 of article_store.py):
```python
class BeatStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._engine: Engine = get_engine(db_path)
        metadata.create_all(self._engine)
```

**Read pattern with engine.connect** (lines 105–121 of article_store.py):
```python
def get_outline_beats(self, article_id: str) -> list[OutlineBeatRecord]:
    with self._engine.connect() as conn:
        rows = conn.execute(
            outline_beats_table.select()
            .where(outline_beats_table.c.article_id == article_id)
            .order_by(outline_beats_table.c.position)
        ).fetchall()
    return [OutlineBeatRecord(...row._mapping) for row in rows]
```

**Write pattern with engine.begin (upsert for SQLite)** — use `INSERT OR REPLACE` for idempotent persistence (RESEARCH.md Open Question 3):
```python
def save_beat(self, article_id: str, beat_number: int, beat_title: str,
              prose: str, placeholder_markers: list) -> None:
    import json
    now = _now_iso()
    with self._engine.begin() as conn:
        conn.execute(
            beats_table.insert().prefix_with("OR REPLACE").values(
                article_id=article_id,
                beat_number=beat_number,
                beat_title=beat_title,
                prose=prose,
                placeholder_markers_json=json.dumps(placeholder_markers),
                created_at=now,
                updated_at=now,
            )
        )
```

Note: Do NOT use lazy imports. The `import json` above is illustrative of what NOT to do — import `json` at the top of the module per CLAUDE.md.

**Pydantic record model pattern** (lines 32–41 of article_store.py):
```python
class OutlineBeatRecord(BaseModel):
    article_id: str
    beat_number: int
    beat_title: str
    data_anchors: str | None
    act_number: int | None
    position: int
    created_at: str
    updated_at: str

class BeatRecord(BaseModel):
    article_id: str
    beat_number: int
    beat_title: str
    prose: str | None
    placeholder_markers_json: str | None
    created_at: str
    updated_at: str
```

**`__all__` convention** (line 148 of article_store.py):
```python
__all__ = ["BeatRecord", "BeatStore", "OutlineBeatRecord", "get_engine"]
```

---

### `src/pitlane_studio/services/pipeline.py` (service, streaming + CRUD)

**Analog:** `packages/pitlane-studio/src/pitlane_studio/services/angles.py`

**Imports pattern** (lines 1–31 of angles.py):
```python
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from pitlane_agent.commands.fetch.session_info import get_session_info
from pitlane_elo.studio_api import detect_stories
from pitlane_studio.store.article_store import ArticleRecord, ArticleStore
from pitlane_studio.store.beat_store import BeatStore, OutlineBeatRecord

logger = logging.getLogger(__name__)
```

Note: Import `AsyncAnthropic` (not just `anthropic.Anthropic`) — `AsyncAnthropic` is required for SSE generator context (RESEARCH.md Pitfall 6). Module-level singleton is safe at import time (RESEARCH.md Assumption A3).

**Module-level client singleton pattern** (from RESEARCH.md Pattern 5):
```python
_async_client = AsyncAnthropic()
```

**Pydantic schema for outline beats** (follows AngleCandidate pattern, lines 58–70 of angles.py):
```python
class OutlineBeat(BaseModel):
    beat_number: int
    beat_title: str
    data_anchors: str
    act_number: int | None
```

**Non-streaming Anthropic call for outline generation** (PTW-01 — sync client pattern from lines 548–572 of angles.py, but non-streaming):
```python
def generate_outline(
    self,
    article_id: str,
    year: int,
    round_num: int,
    angle_id: str,
) -> list[OutlineBeat]:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=[{"role": "user", "content": outline_prompt}],
    )
    # Parse JSON from response.content[0].text
    # Persist to outline_beats via BeatStore
    # Call ArticleStore.transition_status(article_id, "outline_generated")
```

**Async streaming generator pattern for beat prose** (RESEARCH.md Pattern 5, lines 266–273 of RESEARCH.md):
```python
async def stream_beat(self, article_id: str, beat_number: int):
    """Async generator yielding SSE-formatted strings for one beat."""
    # Gate check happens in the ROUTE HANDLER before this is called (Pitfall 1)
    async with _async_client.messages.stream(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[{"role": "user", "content": beat_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

**Exception handling pattern** (lines 573–588 of angles.py):
```python
    except anthropic.BadRequestError:
        logger.warning("...")
        ...
    except anthropic.AuthenticationError:
        logger.warning("ANTHROPIC_API_KEY not set ...")
    except Exception:
        logger.exception("... — defaulting to ...")
```

**`__all__` convention**:
```python
__all__ = ["OutlineBeat", "PipelineOrchestrator"]
```

---

### `src/pitlane_studio/routers/articles.py` (router, request-response + streaming)

**Analog:** `packages/pitlane-studio/src/pitlane_studio/app.py`

**Imports pattern** (extends app.py imports):
```python
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pitlane_studio.services.angles import AngleService, DataNotReadyError
from pitlane_studio.services.pipeline import PipelineOrchestrator
from pitlane_studio.store.article_store import ArticleStore
from pitlane_studio.store.beat_store import BeatStore

logger = logging.getLogger(__name__)
router = APIRouter()
```

**FastAPI route handler pattern** (lines 26–29 of app.py — async def + return dict):
```python
@router.get("/articles/{article_id}/angles")
async def get_angles(article_id: str) -> dict:
    store = ArticleStore()
    article = store.get(article_id)
    try:
        service = AngleService()
        angles = service.get_angles(article.race_year, article.race_round)
        return {"angles": [a.model_dump() for a in angles]}
    except DataNotReadyError as exc:
        raise HTTPException(status_code=422, detail=exc.message)
```

**SSE StreamingResponse pattern with gate-check BEFORE generator** (RESEARCH.md Pattern 1 — critical: raise HTTPException before StreamingResponse, lines 284–300 of RESEARCH.md):
```python
@router.get("/articles/{article_id}/beats/{beat_number}/stream")
async def stream_beat(article_id: str, beat_number: int):
    # Gate check BEFORE StreamingResponse — HTTPException must be raised here (Pitfall 1)
    store = ArticleStore()
    article = store.get(article_id)
    if article.status != "outline_approved":
        raise HTTPException(status_code=409, detail="Outline not approved")

    orchestrator = PipelineOrchestrator()

    async def _generator():
        beat_store = BeatStore()
        outline_beats = beat_store.get_outline_beats(article_id)
        beat = next((b for b in outline_beats if b.beat_number == beat_number), None)
        if beat is None:
            yield f"event: error\ndata: {json.dumps({'beat_number': beat_number, 'message': 'Beat not found', 'retryable': False})}\n\n"
            return
        yield f"event: beat_start\ndata: {json.dumps({'beat_number': beat_number, 'beat_title': beat.beat_title, 'total_beats': len(outline_beats)})}\n\n"
        full_prose: list[str] = []
        async for token in orchestrator.stream_beat(article_id, beat_number):
            full_prose.append(token)
            yield f"event: token\ndata: {json.dumps({'beat_number': beat_number, 'token': token})}\n\n"
        prose = "".join(full_prose)
        placeholder_markers = _detect_placeholders(prose)
        beat_store.save_beat(article_id, beat_number, beat.beat_title, prose, placeholder_markers)
        yield f"event: beat_done\ndata: {json.dumps({'beat_number': beat_number, 'prose': prose, 'placeholder_markers': placeholder_markers})}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

**SSE wire format** (must match exactly — double newline terminates message):
```
event: {name}\ndata: {json_string}\n\n
```

---

### `src/pitlane_studio/routers/acts.py` and `routers/races.py` (router, request-response)

**Analog:** `packages/pitlane-studio/src/pitlane_studio/app.py`

**Router declaration pattern**:
```python
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from pitlane_studio.services.five_act import FiveActMapper

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/acts/{year}/{round_num}")
async def get_acts(year: int, round_num: int) -> dict:
    mapper = FiveActMapper()
    acts = {}
    for act_number in range(1, 6):
        acts[act_number] = mapper.fetch_act_data(year, round_num, act_number)
    return {"acts": acts}
```

---

### `src/pitlane_studio/app.py` (modify — add StaticFiles mount + router registration)

**Analog:** Self (existing file lines 1–29)

**Addition pattern** — add AFTER existing imports, BEFORE `app = FastAPI(...)`, and mount StaticFiles AFTER all router registrations (RESEARCH.md Assumption A4 — StaticFiles at `/` must come last):
```python
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from pitlane_studio.routers import articles, acts, races

# Register API routers (must come BEFORE StaticFiles mount)
app.include_router(articles.router)
app.include_router(acts.router)
app.include_router(races.router)

# StaticFiles mount LAST — catch-all, shadows any route declared after it
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
```

The `html=True` flag is required for SPA fallback: serves `index.html` (as `200.html`) for unmatched paths (RESEARCH.md Pitfall 3 + Assumption A2).

---

### `tests/test_beat_store.py` (test, CRUD)

**Analog:** `packages/pitlane-studio/tests/test_article_store.py`

**Imports pattern** (lines 1–12 of test_article_store.py):
```python
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from pitlane_studio.store.beat_store import BeatStore, BeatRecord, OutlineBeatRecord
```

**Fixture usage pattern** — use existing `tmp_db_path` fixture from conftest.py (lines 12–15 of conftest.py):
```python
@pytest.fixture()
def tmp_beat_store(tmp_db_path: Path) -> BeatStore:
    """BeatStore backed by a temporary SQLite file."""
    return BeatStore(db_path=tmp_db_path)
```

**Test class + real SQLite pattern** (lines 13–57 of test_article_store.py):
```python
class TestBeatStoreOutlineBeats:
    def test_save_and_get_outline_beats(self, tmp_beat_store):
        article_id = str(uuid.uuid4())
        tmp_beat_store.save_outline_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Grid & Qualifying",
            data_anchors="HAM pole by 0.4s",
            act_number=1,
            position=1,
        )
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert len(beats) == 1
        assert beats[0].beat_title == "Grid & Qualifying"

    def test_upsert_outline_beat_is_idempotent(self, tmp_beat_store):
        article_id = str(uuid.uuid4())
        # Save twice — second save should update, not duplicate
        for _ in range(2):
            tmp_beat_store.save_outline_beat(
                article_id=article_id, beat_number=1,
                beat_title="Updated Title", data_anchors=None,
                act_number=1, position=1,
            )
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert len(beats) == 1
        assert beats[0].beat_title == "Updated Title"

class TestBeatStoreBeats:
    def test_save_beat_persists_prose(self, tmp_beat_store):
        article_id = str(uuid.uuid4())
        markers = [{"type": "quote", "offset": 45}]
        tmp_beat_store.save_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Grid & Qualifying",
            prose="The grid formed under grey skies.",
            placeholder_markers=markers,
        )
        beat = tmp_beat_store.get_beat(article_id, 1)
        assert beat.prose == "The grid formed under grey skies."
        assert json.loads(beat.placeholder_markers_json) == markers

    def test_upsert_beat_on_rerun(self, tmp_beat_store):
        article_id = str(uuid.uuid4())
        for i in range(2):
            tmp_beat_store.save_beat(
                article_id=article_id, beat_number=1,
                beat_title="Beat 1", prose=f"prose v{i}", placeholder_markers=[],
            )
        beat = tmp_beat_store.get_beat(article_id, 1)
        assert beat.prose == "prose v1"
```

**File existence assertion pattern** (lines 54–58 of test_article_store.py):
```python
def test_beats_db_file_created_in_db_path(self, tmp_db_path: Path):
    store = BeatStore(db_path=tmp_db_path)
    store.save_beat(str(uuid.uuid4()), 1, "T", "p", [])
    assert tmp_db_path.exists()
```

---

### `tests/test_pipeline.py` (test, streaming)

**Analog:** `packages/pitlane-studio/tests/test_angle_service.py`

**Imports pattern** (lines 1–12 of test_angle_service.py — use mocker for async mocking):
```python
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pitlane_studio.services.pipeline import OutlineBeat, PipelineOrchestrator
from pitlane_studio.store.beat_store import BeatStore
```

**Mocker-based test for async streaming** (pattern from lines 50–88 of test_angle_service.py — `mocker` fixture for patching):
```python
class TestStreamBeatEvents:
    async def test_stream_beat_yields_correct_events(self, tmp_db_path, mocker):
        """PTW-03: stream_beat generator yields beat_start, token×N, beat_done."""
        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = AsyncMock()
        mock_stream.text_stream.__aiter__ = lambda s: iter(["The grid ", "formed under "])

        mocker.patch(
            "pitlane_studio.services.pipeline._async_client.messages.stream",
            return_value=mock_stream,
        )
        orchestrator = PipelineOrchestrator()
        events = []
        async for chunk in orchestrator.stream_beat(article_id, beat_number=1):
            events.append(chunk)
        assert any("beat_start" in e for e in events)
        assert any("token" in e for e in events)
        assert any("beat_done" in e for e in events)

    def test_sse_format_has_double_newline(self, ...):
        """PTW-03: SSE event strings must end with double newline."""
        # Verify wire format: "event: X\ndata: {...}\n\n"
        event = f"event: beat_start\ndata: {json.dumps({'beat_number': 1})}\n\n"
        assert event.endswith("\n\n")
```

---

### `tests/test_routes.py` (test, request-response)

**Analog:** `packages/pitlane-studio/tests/test_app.py`

**Imports pattern** (lines 1–7 of test_app.py):
```python
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pitlane_studio.app import app
```

**TestClient pattern** (lines 9–15 of test_app.py):
```python
def test_acts_route_returns_all_five_acts(mocker):
    mocker.patch(
        "pitlane_studio.routers.acts.FiveActMapper.fetch_act_data",
        return_value={"label": "Grid & Qualifying", "data": {}},
    )
    client = TestClient(app)
    response = client.get("/acts/2025/5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["acts"]) == 5

def test_stream_beat_gate_409(tmp_db_path):
    """PTW-02: /stream returns 409 when article status != outline_approved."""
    # Create article in draft state — no approval
    from pitlane_studio.store.article_store import ArticleStore
    store = ArticleStore(db_path=tmp_db_path)
    article_id = str(uuid.uuid4())
    store.create(article_id, race_year=2025, race_round=5)

    client = TestClient(app)
    response = client.get(f"/articles/{article_id}/beats/1/stream")
    assert response.status_code == 409
```

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** `store/article_store.py` line 11, `services/angles.py` line 13
**Apply to:** All new Python files
```python
from __future__ import annotations
```

### Module-level logger
**Source:** `services/angles.py` line 32, `services/five_act.py` line 26
**Apply to:** All new service and router files
```python
logger = logging.getLogger(__name__)
```

### Pydantic BaseModel for all data records
**Source:** `store/article_store.py` lines 32–41, `services/angles.py` lines 58–70
**Apply to:** `beat_store.py` (OutlineBeatRecord, BeatRecord), `pipeline.py` (OutlineBeat), router request/response schemas
```python
from pydantic import BaseModel

class SomeRecord(BaseModel):
    field: str
    optional_field: str | None
    timestamp: str  # ISO8601 — SQLite has no native datetime type
```

### SQLAlchemy Core — parameterized queries (no string concatenation)
**Source:** `store/article_store.py` lines 107–121
**Apply to:** `beat_store.py` — all `WHERE` clauses
```python
# Correct — parameterized via SQLAlchemy Core
conn.execute(
    table.select().where(table.c.article_id == article_id)
)
# Wrong — never use string formatting in SQL
```

### ISO8601 timestamp helper
**Source:** `store/article_store.py` lines 70–71
**Apply to:** `beat_store.py`
```python
def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
```

### Engine construction with parent dir creation
**Source:** `store/article_store.py` lines 59–67
**Apply to:** `beat_store.py` — `get_engine()` must create parent directories before `create_engine()`
```python
def get_engine(db_path: Path | None = None) -> Engine:
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")
```

### `engine.begin()` for writes, `engine.connect()` for reads
**Source:** `store/article_store.py` lines 91–103 (begin) and 107–121 (connect)
**Apply to:** `beat_store.py`
```python
# Writes — use begin() for auto-commit transaction
with self._engine.begin() as conn:
    conn.execute(table.insert().values(...))

# Reads — use connect() (no transaction needed)
with self._engine.connect() as conn:
    row = conn.execute(table.select().where(...)).fetchone()
```

### conftest.py `tmp_db_path` fixture
**Source:** `tests/conftest.py` lines 12–15
**Apply to:** All new test files — use `tmp_db_path` fixture directly; do NOT create new tmp path fixtures
```python
# conftest.py provides:
@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "articles.db"
```

New test fixtures that need a `BeatStore` should accept `tmp_db_path` and construct directly:
```python
@pytest.fixture()
def tmp_beat_store(tmp_db_path: Path) -> BeatStore:
    return BeatStore(db_path=tmp_db_path)
```

### `__all__` declaration at module end
**Source:** `store/article_store.py` line 148, `services/angles.py` line 601
**Apply to:** All new Python modules
```python
__all__ = ["PublicClass", "public_function"]
```

### Anthropic client — sync vs async
**Source:** `services/angles.py` lines 548–572 (sync) and RESEARCH.md Pattern 5 (async)
**Apply to:** `services/pipeline.py`
- **Outline generation (PTW-01):** Use `anthropic.Anthropic()` (sync) — non-streaming, called from sync context
- **Beat streaming (PTW-03):** Use `AsyncAnthropic()` (async) — module-level singleton, inside `async def` generator
- **Never mix:** Do not use sync `Anthropic()` inside `async def` — blocks event loop (RESEARCH.md Pitfall 6)

---

## Frontend — No Analog Found

The SvelteKit frontend has no existing analog in the codebase. All frontend patterns come from RESEARCH.md.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/svelte.config.js` | config | — | No SvelteKit config exists in codebase |
| `frontend/vite.config.ts` | config | — | No Vite config exists in codebase |
| `frontend/src/lib/extensions/placeholder-nodes.ts` | utility | transform | No TipTap extensions exist in codebase |
| `frontend/src/lib/components/*.svelte` | component | request-response + streaming | No Svelte components exist in codebase |
| `frontend/src/routes/+page.svelte` | component | request-response | No SvelteKit routes exist in codebase |
| `frontend/src/lib/store.ts` | store | — | No Svelte stores exist in codebase |
| `frontend/src/lib/api.ts` | utility | request-response | No typed fetch wrappers exist in codebase |

**Planner should reference RESEARCH.md patterns for these files:**
- Pattern 2 (TipTap custom inline atom node) — `placeholder-nodes.ts`
- Pattern 3 (TipTap instantiation in Svelte 5 `onMount`) — `BeatEditor.svelte`
- Pattern 4 (SvelteKit static build config) — `svelte.config.js` + `vite.config.ts`
- UI-SPEC component contracts — all Svelte component files
- UI-SPEC color/spacing/typography tokens — all CSS in Svelte files

**Wave 0 spike requirement (D-10):** TipTap + Svelte 5 integration must be validated before full editor implementation. The spike validates `onMount` instantiation, `editor.getJSON()` round-trip, and custom node extension. All other frontend work is blocked until spike passes.

---

## Metadata

**Analog search scope:** `packages/pitlane-studio/src/`, `packages/pitlane-studio/tests/`
**Files scanned:** 7 (article_store.py, angles.py, five_act.py, app.py, conftest.py, test_article_store.py, test_app.py, test_angle_service.py)
**Pattern extraction date:** 2026-05-05
