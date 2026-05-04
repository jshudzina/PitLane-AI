"""ArticleStore — SQLAlchemy Core SQLite persistence with strict state machine.

Per CONTEXT.md:
  D-03: SQLAlchemy Core only — Table/Column/MetaData; no ORM layer.
  D-04: Article records are Pydantic BaseModel instances at the Python layer.
  D-05: Invalid state transitions raise ValueError.

Default database path: ~/.pitlane/studio/articles.db
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# State machine (D-05) — strict; any transition not matching this dict raises.
# `published` is terminal (no forward transition).
# ---------------------------------------------------------------------------
_TRANSITIONS: dict[str, str] = {
    "draft": "outline_generated",
    "outline_generated": "outline_approved",
    "outline_approved": "published",
}
_VALID_STATUSES: frozenset[str] = frozenset(_TRANSITIONS.keys()) | {"published"}


class ArticleRecord(BaseModel):
    """Pydantic representation of an article row (D-04)."""

    id: str
    race_year: int
    race_round: int
    angle_id: str | None
    status: str
    created_at: str  # ISO8601 — SQLite has no native datetime type
    updated_at: str


metadata = MetaData()

articles_table = Table(
    "articles",
    metadata,
    Column("id", String, primary_key=True),
    Column("race_year", Integer, nullable=False),
    Column("race_round", Integer, nullable=False),
    Column("angle_id", String, nullable=True),
    Column("status", String, nullable=False, default="draft"),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)


def _default_db_path() -> Path:
    return Path.home() / ".pitlane" / "studio" / "articles.db"


def get_engine(db_path: Path | None = None) -> Engine:
    """Construct an engine, creating parent dirs first (Pitfall 5)."""
    path = db_path or _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ArticleStore:
    """SQLite article persistence with strict state-machine transitions."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._engine: Engine = get_engine(db_path)
        metadata.create_all(self._engine)

    def create(
        self,
        article_id: str,
        *,
        race_year: int,
        race_round: int,
        angle_id: str | None = None,
    ) -> ArticleRecord:
        """Insert a new article in `draft` status."""
        now = _now_iso()
        with self._engine.begin() as conn:
            conn.execute(
                articles_table.insert().values(
                    id=article_id,
                    race_year=race_year,
                    race_round=race_round,
                    angle_id=angle_id,
                    status="draft",
                    created_at=now,
                    updated_at=now,
                )
            )
        return self.get(article_id)

    def get(self, article_id: str) -> ArticleRecord:
        """Return the article record. Raises ValueError if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(articles_table.select().where(articles_table.c.id == article_id)).fetchone()
        if row is None:
            raise ValueError(f"Article {article_id!r} not found")
        return ArticleRecord(
            id=row.id,
            race_year=row.race_year,
            race_round=row.race_round,
            angle_id=row.angle_id,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def transition_status(self, article_id: str, target_status: str) -> ArticleRecord:
        """Advance article to target_status. Raises ValueError on illegal transition."""
        with self._engine.begin() as conn:
            row = conn.execute(articles_table.select().where(articles_table.c.id == article_id)).fetchone()
            if row is None:
                raise ValueError(f"Article {article_id!r} not found")
            current = row.status
            expected = _TRANSITIONS.get(current)
            if expected != target_status:
                raise ValueError(f"Invalid transition: {current!r} -> {target_status!r}. Expected: {expected!r}")
            conn.execute(
                articles_table.update()
                .where(articles_table.c.id == article_id)
                .values(status=target_status, updated_at=_now_iso())
            )
        return self.get(article_id)


__all__ = ["ArticleRecord", "ArticleStore", "get_engine"]
