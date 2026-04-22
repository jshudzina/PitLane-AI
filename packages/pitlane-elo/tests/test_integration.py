"""Integration tests against the real DuckDB database.

These tests are slow and require the production database to be present.
Mark them with ``pytest.mark.slow``.

The endure-Elo inclusion-exclusion win probability is O(n * 2^(n-1)) per
race, so full-history runs (800+ races, ~20 drivers each) take minutes.
Tests here use a 5-season window to stay under ~30s.
"""

from __future__ import annotations

import pytest
from pitlane_elo.data import get_data_dir
from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo

_db_exists = any((get_data_dir() / "race_entries").glob("*.parquet"))


@pytest.mark.slow
@pytest.mark.skipif(not _db_exists, reason="Production DB not found")
class TestHistoryRun:
    def test_endure_elo_one_season(self) -> None:
        """EndureElo should process a single season without error."""
        model = EndureElo()
        preds = run_historical(model, start_year=2023, end_year=2023)
        assert len(preds) >= 10
        metrics = evaluate_model(preds)
        assert metrics["n_races"] == len(preds)
        assert metrics["mean_winner_prob"] > 0.0

    def test_speed_elo_one_season(self) -> None:
        """SpeedElo should process a single season without error."""
        model = SpeedElo()
        preds = run_historical(model, start_year=2023, end_year=2023)
        assert len(preds) >= 10
        metrics = evaluate_model(preds)
        assert metrics["n_races"] == len(preds)
        assert metrics["mean_winner_prob"] > 0.0


@pytest.mark.slow
@pytest.mark.skipif(not _db_exists, reason="Production DB not found")
class TestModelComparison:
    def test_endure_vs_speed_one_season(self) -> None:
        """Compare endure-Elo and speed-Elo over a single season."""
        endure = EndureElo()
        speed = SpeedElo()
        preds_e = run_historical(endure, start_year=2023, end_year=2023)
        preds_s = run_historical(speed, start_year=2023, end_year=2023)
        comparison = compare_models(preds_e, preds_s)
        assert comparison["n_races"] >= 10
        assert 0.0 <= comparison["race_level_pct"] <= 1.0
