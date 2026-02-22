"""Tests for generate_driver_lap_list."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pitlane_agent.commands.analyze.driver_lap_list import _compute_stint_numbers, generate_driver_lap_list

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIMESTAMP = pd.Timestamp("2024-05-26 14:00:00")
_NAT = pd.NaT


def _make_driver_laps_df(
    *,
    lap_numbers: list[int] | None = None,
    lap_times_sec: list[float | None] | None = None,
    compounds: list[str | None] | None = None,
    tyre_life: list[int | None] | None = None,
    pit_out: list[bool] | None = None,
    pit_in: list[bool] | None = None,
    positions: list[int | None] | None = None,
    is_accurate: list[bool] | None = None,
    include_stint_col: bool = False,
    stints: list[int] | None = None,
) -> pd.DataFrame:
    """Build a minimal driver laps DataFrame for testing.

    By default produces 3 accurate laps on SOFT tyres.
    """
    lap_numbers = lap_numbers if lap_numbers is not None else [1, 2, 3]
    n = len(lap_numbers)
    lap_times_sec = lap_times_sec if lap_times_sec is not None else [90.0, 91.0, 89.5][:n] + [90.0] * max(0, n - 3)
    compounds = compounds if compounds is not None else ["SOFT"] * n
    tyre_life = tyre_life if tyre_life is not None else list(range(1, n + 1))
    pit_out = pit_out if pit_out is not None else [False] * n
    pit_in = pit_in if pit_in is not None else [False] * n
    positions = positions if positions is not None else list(range(5, 5 + n))
    is_accurate = is_accurate if is_accurate is not None else [True] * n

    data = {
        "LapNumber": [float(x) for x in lap_numbers],
        "LapTime": [pd.Timedelta(seconds=t) if t is not None else _NAT for t in lap_times_sec],
        "Sector1Time": [pd.Timedelta(seconds=28.0)] * n,
        "Sector2Time": [pd.Timedelta(seconds=30.5)] * n,
        "Sector3Time": [pd.Timedelta(seconds=31.0)] * n,
        "Compound": compounds,
        "TyreLife": [float(x) if x is not None else float("nan") for x in tyre_life],
        "PitOutTime": [_TIMESTAMP if p else _NAT for p in pit_out],
        "PitInTime": [_TIMESTAMP if p else _NAT for p in pit_in],
        "Position": [float(p) if p is not None else float("nan") for p in positions],
        "IsAccurate": is_accurate,
    }
    if include_stint_col:
        data["Stint"] = [float(s) for s in (stints or [1] * n)]

    return pd.DataFrame(data)


def _make_mock_session(driver_laps_df: pd.DataFrame, event_name="Monaco Grand Prix", session_name="Race"):
    """Create a MagicMock session with the given driver laps DataFrame attached."""
    session = MagicMock()
    session.event = {"EventName": event_name}
    session.name = session_name

    mock_driver_laps = MagicMock(wraps=driver_laps_df)
    mock_driver_laps.empty = driver_laps_df.empty
    mock_driver_laps.columns = driver_laps_df.columns
    mock_driver_laps.iterrows = driver_laps_df.iterrows
    mock_driver_laps.__getitem__ = driver_laps_df.__getitem__
    mock_driver_laps.__len__ = lambda self: len(driver_laps_df)

    # Make notna() chain work on Stint column when present
    if "Stint" in driver_laps_df.columns:
        mock_driver_laps["Stint"] = driver_laps_df["Stint"]

    mock_driver_laps.__getitem__.side_effect = lambda key: (
        driver_laps_df[key] if isinstance(key, str) else driver_laps_df[key]
    )

    session.laps.pick_drivers.return_value = driver_laps_df
    return session


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestGenerateDriverLapListValidation:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_empty_driver_laps_raises(self, mock_load):
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = pd.DataFrame()  # empty DataFrame
        mock_load.return_value = session

        with pytest.raises(ValueError, match="No laps found"):
            generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")


# ---------------------------------------------------------------------------
# Success — return structure
# ---------------------------------------------------------------------------


class TestGenerateDriverLapListSuccess:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_returns_expected_top_level_keys(self, mock_load):
        df = _make_driver_laps_df()
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["event_name"] == "Monaco Grand Prix"
        assert result["session_name"] == "Race"
        assert result["year"] == 2024
        assert result["gp"] == "Monaco"
        assert result["driver"] == "VER"
        assert "laps" in result
        assert "pit_stops" in result
        assert "total_laps" in result
        assert "fastest_lap_number" in result

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_total_laps_matches_dataframe_length(self, mock_load):
        df = _make_driver_laps_df(lap_numbers=[1, 2, 3, 4, 5])
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["total_laps"] == 5
        assert len(result["laps"]) == 5

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_per_lap_fields_present(self, mock_load):
        df = _make_driver_laps_df()
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        lap = result["laps"][0]
        expected_fields = {
            "lap_number",
            "lap_time",
            "lap_time_seconds",
            "compound",
            "tyre_life",
            "stint_number",
            "is_pit_out_lap",
            "is_pit_in_lap",
            "is_accurate",
            "position",
            "position_change",
            "sector_1_time",
            "sector_2_time",
            "sector_3_time",
        }
        assert expected_fields.issubset(set(lap.keys()))

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_lap_numbers_are_correct(self, mock_load):
        df = _make_driver_laps_df(lap_numbers=[5, 10, 15])
        session = MagicMock()
        session.event = {"EventName": "Monza Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monza", session_type="R", driver="NOR")

        lap_nums = [lap["lap_number"] for lap in result["laps"]]
        assert lap_nums == [5, 10, 15]

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_fastest_lap_number_is_minimum_time(self, mock_load):
        # lap 3 has shortest lap time (89.5s)
        df = _make_driver_laps_df(lap_numbers=[1, 2, 3], lap_times_sec=[90.0, 91.0, 89.5])
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["fastest_lap_number"] == 3


# ---------------------------------------------------------------------------
# Pit detection
# ---------------------------------------------------------------------------


class TestPitDetection:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_pit_out_lap_flagged(self, mock_load):
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3],
            pit_out=[True, False, False],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["laps"][0]["is_pit_out_lap"] is True
        assert result["laps"][1]["is_pit_out_lap"] is False
        assert result["laps"][2]["is_pit_out_lap"] is False

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_pit_in_lap_flagged(self, mock_load):
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3],
            pit_in=[False, True, False],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["laps"][1]["is_pit_in_lap"] is True
        assert result["laps"][0]["is_pit_in_lap"] is False
        assert result["laps"][2]["is_pit_in_lap"] is False

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_pit_stop_detected_on_compound_change(self, mock_load):
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4],
            compounds=["SOFT", "SOFT", "MEDIUM", "MEDIUM"],
            pit_in=[False, True, False, False],
            pit_out=[False, False, True, False],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert len(result["pit_stops"]) == 1
        stop = result["pit_stops"][0]
        assert stop["from_compound"] == "SOFT"
        assert stop["to_compound"] == "MEDIUM"
        assert stop["lap_number"] == 3  # first lap on new compound

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_no_pit_stops_single_stint(self, mock_load):
        df = _make_driver_laps_df(compounds=["SOFT", "SOFT", "SOFT"])
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["pit_stops"] == []


# ---------------------------------------------------------------------------
# Position change
# ---------------------------------------------------------------------------


class TestPositionChange:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_position_change_positive_when_gaining(self, mock_load):
        # Positions: 5, 4, 3 — gaining 1 place each lap
        df = _make_driver_laps_df(lap_numbers=[1, 2, 3], positions=[5, 4, 3])
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["laps"][0]["position_change"] == 0  # no previous lap
        assert result["laps"][1]["position_change"] == 1  # gained 1 (5→4)
        assert result["laps"][2]["position_change"] == 1  # gained 1 (4→3)

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_position_change_negative_when_losing(self, mock_load):
        # Positions: 3, 4, 5 — losing 1 place each lap
        df = _make_driver_laps_df(lap_numbers=[1, 2, 3], positions=[3, 4, 5])
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["laps"][1]["position_change"] == -1
        assert result["laps"][2]["position_change"] == -1


# ---------------------------------------------------------------------------
# Stint number computation
# ---------------------------------------------------------------------------


class TestStintComputation:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_stint_numbers_computed_from_compound_change(self, mock_load):
        # Stints: SOFT x2, MEDIUM x2 → stint 1, 1, 2, 2
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4],
            compounds=["SOFT", "SOFT", "MEDIUM", "MEDIUM"],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        stint_nums = [lap["stint_number"] for lap in result["laps"]]
        assert stint_nums == [1, 1, 2, 2]

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_fastf1_stint_column_used_when_present(self, mock_load):
        # FastF1 provides Stint column — should use it directly
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4],
            compounds=["SOFT", "SOFT", "SOFT", "SOFT"],  # no compound change
            include_stint_col=True,
            stints=[1, 1, 2, 2],  # but Stint column says two stints
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        stint_nums = [lap["stint_number"] for lap in result["laps"]]
        assert stint_nums == [1, 1, 2, 2]


# ---------------------------------------------------------------------------
# _compute_stint_numbers — direct unit tests
# ---------------------------------------------------------------------------


class TestComputeStintNumbers:
    def test_compound_change_increments_stint(self):
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4],
            compounds=["SOFT", "SOFT", "MEDIUM", "MEDIUM"],
        )
        assert _compute_stint_numbers(df) == [1, 1, 2, 2]

    def test_pit_out_same_compound_increments_stint(self):
        # Lap 3 is a pit-out lap on the same compound (e.g. minor repair)
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4],
            compounds=["SOFT", "SOFT", "SOFT", "SOFT"],
            pit_out=[False, False, True, False],
        )
        assert _compute_stint_numbers(df) == [1, 1, 2, 2]

    def test_single_compound_no_pit_out_stays_in_stint_one(self):
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3],
            compounds=["HARD", "HARD", "HARD"],
        )
        assert _compute_stint_numbers(df) == [1, 1, 1]

    def test_compound_change_and_pit_out_each_increment(self):
        # Lap 3: compound change SOFT→MEDIUM (stint 2)
        # Lap 5: pit-out same compound (stint 3)
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3, 4, 5, 6],
            compounds=["SOFT", "SOFT", "MEDIUM", "MEDIUM", "MEDIUM", "MEDIUM"],
            pit_out=[False, False, False, False, True, False],
        )
        assert _compute_stint_numbers(df) == [1, 1, 2, 2, 3, 3]


# ---------------------------------------------------------------------------
# Testing session path
# ---------------------------------------------------------------------------


class TestTestingSession:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_testing_session_passes_test_params(self, mock_load):
        df = _make_driver_laps_df()
        session = MagicMock()
        session.event = {"EventName": "Pre-Season Testing"}
        session.name = "Testing"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(
            year=2024,
            gp=None,
            session_type=None,
            driver="VER",
            test_number=1,
            session_number=2,
        )

        mock_load.assert_called_once_with(2024, None, None, telemetry=False, test_number=1, session_number=2)
        assert result["gp"] is None

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_testing_session_result_structure(self, mock_load):
        df = _make_driver_laps_df()
        session = MagicMock()
        session.event = {"EventName": "Pre-Season Testing"}
        session.name = "Testing"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(
            year=2024, gp=None, session_type=None, driver="VER", test_number=1, session_number=1
        )

        assert "laps" in result
        assert len(result["laps"]) == 3


# ---------------------------------------------------------------------------
# NaT lap times
# ---------------------------------------------------------------------------


class TestNaTHandling:
    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_nat_lap_time_returns_none(self, mock_load):
        # First lap has NaT lap time (e.g., formation lap)
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3],
            lap_times_sec=[None, 90.0, 89.5],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["laps"][0]["lap_time"] is None
        assert result["laps"][0]["lap_time_seconds"] is None

    @patch("pitlane_agent.commands.analyze.driver_lap_list.load_session_or_testing")
    def test_fastest_lap_ignores_nat_times(self, mock_load):
        # Lap 1 has NaT — fastest should be lap 3 (89.5s)
        df = _make_driver_laps_df(
            lap_numbers=[1, 2, 3],
            lap_times_sec=[None, 91.0, 89.5],
        )
        session = MagicMock()
        session.event = {"EventName": "Monaco Grand Prix"}
        session.name = "Race"
        session.laps.pick_drivers.return_value = df
        mock_load.return_value = session

        result = generate_driver_lap_list(year=2024, gp="Monaco", session_type="R", driver="VER")

        assert result["fastest_lap_number"] == 3
