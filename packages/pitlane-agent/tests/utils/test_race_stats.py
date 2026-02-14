"""Tests for race_stats utility module."""

from unittest.mock import MagicMock

import pandas as pd
from fastf1.exceptions import DataNotLoadedError
from pitlane_agent.utils.race_stats import (
    compute_driver_position_stats,
    compute_race_summary_stats,
    get_circuit_length_km,
)


def _make_session_with_laps(driver_laps_map: dict[str, dict]) -> MagicMock:
    """Create a mock session with laps data for multiple drivers.

    Args:
        driver_laps_map: Dict mapping driver abbreviation to dict with
            'positions' (list of floats) and optionally 'pit_laps' (list of ints)
    """
    session = MagicMock()

    all_rows = []
    drivers = []
    for abbr, data in driver_laps_map.items():
        positions = data["positions"]
        pit_laps = data.get("pit_laps", [])
        drivers.append(abbr)
        for i, pos in enumerate(positions):
            lap_num = i + 1
            pit_out = pd.Timestamp("2024-01-01") if lap_num in pit_laps else pd.NaT
            all_rows.append(
                {
                    "Driver": abbr,
                    "LapNumber": lap_num,
                    "Position": pos,
                    "PitOutTime": pit_out,
                }
            )

    full_df = pd.DataFrame(all_rows)

    def pick_drivers(abbr):
        return full_df[full_df["Driver"] == abbr].copy()

    session.laps = MagicMock()
    session.laps.pick_drivers = pick_drivers
    session.laps.pick_fastest = MagicMock(return_value=None)
    session.laps.empty = len(all_rows) == 0
    session.drivers = list(range(len(drivers)))

    def get_driver(idx):
        return {"Abbreviation": drivers[idx]}

    session.get_driver = get_driver

    return session


class TestComputeDriverPositionStats:
    """Tests for compute_driver_position_stats."""

    def test_basic_stats(self):
        """Test basic position stats computation."""
        session = _make_session_with_laps(
            {
                "VER": {"positions": [1, 1, 1, 1, 1]},
            }
        )

        result = compute_driver_position_stats("VER", session)

        assert result is not None
        assert result["driver"] == "VER"
        assert result["start_position"] == 1
        assert result["finish_position"] == 1
        assert result["net_change"] == 0
        assert result["overtakes"] == 0
        assert result["times_overtaken"] == 0
        assert result["volatility"] == 0.0
        assert result["total_laps"] == 5
        assert result["pit_stops"] == 0

    def test_position_gains(self):
        """Test driver gaining positions."""
        session = _make_session_with_laps(
            {
                "HAM": {"positions": [5, 4, 3, 2, 1]},
            }
        )

        result = compute_driver_position_stats("HAM", session)

        assert result is not None
        assert result["start_position"] == 5
        assert result["finish_position"] == 1
        assert result["net_change"] == 4
        assert result["overtakes"] == 4
        assert result["times_overtaken"] == 0
        assert result["biggest_gain"] == 1
        # biggest_loss uses abs(max(diffs)); when all diffs are negative, max is -1
        assert result["biggest_loss"] == 1

    def test_volatile_driver(self):
        """Test driver with lots of position changes."""
        session = _make_session_with_laps(
            {
                "NOR": {"positions": [3, 8, 2, 10, 1]},
            }
        )

        result = compute_driver_position_stats("NOR", session)

        assert result is not None
        assert result["overtakes"] == 2
        assert result["times_overtaken"] == 2
        assert result["biggest_gain"] == 9  # 10 -> 1
        assert result["biggest_loss"] == 8  # 2 -> 10
        assert result["volatility"] > 0

    def test_pit_stops_counted(self):
        """Test pit stop counting."""
        session = _make_session_with_laps(
            {
                "LEC": {"positions": [3, 3, 3, 3, 3], "pit_laps": [2, 4]},
            }
        )

        result = compute_driver_position_stats("LEC", session)

        assert result is not None
        assert result["pit_stops"] == 2

    def test_empty_laps_returns_none(self):
        """Test that empty laps returns None."""
        session = MagicMock()
        session.laps.pick_drivers.return_value = pd.DataFrame()

        result = compute_driver_position_stats("VER", session)

        assert result is None

    def test_all_nan_positions_returns_none(self):
        """Test that all NaN positions returns None."""
        session = MagicMock()
        df = pd.DataFrame(
            {
                "LapNumber": [1, 2, 3],
                "Position": [float("nan"), float("nan"), float("nan")],
                "PitOutTime": [pd.NaT, pd.NaT, pd.NaT],
            }
        )
        session.laps.pick_drivers.return_value = df

        result = compute_driver_position_stats("VER", session)

        assert result is None


class TestComputeRaceSummaryStats:
    """Tests for compute_race_summary_stats."""

    def test_basic_race_summary(self):
        """Test basic race summary computation."""
        session = _make_session_with_laps(
            {
                "VER": {"positions": [1, 1, 1, 1, 1], "pit_laps": [3]},
                "HAM": {"positions": [5, 4, 3, 2, 2], "pit_laps": [2]},
            }
        )

        result = compute_race_summary_stats(session)

        assert result is not None
        assert result["total_overtakes"] == 3  # HAM made 3 overtakes
        assert result["total_position_changes"] == 3  # VER 0 + HAM 3
        assert result["mean_pit_stops"] == 1.0
        assert result["average_volatility"] > 0
        assert result["total_laps"] == 5

    def test_empty_laps_returns_none(self):
        """Test that empty laps returns None."""
        session = MagicMock()
        session.laps = MagicMock()
        session.laps.empty = True

        result = compute_race_summary_stats(session)

        assert result is None

    def test_data_not_loaded_returns_none(self):
        """Test that DataNotLoadedError returns None."""
        session = MagicMock()
        type(session).laps = property(lambda self: (_ for _ in ()).throw(DataNotLoadedError("Laps not loaded")))

        result = compute_race_summary_stats(session)

        assert result is None

    def test_multi_driver_aggregation(self):
        """Test aggregation across multiple drivers."""
        session = _make_session_with_laps(
            {
                "VER": {"positions": [1, 2, 1, 2, 1], "pit_laps": [2, 4]},
                "HAM": {"positions": [2, 1, 2, 1, 2], "pit_laps": [3]},
                "LEC": {"positions": [3, 3, 3, 3, 3], "pit_laps": [2]},
            }
        )

        result = compute_race_summary_stats(session)

        assert result is not None
        assert result["total_overtakes"] > 0
        assert result["mean_pit_stops"] == round((2 + 1 + 1) / 3, 2)
        assert result["total_laps"] == 5


class TestGetCircuitLengthKm:
    """Tests for get_circuit_length_km."""

    def test_returns_distance_from_fastest_lap(self):
        """Test that circuit length is computed from fastest lap telemetry."""
        session = MagicMock()
        fastest_lap = MagicMock()
        session.laps.pick_fastest.return_value = fastest_lap

        telemetry = pd.DataFrame({"Distance": [0.0, 1500.0, 3000.0, 5303.0]})
        fastest_lap.get_car_data.return_value.add_distance.return_value = telemetry

        result = get_circuit_length_km(session)

        assert result == 5.303

    def test_returns_none_when_no_fastest_lap(self):
        """Test that None is returned when pick_fastest returns None."""
        session = MagicMock()
        session.laps.pick_fastest.return_value = None

        result = get_circuit_length_km(session)

        assert result is None

    def test_returns_none_on_exception(self):
        """Test that None is returned when telemetry raises an exception."""
        session = MagicMock()
        session.laps.pick_fastest.side_effect = Exception("No data")

        result = get_circuit_length_km(session)

        assert result is None

    def test_returns_none_when_telemetry_empty(self):
        """Test that None is returned when telemetry DataFrame is empty."""
        session = MagicMock()
        fastest_lap = MagicMock()
        session.laps.pick_fastest.return_value = fastest_lap
        fastest_lap.get_car_data.return_value.add_distance.return_value = pd.DataFrame()

        result = get_circuit_length_km(session)

        assert result is None
