"""Phase 3 pipeline tests — PipelineOrchestrator unit tests with mocked Anthropic."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from pitlane_studio.services.pipeline import OutlineBeat, PipelineOrchestrator, _detect_placeholders
from pitlane_studio.store.article_store import ArticleStore
from pitlane_studio.store.beat_store import BeatStore


def test_detect_placeholders_finds_all_types():
    prose = "Some text [JOURNALIST: quote] here [JOURNALIST: context] and [JOURNALIST: causal] end"
    markers = _detect_placeholders(prose)
    assert len(markers) == 3
    types = {m["type"] for m in markers}
    assert types == {"quote", "context", "causal"}
    for m in markers:
        assert "offset" in m
        assert isinstance(m["offset"], int)


def test_detect_placeholders_returns_empty_for_no_markers():
    markers = _detect_placeholders("Just plain prose with no placeholders.")
    assert markers == []


def test_generate_outline_calls_anthropic_and_persists(tmp_db_path, mocker):
    fake_beats = [
        {"beat_number": i, "beat_title": f"Beat {i}", "data_anchors": f"Anchor {i}", "act_number": i}
        for i in range(1, 6)
    ]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(fake_beats))]

    mocker.patch(
        "pitlane_studio.services.pipeline.anthropic.Anthropic",
        return_value=MagicMock(
            messages=MagicMock(create=MagicMock(return_value=mock_response))
        ),
    )
    mocker.patch("pitlane_studio.services.pipeline.FiveActMapper.fetch_act_data", return_value={})
    mocker.patch("pitlane_studio.services.pipeline.BeatStore", return_value=BeatStore(db_path=tmp_db_path))
    mocker.patch("pitlane_studio.services.pipeline.ArticleStore", return_value=ArticleStore(db_path=tmp_db_path))

    article_id = str(uuid.uuid4())
    ArticleStore(db_path=tmp_db_path).create(article_id, race_year=2025, race_round=5)

    orchestrator = PipelineOrchestrator()
    result = orchestrator.generate_outline(article_id, 2025, 5, "angle-1", "Test Angle", "Test rationale")

    assert len(result) == 5
    assert all(isinstance(b, OutlineBeat) for b in result)
    assert result[0].beat_number == 1


async def test_stream_beat_yields_correct_sse_events(tmp_db_path, mocker):
    mock_stream_ctx = AsyncMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    async def _fake_text_stream():
        yield "The grid "
        yield "formed."

    mock_stream_ctx.text_stream = _fake_text_stream()

    mocker.patch(
        "pitlane_studio.services.pipeline._async_client.messages.stream",
        return_value=mock_stream_ctx,
    )

    beat_store = BeatStore(db_path=tmp_db_path)
    article_id = str(uuid.uuid4())
    art_store = ArticleStore(db_path=tmp_db_path)
    art_store.create(article_id, race_year=2025, race_round=5)
    art_store.transition_status(article_id, "outline_generated")
    art_store.transition_status(article_id, "outline_approved")
    beat_store.save_outline_beat(article_id, 1, "Grid & Qualifying", "data anchors", 1, 1)

    mocker.patch("pitlane_studio.services.pipeline.BeatStore", return_value=beat_store)
    mocker.patch("pitlane_studio.services.pipeline.ArticleStore", return_value=art_store)
    mocker.patch("pitlane_studio.services.pipeline.FiveActMapper.fetch_act_data", return_value={})

    orchestrator = PipelineOrchestrator()
    chunks = []
    async for chunk in orchestrator.stream_beat(article_id, 1):
        chunks.append(chunk)

    assert any("beat_start" in c for c in chunks)
    assert any("token" in c for c in chunks)
    assert any("beat_done" in c for c in chunks)
    for chunk in chunks:
        assert chunk.endswith("\n\n"), f"SSE chunk missing double newline: {chunk!r}"
