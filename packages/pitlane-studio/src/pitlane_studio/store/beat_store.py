"""BeatStore — SQLAlchemy Core SQLite persistence for outline beats and generated beats.

Per PLAN.md 03-01:
  - outline_beats table: stores the journalist-approved outline structure (one row per beat)
  - beats table: stores generated prose per beat after outline approval
  - Both tables use composite PK (article_id, beat_number) — prevents duplicate rows
  - Upsert via INSERT OR REPLACE — idempotent writes

Default database path: ~/.pitlane/studio/articles.db
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLAlchemy Core table definitions — composite PK on (article_id, beat_number)
# ---------------------------------------------------------------------------

metadata = MetaData()

outline_beats_table = Table(
    "outline_beats",
    metadata,
    Column("article_id", String, primary_key=True),
    Column("beat_number", Integer, primary_key=True),
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
    Column("article_id", String, primary_key=True),
    Column("beat_number", Integer, primary_key=True),
    Column("beat_title", String, nullable=False),
    Column("prose", Text, nullable=True),
    Column("placeholder_markers_json", Text, nullable=True),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)


# ---------------------------------------------------------------------------
# Pydantic record models — D-04 pattern from article_store.py
# ---------------------------------------------------------------------------


class OutlineBeatRecord(BaseModel):
    """Pydantic representation of an outline_beats row."""

    article_id: str
    beat_number: int
    beat_title: str
    data_anchors: str | None
    act_number: int | None
    position: int
    created_at: str
    updated_at: str


class BeatRecord(BaseModel):
    """Pydantic representation of a beats row."""

    article_id: str
    beat_number: int
    beat_title: str
    prose: str | None
    placeholder_markers_json: str | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Engine helpers — replicated from article_store.py
# ---------------------------------------------------------------------------


def _default_db_path() -> Path:
    return Path.home() / ".pitlane" / "studio" / "articles.db"


def get_engine(db_path: Path | None = None) -> Engine:
    """Construct an engine, creating parent dirs first (Pitfall 5)."""
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# BeatStore
# ---------------------------------------------------------------------------


class BeatStore:
    """SQLite persistence for outline beats and generated beat prose."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._engine: Engine = get_engine(db_path)
        metadata.create_all(self._engine)

    # ------------------------------------------------------------------
    # Outline beats
    # ------------------------------------------------------------------

    def save_outline_beat(
        self,
        article_id: str,
        beat_number: int,
        beat_title: str,
        data_anchors: str | None,
        act_number: int | None,
        position: int,
    ) -> None:
        """Upsert one outline beat row (idempotent — INSERT OR REPLACE)."""
        now = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                outline_beats_table.insert()
                .prefix_with("OR REPLACE")
                .values(
                    article_id=article_id,
                    beat_number=beat_number,
                    beat_title=beat_title,
                    data_anchors=data_anchors,
                    act_number=act_number,
                    position=position,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_outline_beats(self, article_id: str) -> list[OutlineBeatRecord]:
        """Return all outline beats for an article, ordered by position ascending."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                outline_beats_table.select()
                .where(outline_beats_table.c.article_id == article_id)
                .order_by(outline_beats_table.c.position)
            ).fetchall()
        return [
            OutlineBeatRecord(
                article_id=row.article_id,
                beat_number=row.beat_number,
                beat_title=row.beat_title,
                data_anchors=row.data_anchors,
                act_number=row.act_number,
                position=row.position,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def save_outline_beats(self, article_id: str, beats: list[dict]) -> None:
        """Bulk upsert outline beats from a list of dicts.

        Each dict must have keys: beat_number, beat_title, data_anchors, act_number, position.
        """
        for beat in beats:
            self.save_outline_beat(
                article_id=article_id,
                beat_number=beat["beat_number"],
                beat_title=beat["beat_title"],
                data_anchors=beat.get("data_anchors"),
                act_number=beat.get("act_number"),
                position=beat.get("position", beat["beat_number"]),
            )

    # ------------------------------------------------------------------
    # Generated beats (prose)
    # ------------------------------------------------------------------

    def save_beat(
        self,
        article_id: str,
        beat_number: int,
        beat_title: str,
        prose: str,
        placeholder_markers: list,
    ) -> None:
        """Upsert one beat prose row (idempotent — INSERT OR REPLACE)."""
        now = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                beats_table.insert()
                .prefix_with("OR REPLACE")
                .values(
                    article_id=article_id,
                    beat_number=beat_number,
                    beat_title=beat_title,
                    prose=prose,
                    placeholder_markers_json=json.dumps(placeholder_markers),
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_beat(self, article_id: str, beat_number: int) -> BeatRecord | None:
        """Return the beat record or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                beats_table.select().where(
                    (beats_table.c.article_id == article_id)
                    & (beats_table.c.beat_number == beat_number)
                )
            ).fetchone()
        if row is None:
            return None
        return BeatRecord(
            article_id=row.article_id,
            beat_number=row.beat_number,
            beat_title=row.beat_title,
            prose=row.prose,
            placeholder_markers_json=row.placeholder_markers_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


__all__ = ["BeatRecord", "BeatStore", "OutlineBeatRecord", "get_engine"]
