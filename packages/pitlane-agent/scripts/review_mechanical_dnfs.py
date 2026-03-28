#!/usr/bin/env python3
"""Review mechanical DNFs (2023+) for misclassified crashes using LLM web search.

Single-car wall crashes (e.g. Stroll Saudi 2024) produce no collision-keyword
message in race control and are classified as "mechanical" by the RCM-based
pipeline.  This script queries DuckDB for those entries and uses Claude with
web search to check FIA / Formula 1 sources for crash evidence, updating the
record to "crash" when the agent confirms the incident.

Usage:
    python scripts/review_mechanical_dnfs.py --year 2024
    python scripts/review_mechanical_dnfs.py --year 2024 --round 5
    python scripts/review_mechanical_dnfs.py --year 2024 --dry-run
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import click
import duckdb
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import ResultMessage
from pitlane_agent.utils.elo_db import init_elo_tables
from pitlane_agent.utils.stats_db import get_db_path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Claude model for classification — Haiku is sufficient for a binary verdict
# backed by web search evidence.
_DEFAULT_MODEL = "haiku"

_SYSTEM_PROMPT = """\
You are an F1 incident analyst.  You will be given the name of a driver and \
a specific F1 race.  Your job is to determine whether that driver's retirement \
from the race was caused by a crash / accident / contact with a wall or barrier, \
OR by a mechanical / reliability failure.

Search fia.com and formula1.com for race reports, stewards' decisions, and \
incident summaries for this specific race.  Focus on evidence of the driver \
hitting a wall, barrier, or another car.

After searching, respond with your verdict and evidence.\
"""

_VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["crash", "mechanical"],
            "description": (
                '"crash" if the driver hit a wall, barrier, or another car; '
                '"mechanical" if it was a reliability / power unit / component failure.'
            ),
        },
        "evidence": {
            "type": "string",
            "description": (
                "One-sentence summary of the evidence found (or lack thereof)."
            ),
        },
    },
    "required": ["verdict", "evidence"],
    "additionalProperties": False,
}


def _fetch_mechanical_dnfs(
    db_path: Path,
    year: int,
    round_number: int | None = None,
) -> list[dict]:
    """Return mechanical-DNF rows from race_entries for the given filters."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        sql = (
            "SELECT year, round, session_type, driver_id, abbreviation, "
            "team, laps_completed, status "
            "FROM race_entries "
            "WHERE year = ? AND dnf_category = 'mechanical'"
        )
        params: list[object] = [year]
        if round_number is not None:
            sql += " AND round = ?"
            params.append(round_number)
        sql += " ORDER BY round, driver_id"
        rows = con.execute(sql, params).fetchall()
        cols = [
            "year", "round", "session_type", "driver_id", "abbreviation",
            "team", "laps_completed", "status",
        ]
        return [dict(zip(cols, row, strict=True)) for row in rows]
    finally:
        con.close()


def _build_user_prompt(entry: dict) -> str:
    """Build the per-entry prompt for the LLM."""
    driver = entry["abbreviation"] or entry["driver_id"]
    session_label = "Sprint" if entry["session_type"] == "S" else "Race"
    return (
        f"Driver: {driver} ({entry['team']})\n"
        f"Event: {entry['year']} Formula 1 Season, Round {entry['round']}, {session_label}\n"
        f"Status reported by timing system: \"{entry['status']}\"\n"
        f"Laps completed before retirement: {entry['laps_completed']}\n\n"
        f"Did {driver} crash (hit a wall, barrier, or another car) during this "
        f"session, or was this a genuine mechanical / reliability retirement?"
    )


async def _classify_with_agent(
    entry: dict,
    model: str = _DEFAULT_MODEL,
) -> dict | None:
    """Call Claude with web search + structured output for one entry.

    Uses claude-agent-sdk query() with output_format to get a JSON verdict.
    Returns the structured output dict on success, or None if the agent
    did not produce structured output.
    """
    options = ClaudeAgentOptions(
        allowed_tools=["WebSearch"],
        permission_mode="bypassPermissions",
        system_prompt=_SYSTEM_PROMPT,
        output_format={"type": "json_schema", "schema": _VERDICT_SCHEMA},
        max_turns=6,
        model=model,
    )

    result: dict | None = None
    last_result_text: str | None = None
    async for message in query(prompt=_build_user_prompt(entry), options=options):
        if isinstance(message, ResultMessage):
            if message.structured_output is not None:
                output = message.structured_output
                if isinstance(output, dict) and "verdict" in output:
                    result = output
            # Fallback: parse the text result if structured_output was not populated
            if result is None and message.result:
                last_result_text = message.result

    if result is None and last_result_text:
        result = _parse_verdict_from_text(last_result_text)

    return result


def _parse_verdict_from_text(text: str) -> dict | None:
    """Best-effort extraction of verdict from plain-text agent response.

    Tries JSON parsing first, then falls back to keyword scanning.
    """
    import json
    import re

    # Try to find a JSON object in the text
    for match in re.finditer(r"\{[^{}]+\}", text):
        try:
            obj = json.loads(match.group())
            if "verdict" in obj:
                return obj
        except json.JSONDecodeError:
            continue

    # Keyword fallback: look for unambiguous crash/mechanical language
    lower = text.lower()
    crash_signals = ("crash", "accident", "collision", "hit the wall", "hit the barrier", "contact with")
    if any(kw in lower for kw in crash_signals):
        return {"verdict": "crash", "evidence": text[:200]}

    return None


def _update_dnf_category(
    db_path: Path,
    updates: list[dict],
) -> int:
    """Batch-update dnf_category to 'crash' for confirmed entries.

    Returns the number of rows updated.
    """
    if not updates:
        return 0
    con = duckdb.connect(str(db_path))
    try:
        for u in updates:
            con.execute(
                "UPDATE race_entries SET dnf_category = 'crash' "
                "WHERE year = ? AND round = ? AND session_type = ? AND driver_id = ?",
                [u["year"], u["round"], u["session_type"], u["driver_id"]],
            )
        return len(updates)
    finally:
        con.close()


async def _review_async(
    db_path: Path,
    entries: list[dict],
    dry_run: bool,
    model: str,
) -> None:
    """Async core: iterate entries, classify via agent, apply updates."""
    reclassified: list[dict] = []
    errors = 0

    for i, entry in enumerate(entries, 1):
        driver = entry["abbreviation"] or entry["driver_id"]
        label = f"[{i}/{len(entries)}] Rd {entry['round']} {driver}"
        click.echo(f"  {label}: querying agent...", err=True)

        try:
            result = await _classify_with_agent(entry, model=model)
        except Exception as exc:
            click.echo(f"  {label}: agent error — {exc}", err=True)
            errors += 1
            continue

        if result is None:
            click.echo(f"  {label}: no structured output in response", err=True)
            errors += 1
            continue

        verdict = result.get("verdict", "mechanical")
        evidence = result.get("evidence", "")
        click.echo(f"  {label}: {verdict} — {evidence}", err=True)

        if verdict == "crash":
            reclassified.append(entry)

        # Respect rate limits
        time.sleep(1)

    click.echo(f"\nResults: {len(reclassified)} crash(es) found, "
               f"{len(entries) - len(reclassified) - errors} confirmed mechanical, "
               f"{errors} error(s)", err=True)

    if not reclassified:
        click.echo("No updates needed.", err=True)
        return

    if dry_run:
        click.echo("\n[DRY RUN] Would reclassify:", err=True)
        for e in reclassified:
            d = e["abbreviation"] or e["driver_id"]
            click.echo(f"  Year {e['year']} Rd {e['round']} {d}: mechanical → crash", err=True)
        return

    updated = _update_dnf_category(db_path, reclassified)
    click.echo(f"\nUpdated {updated} record(s) in {db_path}", err=True)


@click.command()
@click.option("--year", required=True, type=int, help="F1 season year (>= 2023)")
@click.option(
    "--round",
    "round_number",
    default=None,
    type=int,
    help="Specific round number (default: all rounds)",
)
@click.option(
    "--db-path",
    "db_path_str",
    default=None,
    type=str,
    help="Path to DuckDB file (default: bundled pitlane.duckdb)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print proposed changes without writing to DB",
)
@click.option(
    "--model",
    "model_override",
    default=None,
    type=str,
    help=f"Override LLM model (default: {_DEFAULT_MODEL})",
)
def review_mechanical_dnfs(
    year: int,
    round_number: int | None,
    db_path_str: str | None,
    dry_run: bool,
    model_override: str | None,
) -> None:
    """Review mechanical DNFs for misclassified crashes via LLM web search."""
    model = model_override or _DEFAULT_MODEL

    if year < 2023:
        click.echo("This script targets years >= 2023 where Ergast collapses DNF reasons.", err=True)
        raise SystemExit(1)

    db_path = Path(db_path_str) if db_path_str else get_db_path()
    init_elo_tables(db_path)
    click.echo(f"DB: {db_path}", err=True)

    entries = _fetch_mechanical_dnfs(db_path, year, round_number)
    click.echo(f"Found {len(entries)} mechanical DNF(s) for {year}" +
               (f" round {round_number}" if round_number else ""), err=True)
    if not entries:
        return

    asyncio.run(_review_async(db_path, entries, dry_run, model))


if __name__ == "__main__":
    review_mechanical_dnfs()
