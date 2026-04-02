"""Tests for pitlane_elo.separation.alpha_estimation."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pitlane_elo.separation.alpha_estimation import estimate_alpha


class TestEstimateAlpha:
    def test_returns_float(self, multi_race_db: Path) -> None:
        """Result is a float."""
        alpha = estimate_alpha(2023, 2024, db_path=multi_race_db)
        assert isinstance(alpha, float)

    def test_result_is_finite(self, multi_race_db: Path) -> None:
        """OLS result must be a finite number, not NaN or inf."""
        alpha = estimate_alpha(2023, 2024, db_path=multi_race_db)
        assert np.isfinite(alpha)

    def test_deterministic(self, multi_race_db: Path) -> None:
        """Same inputs always produce the same result (no randomness in OLS)."""
        alpha1 = estimate_alpha(2023, 2024, db_path=multi_race_db)
        alpha2 = estimate_alpha(2023, 2024, db_path=multi_race_db)
        assert alpha1 == alpha2

    def test_empty_data_returns_zero(self, tmp_db: Path) -> None:
        """Year range with no data returns 0.0 (safe default)."""
        alpha = estimate_alpha(1900, 1901, db_path=tmp_db)
        assert alpha == 0.0
