"""Tests for telemetry_analysis utility module."""

import numpy as np
import pandas as pd
import pytest
from pitlane_agent.utils.telemetry_analysis import (
    analyze_telemetry,
    detect_lift_and_coast_zones,
    detect_super_clipping_zones,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_telemetry(
    n: int = 500,
    speed: float = 300.0,
    throttle: float = 100.0,
    brake: int = 0,
    rpm: float = 11000.0,
    gear: int = 8,
    lap_seconds: float = 90.0,
) -> pd.DataFrame:
    """Build a baseline telemetry DataFrame with constant values.

    Returns a DataFrame with *n* rows and columns matching FastF1's
    car-data channels: Distance, Speed, Throttle, Brake, RPM, nGear,
    Time.  All channels are constant by default — callers modify slices
    to inject specific zones.
    """
    return pd.DataFrame(
        {
            "Distance": np.linspace(0, 5000, n),
            "Speed": np.full(n, speed),
            "Throttle": np.full(n, throttle),
            "Brake": np.full(n, brake),
            "RPM": np.full(n, rpm),
            "nGear": np.full(n, gear, dtype=int),
            "Time": pd.to_timedelta(np.linspace(0, lap_seconds, n), unit="s"),
        }
    )


def _inject_lift_coast(
    df: pd.DataFrame,
    start: int,
    end: int,
    speed_from: float = 300.0,
    speed_to: float = 270.0,
    rpm_from: float = 11000.0,
    rpm_to: float = 9000.0,
) -> pd.DataFrame:
    """Inject a lift-and-coast zone into *df* between indices *start* and *end*."""
    df = df.copy()
    df.loc[start : end - 1, "Throttle"] = 0.0
    df.loc[start : end - 1, "Speed"] = np.linspace(speed_from, speed_to, end - start)
    df.loc[start : end - 1, "RPM"] = np.linspace(rpm_from, rpm_to, end - start)
    return df


def _inject_super_clip(
    df: pd.DataFrame,
    start: int,
    end: int,
    speed: float = 330.0,
    rpm: float = 11500.0,
) -> pd.DataFrame:
    """Inject a super-clipping zone into *df* between indices *start* and *end*.

    Sets throttle to 100 %, speed constant (plateau), and RPM constant
    (no longer climbing) in a high gear.
    """
    df = df.copy()
    df.loc[start : end - 1, "Throttle"] = 100.0
    df.loc[start : end - 1, "Speed"] = speed
    df.loc[start : end - 1, "RPM"] = rpm
    df.loc[start : end - 1, "nGear"] = 8
    return df


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_dataframe_raises(self):
        empty = pd.DataFrame()
        with pytest.raises(ValueError, match="empty"):
            detect_lift_and_coast_zones(empty)

    def test_missing_columns_raises_lift_coast(self):
        df = pd.DataFrame({"Distance": [0, 1], "Speed": [300, 300]})
        with pytest.raises(ValueError, match="Missing required"):
            detect_lift_and_coast_zones(df)

    def test_missing_columns_raises_super_clip(self):
        df = pd.DataFrame({"Distance": [0, 1], "Speed": [300, 300]})
        with pytest.raises(ValueError, match="Missing required"):
            detect_super_clipping_zones(df)


# ---------------------------------------------------------------------------
# Lift and Coast
# ---------------------------------------------------------------------------


class TestDetectLiftAndCoastZones:
    def test_single_zone_detected(self):
        df = _make_telemetry()
        df = _inject_lift_coast(df, 100, 150)
        zones = detect_lift_and_coast_zones(df)

        assert len(zones) == 1
        zone = zones[0]
        assert zone["start_distance"] == pytest.approx(df["Distance"].iloc[100], abs=1)
        assert zone["end_distance"] == pytest.approx(df["Distance"].iloc[149], abs=1)
        assert zone["duration"] > 0
        assert zone["speed_loss"] > 0
        assert zone["avg_rpm_drop"] > 0

    def test_multiple_zones(self):
        df = _make_telemetry()
        df = _inject_lift_coast(df, 50, 100)
        df = _inject_lift_coast(df, 300, 350)
        zones = detect_lift_and_coast_zones(df)

        assert len(zones) == 2
        assert zones[0]["start_distance"] < zones[1]["start_distance"]

    def test_short_zone_filtered_by_min_duration(self):
        df = _make_telemetry(n=500, lap_seconds=90.0)
        # 3 samples at 90s/500 ≈ 0.54s spacing → zone ≈ 1.08s
        # but make the zone very short: only 2 samples → ~0.36s
        df = _inject_lift_coast(df, 100, 102)
        zones = detect_lift_and_coast_zones(df, min_duration=1.0)

        assert len(zones) == 0

    def test_speed_increase_excluded(self):
        """A zone where speed rises (e.g. downhill) should not be flagged."""
        df = _make_telemetry()
        df = _inject_lift_coast(df, 100, 150, speed_from=270.0, speed_to=300.0)
        zones = detect_lift_and_coast_zones(df)

        assert len(zones) == 0

    def test_no_zones_in_clean_telemetry(self):
        df = _make_telemetry()
        zones = detect_lift_and_coast_zones(df)

        assert zones == []

    def test_brake_on_excludes_zone(self):
        """If brake is applied during the coast, it's not lift-and-coast."""
        df = _make_telemetry()
        df = _inject_lift_coast(df, 100, 150)
        df.loc[120:130, "Brake"] = 1  # brake applied mid-zone
        zones = detect_lift_and_coast_zones(df)

        # The brake splits the zone; the sub-segments may or may not
        # meet the min_duration threshold, but none should span the
        # full original range.
        for z in zones:
            assert not (
                z["start_distance"] <= df["Distance"].iloc[100] and z["end_distance"] >= df["Distance"].iloc[149]
            )


# ---------------------------------------------------------------------------
# Super Clipping
# ---------------------------------------------------------------------------


class TestDetectSuperClippingZones:
    def test_single_zone_detected(self):
        df = _make_telemetry()
        # Set baseline to accelerating (speed & RPM climbing) then inject plateau
        df["Speed"] = np.linspace(200, 340, len(df))
        df["RPM"] = np.linspace(8000, 12000, len(df))
        df = _inject_super_clip(df, 350, 420, speed=330.0, rpm=11500.0)
        zones = detect_super_clipping_zones(df)

        assert len(zones) >= 1
        zone = zones[0]
        assert zone["throttle_percent"] >= 95.0
        assert zone["gear"] >= 6

    def test_low_gear_excluded(self):
        df = _make_telemetry(throttle=50.0)  # baseline below full-throttle
        df = _inject_super_clip(df, 350, 420, speed=330.0, rpm=11500.0)
        df.loc[350:419, "nGear"] = 4  # low gear
        zones = detect_super_clipping_zones(df)

        assert len(zones) == 0

    def test_short_zone_filtered(self):
        df = _make_telemetry(n=500, lap_seconds=90.0, throttle=50.0)
        # Very short injection — only 2 samples
        df = _inject_super_clip(df, 350, 352, speed=330.0, rpm=11500.0)
        zones = detect_super_clipping_zones(df, min_duration=1.0)

        assert len(zones) == 0

    def test_no_zones_when_accelerating(self):
        """Constantly accelerating telemetry should not flag clipping."""
        df = _make_telemetry(throttle=50.0)
        # Steep ramp so rolling std is high (not a plateau)
        df["Speed"] = np.linspace(100, 340, len(df))
        df["RPM"] = np.linspace(5000, 12000, len(df))
        zones = detect_super_clipping_zones(df)

        assert zones == []

    def test_no_zones_in_clean_telemetry(self):
        """Constant-speed full-throttle telemetry should NOT flag as
        clipping — there is no preceding acceleration phase."""
        df = _make_telemetry()
        zones = detect_super_clipping_zones(df)

        assert zones == []


# ---------------------------------------------------------------------------
# Aggregated analysis
# ---------------------------------------------------------------------------


class TestAnalyzeTelemetry:
    def test_combined_analysis(self):
        df = _make_telemetry(throttle=50.0)
        # Inject one lift-and-coast zone
        df = _inject_lift_coast(df, 50, 100)
        # Inject one super-clipping zone with preceding acceleration ramp
        df.loc[280:349, "Speed"] = np.linspace(250, 330, 70)
        df.loc[280:349, "RPM"] = np.linspace(9000, 11500, 70)
        df.loc[280:349, "Throttle"] = 100.0
        df = _inject_super_clip(df, 350, 420, speed=330.0, rpm=11500.0)

        result = analyze_telemetry(df)

        assert result["lift_coast_count"] >= 1
        assert result["total_lift_coast_duration"] > 0
        assert isinstance(result["lift_and_coast_zones"], list)
        assert isinstance(result["super_clipping_zones"], list)

    def test_summary_stats_match_zones(self):
        df = _make_telemetry()
        df = _inject_lift_coast(df, 50, 100)
        df = _inject_lift_coast(df, 200, 250)

        result = analyze_telemetry(df)

        expected_count = len(result["lift_and_coast_zones"])
        expected_dur = round(sum(z["duration"] for z in result["lift_and_coast_zones"]), 3)
        assert result["lift_coast_count"] == expected_count
        assert result["total_lift_coast_duration"] == pytest.approx(expected_dur)

    def test_custom_thresholds_forwarded(self):
        df = _make_telemetry()
        # With default threshold (5.0) a zone at throttle=3 is L&C.
        # With threshold=1.0 it should be excluded.
        df = _inject_lift_coast(df, 100, 150)
        df.loc[100:149, "Throttle"] = 3.0  # above 1.0, below 5.0

        result_default = analyze_telemetry(df)
        result_strict = analyze_telemetry(df, throttle_threshold=1.0)

        assert result_default["lift_coast_count"] >= 1
        assert result_strict["lift_coast_count"] == 0
