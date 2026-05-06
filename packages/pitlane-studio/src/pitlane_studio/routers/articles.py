"""Articles router — /articles/* endpoints for the plan-then-write pipeline."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pitlane_studio.services.angles import AngleService, DataNotReadyError
from pitlane_studio.services.pipeline import PipelineOrchestrator
from pitlane_studio.store.article_store import ArticleStore
from pitlane_studio.store.beat_store import BeatStore

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Request body schemas ---


class CreateArticleRequest(BaseModel):
    race_year: int
    race_round: int
    angle_id: str | None = None


class GenerateOutlineRequest(BaseModel):
    angle_id: str
    angle_name: str
    angle_rationale: str


class PatchOutlineRequest(BaseModel):
    beats: list[dict]  # list of {beat_number, beat_title, data_anchors, act_number, position}


# --- Routes ---


@router.post("/articles")
async def create_article(body: CreateArticleRequest) -> dict:
    article_id = str(uuid.uuid4())
    store = ArticleStore()
    article = store.create(article_id, race_year=body.race_year, race_round=body.race_round, angle_id=body.angle_id)
    return {"article_id": article.id, "status": article.status}


@router.get("/articles/{article_id}/angles")
async def get_angles(article_id: str) -> dict:
    store = ArticleStore()
    try:
        article = store.get(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        service = AngleService()
        angles = service.get_angles(article.race_year, article.race_round)
        return {"angles": [a.model_dump() for a in angles]}
    except DataNotReadyError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc


@router.post("/articles/{article_id}/outline")
async def generate_outline(article_id: str, body: GenerateOutlineRequest) -> dict:
    store = ArticleStore()
    try:
        article = store.get(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        orchestrator = PipelineOrchestrator()
        outline_beats = orchestrator.generate_outline(
            article_id=article_id,
            year=article.race_year,
            round_num=article.race_round,
            angle_id=body.angle_id,
            angle_name=body.angle_name,
            angle_rationale=body.angle_rationale,
        )
        return {"article_id": article_id, "outline_beats": [b.model_dump() for b in outline_beats]}
    except Exception as exc:
        logger.exception("Outline generation failed for article %s", article_id)
        raise HTTPException(status_code=500, detail=f"Outline generation failed: {exc}") from exc


@router.patch("/articles/{article_id}/outline")
async def patch_outline(article_id: str, body: PatchOutlineRequest) -> dict:
    beat_store = BeatStore()
    beat_store.save_outline_beats(article_id, body.beats)
    return {"article_id": article_id, "saved_beats": len(body.beats)}


@router.post("/articles/{article_id}/approve")
async def approve_outline(article_id: str) -> dict:
    store = ArticleStore()
    try:
        article = store.transition_status(article_id, "outline_approved")
        return {"article_id": article_id, "status": article.status}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/articles/{article_id}/beats/{beat_number}/stream")
async def stream_beat(article_id: str, beat_number: int):
    # Gate check BEFORE StreamingResponse — HTTPException must be raised here (not inside generator)
    store = ArticleStore()
    try:
        article = store.get(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if article.status != "outline_approved":
        raise HTTPException(status_code=409, detail="Outline not approved — cannot stream beat prose")

    orchestrator = PipelineOrchestrator()

    async def _generator():
        async for chunk in orchestrator.stream_beat(article_id, beat_number):
            yield chunk

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
