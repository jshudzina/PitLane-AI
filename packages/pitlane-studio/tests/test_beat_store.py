"""PTW-02/03/04 integration tests — BeatStore against real SQLite file (no mocks)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from pitlane_studio.store.beat_store import BeatRecord, BeatStore, OutlineBeatRecord


@pytest.fixture()
def tmp_beat_store(tmp_db_path: Path) -> BeatStore:
    """BeatStore backed by a temporary SQLite file."""
    return BeatStore(db_path=tmp_db_path)


class TestBeatStoreOutlineBeats:
    def test_save_and_get_outline_beats(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        tmp_beat_store.save_outline_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Opening Act",
            data_anchors=None,
            act_number=1,
            position=1,
        )
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert len(beats) == 1
        assert beats[0].beat_title == "Opening Act"

    def test_upsert_outline_beat_is_idempotent(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        tmp_beat_store.save_outline_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="First Title",
            data_anchors=None,
            act_number=1,
            position=1,
        )
        tmp_beat_store.save_outline_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Updated Title",
            data_anchors=None,
            act_number=1,
            position=1,
        )
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert len(beats) == 1
        assert beats[0].beat_title == "Updated Title"

    def test_get_outline_beats_ordered_by_position(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        # Save in reverse order: 3, 1, 2
        for pos, num, title in [(3, 3, "Third"), (1, 1, "First"), (2, 2, "Second")]:
            tmp_beat_store.save_outline_beat(
                article_id=article_id,
                beat_number=num,
                beat_title=title,
                data_anchors=None,
                act_number=None,
                position=pos,
            )
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert [b.position for b in beats] == [1, 2, 3]
        assert [b.beat_title for b in beats] == ["First", "Second", "Third"]

    def test_save_outline_beats_bulk(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        beat_dicts = [
            {"beat_number": i, "beat_title": f"Beat {i}", "data_anchors": None, "act_number": i, "position": i}
            for i in range(1, 4)
        ]
        tmp_beat_store.save_outline_beats(article_id, beat_dicts)
        beats = tmp_beat_store.get_outline_beats(article_id)
        assert len(beats) == 3


class TestBeatStoreBeats:
    def test_save_beat_persists_prose(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        markers = [{"type": "quote", "offset": 45}]
        tmp_beat_store.save_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Opening Beat",
            prose="This is the opening prose.",
            placeholder_markers=markers,
        )
        beat = tmp_beat_store.get_beat(article_id, 1)
        assert beat is not None
        assert beat.prose == "This is the opening prose."
        assert json.loads(beat.placeholder_markers_json) == markers

    def test_upsert_beat_on_rerun(self, tmp_beat_store: BeatStore) -> None:
        article_id = str(uuid.uuid4())
        tmp_beat_store.save_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Beat Title",
            prose="prose v0",
            placeholder_markers=[],
        )
        tmp_beat_store.save_beat(
            article_id=article_id,
            beat_number=1,
            beat_title="Beat Title",
            prose="prose v1",
            placeholder_markers=[],
        )
        beat = tmp_beat_store.get_beat(article_id, 1)
        assert beat is not None
        assert beat.prose == "prose v1"

    def test_get_beat_returns_none_when_missing(self, tmp_beat_store: BeatStore) -> None:
        result = tmp_beat_store.get_beat(str(uuid.uuid4()), 99)
        assert result is None

    def test_beats_db_file_created(self, tmp_db_path: Path) -> None:
        store = BeatStore(db_path=tmp_db_path)
        store.save_beat(
            article_id=str(uuid.uuid4()),
            beat_number=1,
            beat_title="Beat",
            prose="some prose",
            placeholder_markers=[],
        )
        assert tmp_db_path.exists()
