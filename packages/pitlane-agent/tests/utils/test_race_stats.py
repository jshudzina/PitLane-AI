"""Tests for race_stats utility module."""

from unittest.mock import MagicMock

import pandas as pd
from fastf1.exceptions import DataNotLoadedError
from pitlane_agent.utils.race_stats import (
    compute_driver_position_stats,
    compute_race_summary_stats,
    compute_race_summary_stats_from_results,
    get_circuit_length_km,
    get_grid_position,
)


def _make_session_with_grid(driver_laps_map: dict[str, dict]) -> MagicMock:
    """Create a mock session with laps data and GridPosition in session.results.

    Extends _make_session_with_laps by adding a real results DataFrame so that
    get_grid_position() returns the configured grid position.

    Args:
        driver_laps_map: Dict mapping driver abbreviation to dict with
            'positions' (list of floats), 'grid_position' (int), and
            optionally 'pit_laps' (list of ints)
    """
    session = _make_session_with_laps(driver_laps_map)
    results_rows = [
        {"Abbreviation": abbr, "GridPosition": float(data.get("grid_position", 0))}
        for abbr, data in driver_laps_map.items()
    ]
    session.results = pd.DataFrame(results_rows)
    return session


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


class TestGetGridPosition:
    """Tests for get_grid_position."""

    def test_returns_grid_position_when_available(self):
        """Test that grid position is returned from session.results."""
        session = _make_session_with_grid({"VER": {"positions": [1], "grid_position": 3}})
        assert get_grid_position("VER", session) == 3

    def test_returns_none_when_no_results(self):
        """Test that None is returned when session has no results."""
        session = MagicMock()
        session.results = None
        assert get_grid_position("VER", session) is None

    def test_returns_none_when_gridposition_column_missing(self):
        """Test that None is returned when GridPosition column is absent."""
        session = MagicMock()
        session.results = pd.DataFrame({"Abbreviation": ["VER"]})
        assert get_grid_position("VER", session) is None

    def test_returns_none_when_driver_not_in_results(self):
        """Test that None is returned when driver is not in results."""
        session = _make_session_with_grid({"HAM": {"positions": [1], "grid_position": 2}})
        assert get_grid_position("VER", session) is None

    def test_returns_none_for_zero_grid_position(self):
        """Test that zero or missing grid position (e.g. DNQ, testing) returns None."""
        session = _make_session_with_grid({"VER": {"positions": [1], "grid_position": 0}})
        assert get_grid_position("VER", session) is None

    def test_returns_none_on_exception(self):
        """Test that exceptions are swallowed and None is returned."""
        session = MagicMock()
        session.results = property(lambda self: (_ for _ in ()).throw(Exception("no data")))
        assert get_grid_position("VER", session) is None


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

    def test_start_position_uses_grid_position(self):
        """Test that start_position comes from grid position, not Lap 1 position."""
        # Grid P10 → Lap 1 P8 (gained 2 on opening lap) → Lap 2 P6 → Lap 3 P5
        session = _make_session_with_grid({"VER": {"positions": [8, 6, 5], "grid_position": 10}})

        result = compute_driver_position_stats("VER", session)

        assert result is not None
        assert result["start_position"] == 10  # From grid, not Lap 1
        assert result["finish_position"] == 5
        assert result["net_change"] == 5  # 10 - 5
        # Grid→Lap1 transition (10→8 = gain) is included in overtakes
        assert result["overtakes"] == 3  # grid→L1, L1→L2, L2→L3 all gains
        assert result["times_overtaken"] == 0
        assert result["biggest_gain"] == 2  # 10→8 on opening lap

    def test_stats_without_grid_position_falls_back_to_lap1(self):
        """Test fallback to Lap 1 position when grid position is unavailable."""
        # No GridPosition in results — falls back to Lap 1 value
        session = _make_session_with_laps({"VER": {"positions": [8, 6, 5]}})

        result = compute_driver_position_stats("VER", session)

        assert result is not None
        assert result["start_position"] == 8  # Lap 1 value
        assert result["net_change"] == 3  # 8 - 5


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


def _make_results_only_session(rows: list[dict]) -> MagicMock:
    """Create a mock session with results but no lap data (simulates pre-2018)."""
    session = MagicMock()
    type(session).laps = property(lambda self: (_ for _ in ()).throw(DataNotLoadedError("Not loaded")))
    session.results = pd.DataFrame(rows)
    return session


class TestComputeRaceSummaryStatsFromResults:
    """Tests for compute_race_summary_stats_from_results."""

    def test_basic_position_changes(self):
        """Test position changes and overtakes from grid vs finish."""
        # grids [1,5,10], finishes [3,2,8]
        # changes: |1-3|=2, |5-2|=3, |10-8|=2 → total=7
        # overtakes: max(0,1-3)=0, max(0,5-2)=3, max(0,10-8)=2 → total=5
        session = _make_results_only_session([
            {"GridPosition": 1.0, "Position": 3.0, "Laps": 78},
            {"GridPosition": 5.0, "Position": 2.0, "Laps": 78},
            {"GridPosition": 10.0, "Position": 8.0, "Laps": 76},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_position_changes"] == 7
        assert result["total_overtakes"] == 5
        assert result["average_volatility"] == 0.0
        assert result["mean_pit_stops"] == 0.0

    def test_laps_extracted(self):
        """Test that total_laps is the max of the Laps column."""
        session = _make_results_only_session([
            {"GridPosition": 1.0, "Position": 1.0, "Laps": 57},
            {"GridPosition": 2.0, "Position": 2.0, "Laps": 55},
            {"GridPosition": 3.0, "Position": 3.0, "Laps": 53},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_laps"] == 57

    def test_zero_grid_excluded(self):
        """Test that drivers with GridPosition=0 (pit lane start) are excluded."""
        session = _make_results_only_session([
            {"GridPosition": 0.0, "Position": 5.0, "Laps": 50},  # pit lane start
            {"GridPosition": 3.0, "Position": 1.0, "Laps": 50},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        # Only the second driver counted: |3-1|=2, max(0,3-1)=2
        assert result["total_position_changes"] == 2
        assert result["total_overtakes"] == 2

    def test_nan_grid_excluded(self):
        """Test that drivers with NaN GridPosition are excluded."""
        session = _make_results_only_session([
            {"GridPosition": float("nan"), "Position": 5.0, "Laps": 50},
            {"GridPosition": 4.0, "Position": 2.0, "Laps": 50},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_position_changes"] == 2
        assert result["total_overtakes"] == 2

    def test_nan_finish_excluded(self):
        """Test that drivers with NaN finish Position are excluded."""
        session = _make_results_only_session([
            {"GridPosition": 2.0, "Position": float("nan"), "Laps": 10},  # DNF
            {"GridPosition": 4.0, "Position": 2.0, "Laps": 50},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_position_changes"] == 2
        assert result["total_overtakes"] == 2

    def test_missing_grid_column_returns_none(self):
        """Test that missing GridPosition column returns None."""
        session = MagicMock()
        session.results = pd.DataFrame({"Position": [1.0, 2.0]})
        result = compute_race_summary_stats_from_results(session)
        assert result is None

    def test_missing_position_column_returns_none(self):
        """Test that missing Position column returns None."""
        session = MagicMock()
        session.results = pd.DataFrame({"GridPosition": [1.0, 2.0]})
        result = compute_race_summary_stats_from_results(session)
        assert result is None

    def test_empty_results_returns_none(self):
        """Test that empty results DataFrame returns None."""
        session = MagicMock()
        session.results = pd.DataFrame()
        result = compute_race_summary_stats_from_results(session)
        assert result is None

    def test_none_results_returns_none(self):
        """Test that None results returns None."""
        session = MagicMock()
        session.results = None
        result = compute_race_summary_stats_from_results(session)
        assert result is None

    def test_missing_laps_column_gives_zero_laps(self):
        """Test that missing Laps column results in total_laps=0."""
        session = MagicMock()
        session.results = pd.DataFrame({"GridPosition": [1.0], "Position": [1.0]})
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_laps"] == 0

    def test_all_laps_nan_gives_zero_laps(self):
        """Test that all-NaN Laps column results in total_laps=0."""
        session = _make_results_only_session([
            {"GridPosition": 1.0, "Position": 1.0, "Laps": float("nan")},
        ])
        result = compute_race_summary_stats_from_results(session)
        assert result is not None
        assert result["total_laps"] == 0

    def test_exception_returns_none(self):
        """Test that unexpected exceptions are swallowed and return None."""
        session = MagicMock()
        session.results = property(lambda self: (_ for _ in ()).throw(AttributeError("boom")))
        result = compute_race_summary_stats_from_results(session)
        assert result is None
