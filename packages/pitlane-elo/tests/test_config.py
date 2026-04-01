"""Tests for pitlane_elo.config."""

from __future__ import annotations

import dataclasses

import pytest
from pitlane_elo.config import ENDURE_ELO_DEFAULT, SPEED_ELO_DEFAULT, EloConfig


class TestEloConfig:
    def test_frozen(self) -> None:
        cfg = EloConfig(name="test")
        with pytest.raises(AttributeError):
            cfg.name = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        cfg = EloConfig(name="test")
        assert cfg.initial_rating == 0.0
        assert cfg.k_factor == 32.0
        assert cfg.exclude_mechanical_dnf is True

    def test_prebuilt_configs_exist(self) -> None:
        assert ENDURE_ELO_DEFAULT.name == "endure-elo-default"
        assert SPEED_ELO_DEFAULT.name == "speed-elo-default"
        assert SPEED_ELO_DEFAULT.exclude_mechanical_dnf is False

    def test_alpha_default_is_zero(self) -> None:
        cfg = EloConfig(name="test")
        assert cfg.alpha == 0.0

    def test_alpha_in_asdict(self) -> None:
        """alpha must appear in dataclasses.asdict output for JSON serialisation."""
        cfg = EloConfig(name="test")
        d = dataclasses.asdict(cfg)
        assert "alpha" in d
        assert d["alpha"] == 0.0

    def test_existing_configs_have_alpha_zero(self) -> None:
        """Pre-built configs default to alpha=0.0 (backward compat)."""
        assert ENDURE_ELO_DEFAULT.alpha == 0.0
        assert SPEED_ELO_DEFAULT.alpha == 0.0

    def test_alpha_custom_value(self) -> None:
        cfg = EloConfig(name="test", alpha=7.3)
        assert cfg.alpha == pytest.approx(7.3)
