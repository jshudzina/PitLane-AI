"""Hyperparameter configuration for ELO model variants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EloConfig:
    """Immutable configuration for a single ELO model variant.

    All hyperparameters needed to fully specify a rating model run.
    Frozen to prevent accidental mutation during training.
    """

    name: str

    # Rating initialization
    initial_rating: float = 0.0

    # K-factor (learning rate)
    k_factor: float = 32.0
    k_min: float = 0.05
    k_max: float = 0.5

    # Temporal decay (AR(1) process, per Powell)
    phi_race: float = 0.99  # between-race decay within a season
    phi_season: float = 0.90  # between-season decay
    phi_regulation: float = 0.70  # major regulation change decay

    # Seasons with major regulation changes (larger reset applied)
    regulation_years: tuple[int, ...] = (2009, 2014, 2017, 2022, 2026)

    # DNF handling
    exclude_mechanical_dnf: bool = True  # Xun's approach: exclude mechanical DNFs from ELO

    # Car rating (Xun's Rc)
    car_rating_weight: float = 0.0  # 0 = pure driver Elo, >0 = Rc adjustment


# ---------------------------------------------------------------------------
# Pre-built configurations for comparison experiments
# ---------------------------------------------------------------------------

ENDURE_ELO_DEFAULT = EloConfig(
    name="endure-elo-default",
    initial_rating=0.0,
    # Powell (2023) Table 1: k = 0.36 for both endure- and speed-Elo
    k_factor=0.36,
    phi_race=0.99,
    phi_season=0.90,
    # Disabled: 2025 data classifies all DNFs as "retired" so we can't
    # distinguish mechanical failures from crashes. Re-enable once the
    # DNF classification pipeline is fixed.
    exclude_mechanical_dnf=False,
)

SPEED_ELO_DEFAULT = EloConfig(
    name="speed-elo-default",
    initial_rating=0.0,
    k_factor=0.36,  # Powell (2023) Table 1
    phi_race=0.99,
    phi_season=0.90,
    exclude_mechanical_dnf=False,  # see endure-Elo comment re: 2025 data
)
