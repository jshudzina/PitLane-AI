"""Get F1 season summary with races ranked by wildness.

Loads all races in a season, computes position change, volatility,
and pit stop statistics, then ranks races by a composite wildness score.

Usage:
    pitlane season-summary --year 2024
"""

import logging
from typing import TypedDict

import fastf1
import pandas as pd
from fastf1.core import Session
from fastf1.exceptions import DataNotLoadedError

from pitlane_agent.utils.constants import (
    AVG_CIRCUIT_LENGTH_KM,
    TRACK_STATUS_RED_FLAG,
    TRACK_STATUS_SAFETY_CAR,
    TRACK_STATUS_VSC_DEPLOYED,
)
from pitlane_agent.utils.fastf1_helpers import load_session, setup_fastf1_cache
from pitlane_agent.utils.race_stats import (
    RaceSummaryStats,
    compute_race_summary_stats,
    get_circuit_length_km,
)

logger = logging.getLogger(__name__)


class SeasonRaceSummary(TypedDict):
    """Summary statistics for a single race in a season."""

    round: int
    event_name: str
    country: str
    date: str | None
    session_type: str
    circuit_length_km: float | None
    race_distance_km: float
    podium: list[str]
    race_summary: RaceSummaryStats
    num_safety_cars: int
    num_virtual_safety_cars: int
    num_red_flags: int
    wildness_score: float


class SeasonAverages(TypedDict):
    """Per-lap normalized season averages across all races.

    Overtakes and position changes are expressed as per-lap rates
    so that sprints and full races contribute equally.
    """

    overtakes_per_lap: float
    position_changes_per_lap: float
    average_volatility: float
    mean_pit_stops: float


class SeasonSummary(TypedDict):
    """Complete season summary with races ranked by wildness."""

    year: int
    total_races: int
    races: list[SeasonRaceSummary]
    season_averages: SeasonAverages


def _count_track_interruptions(session: Session) -> tuple[int, int, int]:
    """Count safety cars, VSCs, and red flags from track status data.

    Returns:
        Tuple of (safety_cars, virtual_safety_cars, red_flags)
    """
    try:
        track_status = session.track_status
        safety_cars = len(track_status[track_status["Status"] == TRACK_STATUS_SAFETY_CAR])
        vscs = len(track_status[track_status["Status"] == TRACK_STATUS_VSC_DEPLOYED])
        red_flags = len(track_status[track_status["Status"] == TRACK_STATUS_RED_FLAG])
        return safety_cars, vscs, red_flags
    except DataNotLoadedError:
        return 0, 0, 0


def _compute_wildness_score(
    race_summary: RaceSummaryStats,
    num_safety_cars: int,
    num_red_flags: int,
    race_distance_km: float,
    max_overtakes_per_km: float,
    max_volatility: float,
) -> float:
    """Compute a composite wildness score for a race.

    The score is a weighted combination of normalized overtake density,
    volatility, and safety car/red flag bonuses.  Overtakes are expressed
    as a per-km rate so that shortened races and sprints are not penalised
    for covering fewer laps.

    Args:
        race_summary: Aggregate race statistics
        num_safety_cars: Number of safety car deployments
        num_red_flags: Number of red flags
        race_distance_km: Completed race distance (total_laps * circuit_length_km,
            or total_laps * AVG_CIRCUIT_LENGTH_KM when circuit length is unavailable)
        max_overtakes_per_km: Maximum overtakes-per-km across comparable races
        max_volatility: Maximum average volatility across comparable races

    Returns:
        Wildness score (higher = wilder race)
    """
    overtakes_per_km = race_summary["total_overtakes"] / race_distance_km if race_distance_km > 0 else 0
    norm_overtakes = overtakes_per_km / max_overtakes_per_km if max_overtakes_per_km > 0 else 0
    norm_volatility = race_summary["average_volatility"] / max_volatility if max_volatility > 0 else 0

    # Weighted formula: overtake density and volatility are primary signals,
    # safety cars and red flags add bonus
    return round(
        0.4 * norm_overtakes
        + 0.3 * norm_volatility
        + 0.2 * min(num_safety_cars / 3, 1.0)
        + 0.1 * min(num_red_flags, 1.0),
        3,
    )


def get_season_summary(year: int) -> SeasonSummary:
    """Load all races in a season and rank them by wildness.

    This loads each race session individually, which can be slow on first run.
    Subsequent calls benefit from FastF1's cache.

    Args:
        year: Championship year (e.g., 2024)

    Returns:
        Dictionary with races sorted by wildness score (descending)
        and season-wide averages.
    """
    setup_fastf1_cache()
    schedule = fastf1.get_event_schedule(year, include_testing=False)

    # Collect raw data for all sessions first (need max values for normalization)
    raw_races = []

    for _, event in schedule.iterrows():
        round_number = int(event["RoundNumber"])
        if round_number == 0:
            continue

        event_name = event["EventName"]
        country = event["Country"]
        event_date = event["EventDate"]
        date_str = event_date.isoformat()[:10] if pd.notna(event_date) else None
        event_format = event.get("EventFormat", "conventional")

        # Determine which sessions to load: always Race, plus Sprint for sprint weekends
        session_types = ["R"]
        if event_format in ("sprint", "sprint_shootout", "sprint_qualifying"):
            session_types.append("S")

        for session_type in session_types:
            logger.info("Loading %s %d: %s", session_type, round_number, event_name)

            try:
                session = load_session(year, event_name, session_type, messages=True)
            except Exception as e:
                logger.warning("Could not load %s %d: %s, skipping — %s", session_type, round_number, event_name, e)
                continue

            race_summary = compute_race_summary_stats(session)
            if race_summary is None:
                logger.warning("No laps data for %s %d: %s, skipping", session_type, round_number, event_name)
                continue

            safety_cars, vscs, red_flags = _count_track_interruptions(session)

            # Extract podium (top 3 finishers) from results
            podium: list[str] = []
            try:
                results = session.results.sort_values("Position")
                for _, driver in results.head(3).iterrows():
                    if pd.notna(driver["Position"]):
                        podium.append(driver["Abbreviation"])
            except Exception:
                pass

            raw_races.append(
                {
                    "round": round_number,
                    "event_name": event_name,
                    "country": country,
                    "date": date_str,
                    "session_type": session_type,
                    "circuit_length_km": get_circuit_length_km(session),
                    "podium": podium,
                    "race_summary": race_summary,
                    "num_safety_cars": safety_cars,
                    "num_virtual_safety_cars": vscs,
                    "num_red_flags": red_flags,
                }
            )

    if not raw_races:
        return {
            "year": year,
            "total_races": 0,
            "races": [],
            "season_averages": {
                "overtakes_per_lap": 0.0,
                "position_changes_per_lap": 0.0,
                "average_volatility": 0.0,
                "mean_pit_stops": 0.0,
            },
        }

    # Compute race distance for each entry.  When circuit_length_km is
    # available we use total_laps * circuit_length_km; otherwise we fall
    # back to total_laps * AVG_CIRCUIT_LENGTH_KM (~5 km).  Note:
    # circuit_length_km requires telemetry, which is not loaded here
    # (telemetry=False) to keep the command fast, so the average-length
    # fallback is the current default path.
    for race in raw_races:
        laps = race["race_summary"]["total_laps"]
        circuit_km = race["circuit_length_km"]
        race["race_distance_km"] = laps * circuit_km if circuit_km is not None else laps * AVG_CIRCUIT_LENGTH_KM

    # Compute normalization maxima across all sessions.  Since overtakes
    # are already expressed as a per-distance density, sprints and full
    # races are directly comparable without separate bucketing.
    max_overtakes_per_km = max(
        (r["race_summary"]["total_overtakes"] / r["race_distance_km"] if r["race_distance_km"] > 0 else 0)
        for r in raw_races
    )
    max_volatility = max(r["race_summary"]["average_volatility"] for r in raw_races)

    # Compute wildness scores and build final race list
    races: list[SeasonRaceSummary] = []
    for race in raw_races:
        wildness = _compute_wildness_score(
            race["race_summary"],
            race["num_safety_cars"],
            race["num_red_flags"],
            race["race_distance_km"],
            max_overtakes_per_km,
            max_volatility,
        )
        races.append(
            {
                **race,
                "wildness_score": wildness,
            }
        )

    # Sort by wildness score descending
    races.sort(key=lambda r: r["wildness_score"], reverse=True)

    # Compute season averages normalized by race distance so sprints
    # and full races contribute equally (per-lap rates).
    num_races = len(races)
    per_lap_overtakes = []
    per_lap_pos_changes = []
    for r in races:
        laps = r["race_summary"]["total_laps"]
        if laps > 0:
            per_lap_overtakes.append(r["race_summary"]["total_overtakes"] / laps)
            per_lap_pos_changes.append(r["race_summary"]["total_position_changes"] / laps)

    season_averages: SeasonAverages = {
        "overtakes_per_lap": round(sum(per_lap_overtakes) / len(per_lap_overtakes), 2) if per_lap_overtakes else 0.0,
        "position_changes_per_lap": round(sum(per_lap_pos_changes) / len(per_lap_pos_changes), 2)
        if per_lap_pos_changes
        else 0.0,
        "average_volatility": round(sum(r["race_summary"]["average_volatility"] for r in races) / num_races, 2),
        "mean_pit_stops": round(sum(r["race_summary"]["mean_pit_stops"] for r in races) / num_races, 2),
    }

    return {
        "year": year,
        "total_races": num_races,
        "races": races,
        "season_averages": season_averages,
    }
