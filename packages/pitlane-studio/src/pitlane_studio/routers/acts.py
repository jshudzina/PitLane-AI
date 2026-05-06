"""Acts router — /acts/* endpoints for the five-act race structure."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from pitlane_studio.services.five_act import ACT_CONFIG, FiveActMapper

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/acts/{year}/{round_num}")
async def get_acts(year: int, round_num: int) -> dict:
    """Return all 5 acts with labels and fetched data for a given race."""
    mapper = FiveActMapper()
    acts: dict[int, dict] = {}
    for act_number in range(1, 6):
        try:
            data = mapper.fetch_act_data(year, round_num, act_number)
        except Exception:
            logger.exception("Failed to fetch act %d data for %d/%d", act_number, year, round_num)
            data = {}
        acts[act_number] = {
            "label": ACT_CONFIG[act_number]["label"],
            "data": data,
        }
    return {"acts": acts}
