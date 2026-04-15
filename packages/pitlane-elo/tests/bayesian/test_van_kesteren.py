"""Tests for pitlane_elo.bayesian.van_kesteren."""

from __future__ import annotations

import arviz as az
import numpy as np
import pytest
from pitlane_elo.bayesian.van_kesteren import VAN_KESTEREN_FAST, VanKesterenConfig, VanKesterenModel


@pytest.mark.bayesian
class TestSmoke:
    """Category 1: model runs, returns correct types, keys match inputs."""

    def test_fit_returns_inference_data(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        trace = model.fit(dominant_season)
        assert isinstance(trace, az.InferenceData)

    def test_driver_ratings_keys(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ratings = model.driver_ratings()
        assert set(ratings) == {"driver_a", "driver_b", "driver_c"}

    def test_team_ratings_keys(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ratings = model.team_ratings()
        assert set(ratings) == {"TeamA", "TeamB"}

    def test_driver_ranking_structure(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ranking = model.driver_ranking()
        assert len(ranking) == 3
        # Each entry is (str, float).
        for name, score in ranking:
            assert isinstance(name, str)
            assert isinstance(score, float)
        # Descending order.
        scores = [s for _, s in ranking]
        assert scores == sorted(scores, reverse=True)

    def test_team_ranking_structure(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ranking = model.team_ranking()
        scores = [s for _, s in ranking]
        assert scores == sorted(scores, reverse=True)

    def test_trace_property(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        assert isinstance(model.trace, az.InferenceData)

    def test_season_data_property(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        assert model.season_data.n_drivers == 3

    def test_unfitted_raises(self) -> None:
        model = VanKesterenModel(VAN_KESTEREN_FAST)
        with pytest.raises(RuntimeError, match="not been fitted"):
            model.driver_ratings()

    def test_credible_intervals_structure(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        cis = model.driver_credible_intervals()
        assert set(cis) == {"driver_a", "driver_b", "driver_c"}
        for lo, hi in cis.values():
            assert lo < hi


@pytest.mark.bayesian
class TestIdentifiability:
    """Category 2: ZeroSumNormal enforces sum-to-zero constraint."""

    def test_driver_ratings_sum_to_zero(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        total = sum(model.driver_ratings().values())
        assert abs(total) < 1e-6

    def test_team_ratings_sum_to_zero(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        total = sum(model.team_ratings().values())
        assert abs(total) < 1e-6


@pytest.mark.bayesian
class TestRankOrdering:
    """Category 3: dominant fixture produces correct hierarchy."""

    def test_driver_a_beats_driver_b(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ratings = model.driver_ratings()
        assert ratings["driver_a"] > ratings["driver_b"]

    def test_driver_b_beats_driver_c(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ratings = model.driver_ratings()
        assert ratings["driver_b"] > ratings["driver_c"]

    def test_team_a_beats_team_b(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        ratings = model.team_ratings()
        assert ratings["TeamA"] > ratings["TeamB"]

    def test_driver_ranking_top_is_driver_a(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        top_driver, _ = model.driver_ranking()[0]
        assert top_driver == "driver_a"


@pytest.mark.bayesian
class TestStep2:
    """Category 4: seasonal form deviations (model_step=2)."""

    def test_fit_returns_inference_data(
        self,
        dominant_season: list,
        fast_config_step2: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config_step2)
        trace = model.fit(dominant_season)
        assert isinstance(trace, az.InferenceData)

    def test_seasonal_driver_ratings_keys(
        self,
        dominant_season: list,
        fast_config_step2: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config_step2)
        model.fit(dominant_season)
        ratings = model.seasonal_driver_ratings()
        assert set(ratings) == {"driver_a", "driver_b", "driver_c"}

    def test_seasonal_team_ratings_keys(
        self,
        dominant_season: list,
        fast_config_step2: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config_step2)
        model.fit(dominant_season)
        ratings = model.seasonal_team_ratings()
        assert set(ratings) == {"TeamA", "TeamB"}

    def test_seasonal_ratings_are_finite(
        self,
        dominant_season: list,
        fast_config_step2: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config_step2)
        model.fit(dominant_season)
        for v in model.seasonal_driver_ratings().values():
            assert np.isfinite(v)
        for v in model.seasonal_team_ratings().values():
            assert np.isfinite(v)

    def test_seasonal_driver_ratings_raises_on_step1(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        with pytest.raises(RuntimeError, match="model_step"):
            model.seasonal_driver_ratings()

    def test_seasonal_team_ratings_raises_on_step1(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        with pytest.raises(RuntimeError, match="model_step"):
            model.seasonal_team_ratings()

    def test_seasonal_ratings_sum_to_zero(
        self,
        dominant_season: list,
        fast_config_step2: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config_step2)
        model.fit(dominant_season)
        assert abs(sum(model.seasonal_driver_ratings().values())) < 1e-6
        assert abs(sum(model.seasonal_team_ratings().values())) < 1e-6


@pytest.mark.bayesian
class TestPredictWinProbabilities:
    """Category 5: posterior predictive win probability computation."""

    def test_probabilities_sum_to_one(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        lineup = [("driver_a", "TeamA"), ("driver_b", "TeamA"), ("driver_c", "TeamB")]
        probs = model.predict_win_probabilities(lineup)
        assert abs(probs.sum() - 1.0) < 1e-6

    def test_dominant_driver_highest_probability(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        """driver_a always wins in dominant_season — should get highest win prob."""
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        lineup = [("driver_a", "TeamA"), ("driver_b", "TeamA"), ("driver_c", "TeamB")]
        probs = model.predict_win_probabilities(lineup)
        assert probs[0] > probs[1]
        assert probs[0] > probs[2]

    def test_unknown_driver_gets_prior_mean(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        """Unknown driver has eta=0; probs must still sum to 1 and be positive."""
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        lineup = [("driver_a", "TeamA"), ("unknown_rookie", "UnknownTeam")]
        probs = model.predict_win_probabilities(lineup)
        assert abs(probs.sum() - 1.0) < 1e-6
        assert np.all(probs > 0)

    def test_returns_numpy_array(
        self,
        dominant_season: list,
        fast_config: VanKesterenConfig,
    ) -> None:
        model = VanKesterenModel(fast_config)
        model.fit(dominant_season)
        lineup = [("driver_a", "TeamA"), ("driver_b", "TeamA")]
        probs = model.predict_win_probabilities(lineup)
        assert isinstance(probs, np.ndarray)
        assert probs.shape == (2,)

    def test_raises_when_unfitted(self) -> None:
        model = VanKesterenModel()
        with pytest.raises(RuntimeError):
            model.predict_win_probabilities([("driver_a", "TeamA")])


@pytest.mark.slow
@pytest.mark.bayesian
class TestConvergence:
    """Category 5: MCMC convergence diagnostics. Slow — run with -m slow."""

    def test_rhat_below_threshold(self, dominant_season: list) -> None:
        """R-hat for all theta_d chains should be < 1.05."""
        config = VanKesterenConfig(
            name="van-kesteren-convergence",
            draws=1000,
            tune=1000,
            chains=4,
            random_seed=0,
        )
        model = VanKesterenModel(config)
        model.fit(dominant_season)
        rhat = az.rhat(model.trace)["theta_d"].values
        assert np.all(rhat < 1.05), f"R-hat exceeded threshold: {rhat}"
