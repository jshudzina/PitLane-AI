"""Phase 3 router tests — FastAPI TestClient tests for all pipeline routes."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from pitlane_studio.app import app
from pitlane_studio.services.angles import DataNotReadyError
from pitlane_studio.store.article_store import ArticleStore
from pitlane_studio.store.beat_store import BeatStore


def test_acts_route_returns_all_five_acts(mocker):
    mocker.patch(
        "pitlane_studio.routers.acts.FiveActMapper.fetch_act_data",
        return_value={"label": "Grid & Qualifying", "data": {}},
    )
    client = TestClient(app)
    response = client.get("/acts/2025/5")
    assert response.status_code == 200
    data = response.json()
    assert "acts" in data
    assert len(data["acts"]) == 5
    for act_val in data["acts"].values():
        assert "label" in act_val
        assert "data" in act_val


def test_stream_beat_gate_409(tmp_db_path, mocker):
    mocker.patch("pitlane_studio.routers.articles.ArticleStore", return_value=ArticleStore(db_path=tmp_db_path))
    article_id = str(uuid.uuid4())
    ArticleStore(db_path=tmp_db_path).create(article_id, race_year=2025, race_round=5)

    client = TestClient(app)
    response = client.get(f"/articles/{article_id}/beats/1/stream")
    assert response.status_code == 409


def test_approve_outline_transitions_status(tmp_db_path, mocker):
    mocker.patch("pitlane_studio.routers.articles.ArticleStore", return_value=ArticleStore(db_path=tmp_db_path))
    article_id = str(uuid.uuid4())
    store = ArticleStore(db_path=tmp_db_path)
    store.create(article_id, race_year=2025, race_round=5)
    store.transition_status(article_id, "outline_generated")

    client = TestClient(app)
    response = client.post(f"/articles/{article_id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "outline_approved"


def test_patch_outline_persists_beats(tmp_db_path, mocker):
    mocker.patch("pitlane_studio.routers.articles.BeatStore", return_value=BeatStore(db_path=tmp_db_path))
    article_id = str(uuid.uuid4())

    beats_payload = [
        {"beat_number": 1, "beat_title": "Grid & Qualifying", "data_anchors": "HAM pole", "act_number": 1, "position": 1},
        {"beat_number": 2, "beat_title": "Lap 1 Chaos", "data_anchors": "3 cars DNF", "act_number": 2, "position": 2},
    ]

    client = TestClient(app)
    response = client.patch(f"/articles/{article_id}/outline", json={"beats": beats_payload})
    assert response.status_code == 200
    data = response.json()
    assert data["saved_beats"] == 2

    beat_store = BeatStore(db_path=tmp_db_path)
    saved = beat_store.get_outline_beats(article_id)
    assert len(saved) == 2


def test_angles_route_returns_422_when_data_not_ready(tmp_db_path, mocker):
    mocker.patch("pitlane_studio.routers.articles.ArticleStore", return_value=ArticleStore(db_path=tmp_db_path))
    article_id = str(uuid.uuid4())
    ArticleStore(db_path=tmp_db_path).create(article_id, race_year=2025, race_round=5)

    mocker.patch(
        "pitlane_studio.routers.articles.AngleService.get_angles",
        side_effect=DataNotReadyError("Race data not ready"),
    )

    client = TestClient(app)
    response = client.get(f"/articles/{article_id}/angles")
    assert response.status_code == 422
