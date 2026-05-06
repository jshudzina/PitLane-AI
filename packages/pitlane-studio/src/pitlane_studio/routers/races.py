"""Races router — /races/* endpoints for race and season selection."""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, HTTPException

from pitlane_agent.commands.fetch.season_summary import get_season_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/races/years")
async def get_years() -> dict:
    """Return list of available season years (2023 to current)."""
    current_year = datetime.datetime.now().year
    years = list(range(2023, current_year + 1))
    return {"years": years}


@router.get("/races/{year}/rounds")
async def get_rounds(year: int) -> dict:
    """Return list of rounds for a given year."""
    try:
        summary = get_season_summary(year)
        rounds = summary.get("rounds", [])
        return {"year": year, "rounds": rounds}
    except Exception as exc:
        logger.exception("Failed to fetch rounds for year %d", year)
        raise HTTPException(status_code=502, detail=f"Could not fetch rounds: {exc}") from exc
