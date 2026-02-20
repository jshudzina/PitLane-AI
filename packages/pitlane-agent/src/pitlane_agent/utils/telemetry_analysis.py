"""Telemetry analysis utilities for detecting driving techniques.

Identifies lift-and-coast and super-clipping zones from a single lap's
telemetry DataFrame.  Pure analysis — no visualization.

Lift and Coast: driver releases throttle before the braking zone to save
fuel or manage tyres.  Signature is a gap between throttle-off and
brake-on while speed declines gradually from drag.

Super Clipping: the MGU-K stops deploying energy at the end of a straight
because the battery is depleted or the per-lap limit is reached.
Signature is a speed plateau or slight drop while throttle is pinned
at 100 % in a high gear.
"""

from typing import TypedDict

import pandas as pd

from pitlane_agent.utils.constants import (
    LIFT_COAST_BRAKE_THRESHOLD,
    LIFT_COAST_MIN_DURATION,
    LIFT_COAST_THROTTLE_THRESHOLD,
    SUPER_CLIP_ACCEL_LOOKBACK,
    SUPER_CLIP_MIN_DURATION,
    SUPER_CLIP_MIN_GEAR,
    SUPER_CLIP_MIN_SPEED_GAIN,
    SUPER_CLIP_RPM_STUTTER_THRESHOLD,
    SUPER_CLIP_SPEED_TOLERANCE,
    SUPER_CLIP_THROTTLE_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class LiftAndCoastZone(TypedDict):
    """A detected lift-and-coast zone."""

    start_distance: float  # metres
    end_distance: float  # metres
    duration: float  # seconds
    speed_loss: float  # km/h lost during the coast
    avg_rpm_drop: float  # RPM drop (start RPM − mean RPM)
    gear: int  # gear held during coast


class SuperClippingZone(TypedDict):
    """A detected super-clipping zone."""

    start_distance: float  # metres
    end_distance: float  # metres
    duration: float  # seconds
    throttle_percent: float  # average throttle (≈100 %)
    speed_plateau: float  # average speed during clipping (km/h)
    rpm_plateau: float  # average RPM during clipping
    gear: int  # gear (typically 7 or 8)


class TelemetryAnalysisResult(TypedDict):
    """Combined analysis result for a single lap."""

    lift_and_coast_zones: list[LiftAndCoastZone]
    super_clipping_zones: list[SuperClippingZone]
    total_lift_coast_duration: float  # seconds
    total_clipping_duration: float  # seconds
    lift_coast_count: int
    clipping_count: int


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_LIFT_COAST_COLUMNS = ["Distance", "Speed", "Throttle", "Brake", "RPM", "nGear", "Time"]
_SUPER_CLIP_COLUMNS = ["Distance", "Speed", "Throttle", "RPM", "nGear", "Time"]


def _validate_telemetry_columns(
    telemetry: pd.DataFrame,
    required: list[str],
) -> None:
    """Raise ``ValueError`` if *telemetry* is empty or missing columns."""
    if telemetry.empty:
        raise ValueError("Telemetry DataFrame is empty")
    missing = [c for c in required if c not in telemetry.columns]
    if missing:
        raise ValueError(f"Missing required telemetry channels: {missing}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_lift_and_coast_zones(
    telemetry: pd.DataFrame,
    *,
    min_duration: float = LIFT_COAST_MIN_DURATION,
    throttle_threshold: float = LIFT_COAST_THROTTLE_THRESHOLD,
    brake_threshold: int = LIFT_COAST_BRAKE_THRESHOLD,
) -> list[LiftAndCoastZone]:
    """Detect lift-and-coast zones in *telemetry*.

    A zone is a contiguous region where throttle is near-zero, the brake
    is off, and speed is declining (drag deceleration).

    Args:
        telemetry: DataFrame with columns Distance, Speed, Throttle,
            Brake, RPM, nGear, Time.
        min_duration: Minimum zone duration in seconds.
        throttle_threshold: Maximum throttle % considered "off".
        brake_threshold: Maximum brake value considered "off" (0 or 1).

    Returns:
        List of :class:`LiftAndCoastZone` dicts ordered by distance.
    """
    _validate_telemetry_columns(telemetry, _LIFT_COAST_COLUMNS)

    coasting = (telemetry["Throttle"] <= throttle_threshold) & (telemetry["Brake"] <= brake_threshold)
    groups = (coasting != coasting.shift()).cumsum()

    zones: list[LiftAndCoastZone] = []
    for _, group in telemetry[coasting].groupby(groups):
        if len(group) < 2:
            continue

        duration = (group["Time"].iloc[-1] - group["Time"].iloc[0]).total_seconds()
        if duration < min_duration:
            continue

        speed_start = float(group["Speed"].iloc[0])
        speed_end = float(group["Speed"].iloc[-1])
        if speed_end >= speed_start:
            continue

        zones.append(
            LiftAndCoastZone(
                start_distance=float(group["Distance"].iloc[0]),
                end_distance=float(group["Distance"].iloc[-1]),
                duration=round(duration, 3),
                speed_loss=round(speed_start - speed_end, 1),
                avg_rpm_drop=round(float(group["RPM"].iloc[0]) - float(group["RPM"].mean()), 0),
                gear=int(group["nGear"].mode().iloc[0]),
            )
        )

    return zones


def detect_super_clipping_zones(
    telemetry: pd.DataFrame,
    *,
    min_duration: float = SUPER_CLIP_MIN_DURATION,
    throttle_threshold: float = SUPER_CLIP_THROTTLE_THRESHOLD,
    speed_tolerance: float = SUPER_CLIP_SPEED_TOLERANCE,
    rpm_stutter_threshold: float = SUPER_CLIP_RPM_STUTTER_THRESHOLD,
    min_gear: int = SUPER_CLIP_MIN_GEAR,
    accel_lookback: int = SUPER_CLIP_ACCEL_LOOKBACK,
    min_speed_gain: float = SUPER_CLIP_MIN_SPEED_GAIN,
) -> list[SuperClippingZone]:
    """Detect super-clipping zones in *telemetry*.

    A zone is a contiguous region where throttle is pinned at 100 %,
    speed plateaus (low rolling standard deviation), and RPM stops
    climbing — all in a high gear.  The zone must be preceded by a
    rising-speed phase (acceleration) to distinguish genuine MGU-K
    depletion from steady-state cruising.

    Args:
        telemetry: DataFrame with columns Distance, Speed, Throttle,
            RPM, nGear, Time.
        min_duration: Minimum zone duration in seconds.
        throttle_threshold: Minimum throttle % for "full throttle".
        speed_tolerance: Maximum rolling speed std-dev (km/h) to
            consider a plateau.
        rpm_stutter_threshold: Maximum per-sample RPM increase;
            lower or negative values indicate the engine is no longer
            accelerating.
        min_gear: Minimum gear for a valid clipping zone.
        accel_lookback: Number of samples before the zone start to
            check for preceding acceleration.
        min_speed_gain: Minimum speed increase (km/h) in the lookback
            window required to confirm a preceding acceleration phase.

    Returns:
        List of :class:`SuperClippingZone` dicts ordered by distance.
    """
    _validate_telemetry_columns(telemetry, _SUPER_CLIP_COLUMNS)

    window = min(5, len(telemetry))
    speed_std = telemetry["Speed"].rolling(window, min_periods=1).std().fillna(0.0)
    rpm_diff = telemetry["RPM"].diff().fillna(0.0)

    clipping = (
        (telemetry["Throttle"] >= throttle_threshold)
        & (speed_std <= speed_tolerance)
        & (rpm_diff <= rpm_stutter_threshold)
    )
    groups = (clipping != clipping.shift()).cumsum()

    speeds = telemetry["Speed"].values

    zones: list[SuperClippingZone] = []
    for _, group in telemetry[clipping].groupby(groups):
        if len(group) < 2:
            continue

        gear = int(group["nGear"].mode().iloc[0])
        if gear < min_gear:
            continue

        duration = (group["Time"].iloc[-1] - group["Time"].iloc[0]).total_seconds()
        if duration < min_duration:
            continue

        # Require preceding acceleration: speed must have risen by at
        # least *min_speed_gain* in the *accel_lookback* samples before
        # the zone starts.  Without this, constant-speed straights and
        # steady-state cruising produce false positives.
        zone_start_idx = group.index[0]
        lookback_start = max(0, zone_start_idx - accel_lookback)
        speed_gain = speeds[zone_start_idx] - speeds[lookback_start]
        if speed_gain < min_speed_gain:
            continue

        zones.append(
            SuperClippingZone(
                start_distance=float(group["Distance"].iloc[0]),
                end_distance=float(group["Distance"].iloc[-1]),
                duration=round(duration, 3),
                throttle_percent=round(float(group["Throttle"].mean()), 1),
                speed_plateau=round(float(group["Speed"].mean()), 1),
                rpm_plateau=round(float(group["RPM"].mean()), 0),
                gear=gear,
            )
        )

    return zones


def analyze_telemetry(
    telemetry: pd.DataFrame,
    **kwargs: float | int,
) -> TelemetryAnalysisResult:
    """Run all telemetry detectors and return an aggregated result.

    Keyword arguments are forwarded to :func:`detect_lift_and_coast_zones`
    and :func:`detect_super_clipping_zones` where the parameter names
    match.

    Raises:
        ValueError: If *telemetry* is empty or missing required columns.
    """
    import inspect

    lc_params = inspect.signature(detect_lift_and_coast_zones).parameters
    sc_params = inspect.signature(detect_super_clipping_zones).parameters

    lc_kwargs = {k: v for k, v in kwargs.items() if k in lc_params}
    sc_kwargs = {k: v for k, v in kwargs.items() if k in sc_params}

    lc_zones = detect_lift_and_coast_zones(telemetry, **lc_kwargs)
    sc_zones = detect_super_clipping_zones(telemetry, **sc_kwargs)

    lc_total = round(sum(z["duration"] for z in lc_zones), 3)
    sc_total = round(sum(z["duration"] for z in sc_zones), 3)

    return TelemetryAnalysisResult(
        lift_and_coast_zones=lc_zones,
        super_clipping_zones=sc_zones,
        total_lift_coast_duration=lc_total,
        total_clipping_duration=sc_total,
        lift_coast_count=len(lc_zones),
        clipping_count=len(sc_zones),
    )
