"""PipelineOrchestrator — plan-then-write pipeline for F1 journalism.

Per CONTEXT.md:
  D-02: Full outline context included in every per-beat prompt.
  PTW-01: generate_outline() makes a single async SDK call,
          persists to outline_beats, transitions article to outline_generated.
  PTW-03: stream_beat() is an async generator yielding SSE-formatted strings.
  PTW-04: placeholder_markers detected by regex; must appear verbatim in prose.

Beat streaming model: claude-sonnet-4-5-20250929
Outline generation model: claude-haiku-4-5
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncIterator

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions
from claude_agent_sdk import query as sdk_query
from pydantic import BaseModel

from pitlane_studio.services.five_act import ACT_CONFIG, FiveActMapper
from pitlane_studio.store.article_store import ArticleStore
from pitlane_studio.store.beat_store import BeatStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class OutlineBeat(BaseModel):
    """One beat in the structured article outline."""

    beat_number: int
    beat_title: str
    data_anchors: str
    act_number: int | None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _detect_placeholders(prose: str) -> list[dict]:
    """Scan prose for [JOURNALIST: quote/context/causal] patterns.

    Returns a list of dicts with 'type' (str) and 'offset' (int) keys.
    Pattern matches: [JOURNALIST: quote], [JOURNALIST: context], [JOURNALIST: causal]
    """
    pattern = r'\[JOURNALIST:\s*(quote|context|causal)\]'
    return [
        {"type": match.group(1), "offset": match.start()}
        for match in re.finditer(pattern, prose)
    ]


def _build_outline_prompt(
    year: int,
    round_num: int,
    angle_name: str,
    angle_rationale: str,
    act_data: dict[int, dict],
) -> str:
    """Build the non-streaming prompt for outline generation.

    Includes the five act labels from ACT_CONFIG and key data per act.
    Returns a JSON array of 5 beat objects.
    """
    act_labels = "\n".join(
        f"Act {act_num}: {ACT_CONFIG[act_num]['label']}"
        for act_num in range(1, 6)
    )

    act_summaries_parts = []
    for act_num in range(1, 6):
        data = act_data.get(act_num, {})
        # Use first available data value as a one-sentence context
        summary_text = ""
        for val in data.values():
            if val and isinstance(val, (str, dict, list)):
                text = str(val)
                # Trim long data to a reasonable summary length
                summary_text = text[:300] if len(text) > 300 else text
                break
        act_summaries_parts.append(
            f"Act {act_num} ({ACT_CONFIG[act_num]['label']}): {summary_text or 'No data available'}"
        )
    act_summaries = "\n".join(act_summaries_parts)

    return f"""You are an F1 journalism assistant generating a structured article outline.

Story angle: {angle_name}
Angle rationale: {angle_rationale}
Race: {year} Round {round_num}

Five-act race structure:
{act_labels}

Key race data per act:
{act_summaries}

Generate a JSON array of exactly 5 outline beats — one per act. Each beat must map to its act.

For each beat include:
- beat_number: integer 1-5
- beat_title: a concise, compelling headline for this beat (string)
- data_anchors: one sentence of data context for this beat. MUST reference at least one of: [JOURNALIST: quote], [JOURNALIST: context], or [JOURNALIST: causal] as a placeholder for journalist-supplied content
- act_number: integer 1-5 matching the act

Rules:
- Across the 5 beats combined, include at least one [JOURNALIST: quote], one [JOURNALIST: context], and one [JOURNALIST: causal] placeholder reference in the data_anchors fields
- Placeholders must appear verbatim: [JOURNALIST: quote], [JOURNALIST: context], [JOURNALIST: causal]
- Return ONLY a valid JSON array — no explanation, no markdown, no preamble

Example format:
[
  {{"beat_number": 1, "beat_title": "Grid Positions Set the Stage", "data_anchors": "Hamilton qualified P3 [JOURNALIST: context]", "act_number": 1}},
  ...
]"""


def _build_beat_prompt(
    beat_title: str,
    data_anchors: str,
    full_outline: list[OutlineBeat],
    act_data: dict,
) -> str:
    """Build the per-beat streaming prompt.

    Includes the full outline context (D-02) and the current beat's details.
    Prose target: 150-250 words. Must include all three placeholder types verbatim.
    """
    outline_context = "\n".join(
        f"  Beat {b.beat_number}: {b.beat_title} — {b.data_anchors}"
        for b in full_outline
    )

    # Summarize act data for context
    act_summary = ""
    for val in act_data.values():
        if val and isinstance(val, (str, dict, list)):
            text = str(val)
            act_summary = text[:400] if len(text) > 400 else text
            break
    if not act_summary:
        act_summary = "No act data available."

    return f"""You are an F1 journalism assistant writing a specific beat for an article.

Full article outline (for narrative consistency):
{outline_context}

Current beat to write:
  Title: {beat_title}
  Data anchors: {data_anchors}

Act context data:
{act_summary}

Write the prose for THIS beat only. Requirements:
- 150–250 words
- MUST include EXACTLY ONE of each placeholder verbatim in the prose:
    [JOURNALIST: quote]    — where a direct quote from a driver/team should go
    [JOURNALIST: context]  — where background context the journalist knows should go
    [JOURNALIST: causal]   — where the journalist's causal reasoning should go
- Placeholders must appear word-for-word, including brackets and colon
- Do NOT fill in the placeholders — leave them exactly as shown
- Write in a journalistic tone appropriate for an F1 article

Write ONLY the prose — no title, no explanation, no JSON."""


# ---------------------------------------------------------------------------
# PipelineOrchestrator
# ---------------------------------------------------------------------------


class PipelineOrchestrator:
    """Core pipeline service: outline generation and per-beat SSE streaming.

    Routers call these methods. This class owns:
    - generate_outline(): sync Anthropic call → persist to BeatStore → transition article
    - stream_beat(): async generator yielding SSE strings with token events
    """

    async def generate_outline(
        self,
        article_id: str,
        year: int,
        round_num: int,
        angle_id: str,
        angle_name: str,
        angle_rationale: str,
    ) -> list[OutlineBeat]:
        """Generate a structured 5-beat outline for the article.

        Makes a single async SDK call (claude-haiku-4-5), persists to
        outline_beats table, and transitions the article status to
        'outline_generated'.

        Args:
            article_id: UUID of the article to generate outline for.
            year: F1 season year.
            round_num: Race round number.
            angle_id: ID of the selected story angle.
            angle_name: Human-readable angle name.
            angle_rationale: Brief rationale for why this angle is interesting.

        Returns:
            List of 5 OutlineBeat objects.

        Raises:
            json.JSONDecodeError: If LLM response is not valid JSON.
            Exception: Re-raised after logging for any other error.
        """
        try:
            # 1. Fetch act data for all 5 acts
            mapper = FiveActMapper()
            act_data: dict[int, dict] = {
                act_num: mapper.fetch_act_data(year, round_num, act_num)
                for act_num in range(1, 6)
            }

            # 2. Build prompt
            prompt = _build_outline_prompt(year, round_num, angle_name, angle_rationale, act_data)

            # 3. SDK call — collect all text blocks from AssistantMessages
            options = ClaudeAgentOptions(model="claude-haiku-4-5", allowed_tools=[])
            collected: list[str] = []
            async for msg in sdk_query(prompt=prompt, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if hasattr(block, "text"):
                            collected.append(block.text)
            raw_text = "".join(collected)

            # 4. Parse JSON and validate
            try:
                raw_beats = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                logger.error(
                    "generate_outline: LLM response was not valid JSON for article %s: %s",
                    article_id,
                    raw_text[:200],
                )
                raise json.JSONDecodeError(
                    "Outline LLM response was not valid JSON",
                    exc.doc,
                    exc.pos,
                ) from exc

            outline_beats = [OutlineBeat(**b) for b in raw_beats]

            # 5. Persist to BeatStore
            BeatStore().save_outline_beats(article_id, [b.model_dump() for b in outline_beats])

            # 6. Transition article status
            ArticleStore().transition_status(article_id, "outline_generated")

            # 7. Return
            return outline_beats

        except json.JSONDecodeError:
            raise
        except Exception:
            logger.exception(
                "generate_outline: unexpected error for article %s",
                article_id,
            )
            raise

    async def stream_beat(
        self,
        article_id: str,
        beat_number: int,
    ) -> AsyncIterator[str]:  # yields SSE-formatted strings
        """Stream prose for a single beat as Server-Sent Events.

        Yields SSE strings in order:
          1. event: beat_start — signals start with beat metadata
          2. event: token    — one per streamed text chunk from the LLM
          3. event: beat_done — final event with full prose and placeholder_markers
          4. event: error    — only on failure (beat not found, or LLM error)

        The approval gate is enforced in the route handler, not here.

        Args:
            article_id: UUID of the article.
            beat_number: Which beat to generate prose for (1-5).

        Yields:
            SSE-formatted strings (each ending with double newline).
        """
        # 1. Load outline beats from BeatStore
        beat_store = BeatStore()
        outline_records = beat_store.get_outline_beats(article_id)
        outline_beats = [
            OutlineBeat(
                beat_number=r.beat_number,
                beat_title=r.beat_title,
                data_anchors=r.data_anchors or "",
                act_number=r.act_number,
            )
            for r in outline_records
        ]

        # 2. Find the current beat
        beat = next((b for b in outline_beats if b.beat_number == beat_number), None)
        if beat is None:
            yield (
                f"event: error\n"
                f"data: {json.dumps({'beat_number': beat_number, 'message': 'Beat not found', 'retryable': False})}\n\n"
            )
            return

        # 3. Load act data for this beat
        mapper = FiveActMapper()
        article = ArticleStore().get(article_id)
        act_data = mapper.fetch_act_data(
            article.race_year,
            article.race_round,
            beat.act_number or beat_number,
        )

        # 4. Emit beat_start
        yield (
            f"event: beat_start\n"
            f"data: {json.dumps({'beat_number': beat_number, 'beat_title': beat.beat_title, 'total_beats': len(outline_beats)})}\n\n"
        )

        # 5. Build prompt
        prompt = _build_beat_prompt(beat.beat_title, beat.data_anchors, outline_beats, act_data)

        # 6. Collect full prose via SDK, emit as single token event, then beat_done
        full_prose_parts: list[str] = []
        try:
            options = ClaudeAgentOptions(model="claude-sonnet-4-5-20250929", allowed_tools=[])
            async for msg in sdk_query(prompt=prompt, options=options):
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            full_prose_parts.append(block.text)
            prose_text = "".join(full_prose_parts)
            yield (
                f"event: token\n"
                f"data: {json.dumps({'beat_number': beat_number, 'token': prose_text})}\n\n"
            )

            # 7. Detect placeholders
            prose = prose_text
            placeholder_markers = _detect_placeholders(prose)

            # 8. Persist beat
            BeatStore().save_beat(article_id, beat_number, beat.beat_title, prose, placeholder_markers)

            # 9. Emit beat_done
            yield (
                f"event: beat_done\n"
                f"data: {json.dumps({'beat_number': beat_number, 'prose': prose, 'placeholder_markers': placeholder_markers})}\n\n"
            )

        except Exception as e:
            logger.exception(
                "stream_beat: error streaming beat %d for article %s",
                beat_number,
                article_id,
            )
            yield (
                f"event: error\n"
                f"data: {json.dumps({'beat_number': beat_number, 'message': str(e), 'retryable': True})}\n\n"
            )


__all__ = ["OutlineBeat", "PipelineOrchestrator"]
