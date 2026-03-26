"""Tests for pitlane_elo.config."""

from __future__ import annotations

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
