"""Tests for pitlane_elo.prediction.forecast."""

from __future__ import annotations

from pathlib import Path

from pitlane_elo.prediction.forecast import compare_models, evaluate_model, run_historical
from pitlane_elo.ratings.endure_elo import EndureElo
from pitlane_elo.ratings.speed_elo import SpeedElo


class TestRunHistorical:
    def test_single_race(self, populated_db: Path) -> None:
        """Should produce one prediction for the single race in populated_db."""
        import os

        os.environ["PITLANE_DB_PATH"] = str(populated_db)
        try:
            model = EndureElo()
            preds = run_historical(model, start_year=2024, end_year=2024)
            assert len(preds) == 1
            assert preds[0].year == 2024
            assert preds[0].round == 1
            assert len(preds[0].driver_ids) == 5
            assert abs(preds[0].predicted_probs.sum() - 1.0) < 1e-10
        finally:
            os.environ.pop("PITLANE_DB_PATH", None)

    def test_multi_race_with_season_boundary(self, multi_race_db: Path) -> None:
        """Should handle season boundaries and produce predictions for each race."""
        import os

        os.environ["PITLANE_DB_PATH"] = str(multi_race_db)
        try:
            model = EndureElo()
            preds = run_historical(model, start_year=2023, end_year=2024)
            assert len(preds) == 6  # 3 races per season, 2 seasons
            # Verify season boundary was handled (ratings exist for both seasons)
            years = {p.year for p in preds}
            assert years == {2023, 2024}
        finally:
            os.environ.pop("PITLANE_DB_PATH", None)


class TestEvaluateModel:
    def test_filters_by_year(self, multi_race_db: Path) -> None:
        import os

        os.environ["PITLANE_DB_PATH"] = str(multi_race_db)
        try:
            model = EndureElo()
            preds = run_historical(model, start_year=2023, end_year=2024)
            result = evaluate_model(preds, eval_start_year=2024, eval_end_year=2024)
            assert result["n_races"] == 3
        finally:
            os.environ.pop("PITLANE_DB_PATH", None)


class TestCompareModels:
    def test_compare_endure_vs_speed(self, multi_race_db: Path) -> None:
        import os

        os.environ["PITLANE_DB_PATH"] = str(multi_race_db)
        try:
            endure = EndureElo()
            speed = SpeedElo()
            preds_e = run_historical(endure, start_year=2023, end_year=2024)
            preds_s = run_historical(speed, start_year=2023, end_year=2024)
            result = compare_models(preds_e, preds_s)
            assert result["n_races"] == 6
            assert 0.0 <= result["race_level_pct"] <= 1.0
        finally:
            os.environ.pop("PITLANE_DB_PATH", None)
