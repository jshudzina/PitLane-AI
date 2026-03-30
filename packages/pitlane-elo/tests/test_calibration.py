"""Tests for the calibration module."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pitlane_elo.calibration import CalibrationResult, calibrate, random_search
from pitlane_elo.config import ENDURE_ELO_DEFAULT
from pitlane_elo.ratings.endure_elo import EndureElo


class TestRandomSearch:
    """Unit tests for random_search(); _score is mocked — tests cover sampling behavior."""

    def test_returns_n_trials_results(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            results = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=5,
                seed=0,
            )
        assert len(results) == 5

    def test_results_sorted_descending(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            results = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=10,
                seed=1,
            )
        lls = [r["log_likelihood"] for r in results]
        assert lls == sorted(lls, reverse=True)

    def test_result_keys(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            results = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=3,
                seed=2,
            )
        for r in results:
            assert set(r.keys()) == {"k_max", "phi_race", "phi_season", "log_likelihood"}

    def test_seed_reproducibility(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            r1 = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=5,
                seed=42,
            )
            r2 = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=5,
                seed=42,
            )
        for a, b in zip(r1, r2, strict=True):
            assert a["k_max"] == pytest.approx(b["k_max"])
            assert a["phi_race"] == pytest.approx(b["phi_race"])
            assert a["phi_season"] == pytest.approx(b["phi_season"])

    def test_different_seeds_differ(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            r1 = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=5,
                seed=0,
            )
            r2 = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=5,
                seed=99,
            )
        assert any(a["k_max"] != pytest.approx(b["k_max"]) for a, b in zip(r1, r2, strict=True))

    def test_params_within_bounds(self):
        with patch("pitlane_elo.calibration._score", side_effect=_fake_score):
            results = random_search(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2024,
                n_trials=50,
                seed=7,
            )
        for r in results:
            assert 0.05 <= r["k_max"] <= 1.5
            assert 0.90 <= r["phi_race"] <= 0.999
            assert 0.60 <= r["phi_season"] <= 0.99


def _fake_score(k_max, phi_race, phi_season, **_kwargs):
    """Fake scoring function: best when k_max=0.4, phi_race=0.99, phi_season=0.90."""
    return -(abs(k_max - 0.4) + abs(phi_race - 0.99) + abs(phi_season - 0.90))


class TestCalibrate:
    """Unit tests for calibrate(); _score is mocked to avoid expensive model runs."""

    def test_returns_calibration_result(self):
        with (
            patch("pitlane_elo.calibration._score", side_effect=_fake_score),
            patch("pitlane_elo.calibration.run_historical", return_value=[]),
            patch("pitlane_elo.calibration.evaluate_model", return_value={"log_likelihood": -10.0, "n_races": 5}),
        ):
            result = calibrate(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2023,
                val_start=2024,
                val_end=2024,
                n_trials=5,
                seed=0,
            )
        assert isinstance(result, CalibrationResult)

    def test_best_config_has_valid_params(self):
        with (
            patch("pitlane_elo.calibration._score", side_effect=_fake_score),
            patch("pitlane_elo.calibration.run_historical", return_value=[]),
            patch("pitlane_elo.calibration.evaluate_model", return_value={"log_likelihood": -10.0, "n_races": 5}),
        ):
            result = calibrate(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2023,
                val_start=2024,
                val_end=2024,
                n_trials=5,
                seed=0,
            )
        cfg = result.best_config
        assert 0.01 <= cfg.k_max <= 2.0
        assert 0.5 <= cfg.phi_race < 1.0
        assert 0.5 <= cfg.phi_season < 1.0

    def test_random_results_count(self):
        with (
            patch("pitlane_elo.calibration._score", side_effect=_fake_score),
            patch("pitlane_elo.calibration.run_historical", return_value=[]),
            patch("pitlane_elo.calibration.evaluate_model", return_value={"log_likelihood": -10.0, "n_races": 5}),
        ):
            result = calibrate(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2023,
                val_start=2024,
                val_end=2024,
                n_trials=4,
                seed=0,
            )
        assert len(result.random_results) == 4

    def test_best_config_name_suffix(self):
        with (
            patch("pitlane_elo.calibration._score", side_effect=_fake_score),
            patch("pitlane_elo.calibration.run_historical", return_value=[]),
            patch("pitlane_elo.calibration.evaluate_model", return_value={"log_likelihood": -10.0, "n_races": 5}),
        ):
            result = calibrate(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2023,
                val_start=2024,
                val_end=2024,
                n_trials=5,
                seed=0,
            )
        assert result.best_config.name.endswith("-calibrated")

    def test_nelder_mead_improves_on_random_best(self):
        # Nelder-Mead should find params closer to the fake optimum (0.4, 0.99, 0.90)
        with (
            patch("pitlane_elo.calibration._score", side_effect=_fake_score),
            patch("pitlane_elo.calibration.run_historical", return_value=[]),
            patch("pitlane_elo.calibration.evaluate_model", return_value={"log_likelihood": -10.0, "n_races": 5}),
        ):
            result = calibrate(
                EndureElo,
                ENDURE_ELO_DEFAULT,
                warmup_start=2023,
                cal_start=2023,
                cal_end=2023,
                val_start=2024,
                val_end=2024,
                n_trials=10,
                seed=0,
            )
        cfg = result.best_config
        assert abs(cfg.k_max - 0.4) < 0.05
        assert abs(cfg.phi_race - 0.99) < 0.005
        assert abs(cfg.phi_season - 0.90) < 0.01
