"""Tests for pitlane_elo.prediction.forecast."""

from __future__ import annotations

from pathlib import Path

import pytest
from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo


@pytest.fixture()
def _use_populated_db(populated_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PITLANE_DATA_DIR", str(populated_db))


@pytest.fixture()
def _use_multi_race_db(multi_race_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PITLANE_DATA_DIR", str(multi_race_db))


@pytest.mark.usefixtures("_use_populated_db")
class TestRunHistorical:
    def test_single_race(self) -> None:
        """Should produce one prediction for the single race in populated_db."""
        model = EndureElo()
        preds = run_historical(model, start_year=2024, end_year=2024)
        assert len(preds) == 1
        assert preds[0].year == 2024
        assert preds[0].round == 1
        assert len(preds[0].driver_ids) == 5
        assert abs(preds[0].predicted_probs.sum() - 1.0) < 1e-10


@pytest.mark.usefixtures("_use_multi_race_db")
class TestRunHistoricalMultiRace:
    def test_multi_race_with_season_boundary(self) -> None:
        """Should handle season boundaries and produce predictions for each race."""
        model = EndureElo()
        preds = run_historical(model, start_year=2023, end_year=2024)
        assert len(preds) == 6  # 3 races per season, 2 seasons
        # Verify season boundary was handled (ratings exist for both seasons)
        years = {p.year for p in preds}
        assert years == {2023, 2024}


@pytest.mark.usefixtures("_use_multi_race_db")
class TestEvaluateModel:
    def test_filters_by_year(self) -> None:
        model = EndureElo()
        preds = run_historical(model, start_year=2023, end_year=2024)
        result = evaluate_model(preds, eval_start_year=2024, eval_end_year=2024)
        assert result["n_races"] == 3


@pytest.mark.usefixtures("_use_multi_race_db")
class TestCompareModels:
    def test_compare_endure_vs_speed(self) -> None:
        endure = EndureElo()
        speed = SpeedElo()
        preds_e = run_historical(endure, start_year=2023, end_year=2024)
        preds_s = run_historical(speed, start_year=2023, end_year=2024)
        result = compare_models(preds_e, preds_s)
        assert result["n_races"] == 6
        assert 0.0 <= result["race_level_pct"] <= 1.0
