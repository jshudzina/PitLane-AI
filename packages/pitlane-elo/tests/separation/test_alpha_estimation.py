"""Tests for pitlane_elo.separation.alpha_estimation."""

from __future__ import annotations

from pathlib import Path

from pitlane_elo.separation.alpha_estimation import estimate_alpha


class TestEstimateAlpha:
    def test_returns_float_in_default_bounds(self, multi_race_db: Path) -> None:
        """Result should be in [0.0, 15.0] (default bounds)."""
        alpha = estimate_alpha(2023, 2024, db_path=multi_race_db)
        assert isinstance(alpha, float)
        assert 0.0 <= alpha <= 15.0

    def test_custom_bounds_respected(self, multi_race_db: Path) -> None:
        """Returned alpha must lie within the custom bounds."""
        alpha = estimate_alpha(2023, 2024, db_path=multi_race_db, alpha_bounds=(2.0, 5.0))
        assert 2.0 <= alpha <= 5.0

    def test_n_steps_one_no_error(self, multi_race_db: Path) -> None:
        """n_steps=1 should return the single candidate without error."""
        alpha = estimate_alpha(2023, 2024, db_path=multi_race_db, n_steps=1)
        assert alpha == 0.0  # linspace(0, 15, 1) = [0.0]

    def test_empty_data_returns_lower_bound(self, tmp_db: Path) -> None:
        """Year range with no data returns alpha_bounds[0]."""
        alpha = estimate_alpha(1900, 1901, db_path=tmp_db)
        assert alpha == 0.0

    def test_custom_bounds_empty_data_returns_lower_bound(self, tmp_db: Path) -> None:
        """Empty data with custom bounds returns the lower bound."""
        alpha = estimate_alpha(1900, 1901, db_path=tmp_db, alpha_bounds=(3.0, 8.0))
        assert alpha == 3.0

    def test_deterministic(self, multi_race_db: Path) -> None:
        """Same inputs produce the same result (grid search is deterministic)."""
        alpha1 = estimate_alpha(2023, 2024, db_path=multi_race_db, n_steps=5)
        alpha2 = estimate_alpha(2023, 2024, db_path=multi_race_db, n_steps=5)
        assert alpha1 == alpha2
