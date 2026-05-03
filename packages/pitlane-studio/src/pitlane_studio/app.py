"""FastAPI application for PitLane Studio."""

import logging
import os

from fastapi import FastAPI

_log_level_str = os.getenv("PITLANE_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("pitlane_studio").setLevel(_log_level)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PitLane Studio",
    description="F1 journalism co-authoring interface",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
