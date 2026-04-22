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
import json
import logging
import re
from pathlib import Path
from typing import Any

import click
import duckdb
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import ResultMessage
from pitlane_agent.utils.stats_db import get_data_dir, init_data_dir

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Claude model for classification — Haiku is sufficient for a binary verdict
# backed by web search evidence.
_DEFAULT_MODEL = "haiku"
_MAX_RETRIES = 2  # up to 3 total attempts per entry

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
            "description": ("One-sentence summary of the evidence found (or lack thereof)."),
        },
    },
    "required": ["verdict", "evidence"],
    "additionalProperties": False,
}


def _fetch_mechanical_dnfs(
    data_dir: Path,
    year: int,
    round_numbers: tuple[int, ...] | None = None,
) -> list[dict]:
    """Return mechanical-DNF rows from race_entries for the given filters."""
    race_path = data_dir / f"race_entries_{year}.parquet"
    stats_path = data_dir / "session_stats.parquet"
    if not race_path.exists():
        return []
    has_stats = stats_path.exists()
    if has_stats:
        select = (
            "SELECT r.year, r.round, r.session_type, r.driver_id, r.abbreviation, "
            "r.team, r.laps_completed, r.status, s.event_name "
            f"FROM read_parquet('{race_path}') r "
            f"LEFT JOIN read_parquet('{stats_path}') s "
            "ON r.year = s.year AND r.round = s.round AND r.session_type = s.session_type "
            "WHERE r.dnf_category = 'mechanical'"
        )
        round_col = "r.round"
        order_by = "ORDER BY r.round, r.driver_id"
    else:
        select = (
            "SELECT year, round, session_type, driver_id, abbreviation, "
            "team, laps_completed, status, NULL AS event_name "
            f"FROM read_parquet('{race_path}') "
            "WHERE dnf_category = 'mechanical'"
        )
        round_col = "round"
        order_by = "ORDER BY round, driver_id"
    params: list[object] = []
    if round_numbers:
        placeholders = ", ".join("?" * len(round_numbers))
        select += f" AND {round_col} IN ({placeholders})"
        params.extend(round_numbers)
    sql = f"{select} {order_by}"
    con = duckdb.connect()
    try:
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()
    cols = ["year", "round", "session_type", "driver_id", "abbreviation", "team", "laps_completed", "status", "event_name"]
    return [dict(zip(cols, row, strict=True)) for row in rows]


def _build_user_prompt(entry: dict) -> str:
    """Build the per-entry prompt for the LLM."""
    driver = entry["abbreviation"] or entry["driver_id"]
    session_label = "Sprint" if entry["session_type"] == "S" else "Race"
    event_name = entry.get("event_name") or f"Formula 1 Season, Round {entry['round']}"
    return (
        f"Driver: {driver} ({entry['team']})\n"
        f"Event: {entry['year']} {event_name}, {session_label}\n"
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
    crash_signals = (
        "crash",
        "accident",
        "collision",
        "hit the wall",
        "hit the barrier",
        "contact with",
        "spun",
        "spun out",
        "rolled",
        "flipped",
        "off track",
        "into the gravel",
        "into the tyre barrier",
        "beached",
    )
    if any(kw in lower for kw in crash_signals):
        return {"verdict": "crash", "evidence": text[:200]}

    mechanical_signals = (
        "engine",
        "power unit",
        "gearbox",
        "hydraulic",
        "brake failure",
        "electrical",
        "overheating",
        "oil leak",
        "water leak",
        "suspension failure",
        "mechanical failure",
        "reliability",
        "technical issue",
        "disqualified",
        "excluded",
        "underweight",
        "skid block",
        "plank",
    )
    if any(kw in lower for kw in mechanical_signals):
        return {"verdict": "mechanical", "evidence": text[:200]}

    return None


def _update_dnf_category(
    data_dir: Path,
    updates: list[dict],
) -> int:
    """Batch-update dnf_category to 'crash' for confirmed entries.

    Returns the number of rows updated.
    """
    if not updates:
        return 0
    from collections import defaultdict

    by_year: dict[int, list[dict]] = defaultdict(list)
    for u in updates:
        by_year[u["year"]].append(u)

    for year, year_updates in by_year.items():
        parquet_path = data_dir / f"race_entries_{year}.parquet"
        if not parquet_path.exists():
            continue
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE t AS SELECT * FROM read_parquet('{parquet_path}')")
            for u in year_updates:
                con.execute(
                    "UPDATE t SET dnf_category = 'crash' "
                    "WHERE round = ? AND session_type = ? AND driver_id = ?",
                    [u["round"], u["session_type"], u["driver_id"]],
                )
            con.execute(f"COPY t TO '{parquet_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        finally:
            con.close()

    return len(updates)


async def _review_async(
    data_dir: Path,
    entries: list[dict],
    dry_run: bool,
    model: str,
) -> None:
    """Async core: iterate entries, classify via agent, apply updates."""
    reclassified: list[dict] = []
    failed: list[dict] = []

    for i, entry in enumerate(entries, 1):
        driver = entry["abbreviation"] or entry["driver_id"]
        label = f"[{i}/{len(entries)}] Rd {entry['round']} {driver}"
        click.echo(f"  {label}: querying agent...", err=True)

        result: dict | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                result = await _classify_with_agent(entry, model=model)
            except Exception as exc:
                if attempt < _MAX_RETRIES:
                    click.echo(f"  {label}: error, retrying ({attempt + 1}/{_MAX_RETRIES})...", err=True)
                    await asyncio.sleep(2)
                else:
                    click.echo(f"  {label}: agent error — {exc}", err=True)
                continue

            if result is not None:
                break

            if attempt < _MAX_RETRIES:
                click.echo(f"  {label}: no output, retrying ({attempt + 1}/{_MAX_RETRIES})...", err=True)
                await asyncio.sleep(2)

        if result is None:
            click.echo(f"  {label}: no structured output after {_MAX_RETRIES + 1} attempts", err=True)
            failed.append(entry)
            continue

        verdict = result.get("verdict", "mechanical")
        evidence = result.get("evidence", "")
        click.echo(f"  {label}: {verdict} — {evidence}", err=True)

        if verdict == "crash":
            reclassified.append(entry)

        # Respect rate limits
        await asyncio.sleep(1)

    click.echo(
        f"\nResults: {len(reclassified)} crash(es) found, "
        f"{len(entries) - len(reclassified) - len(failed)} confirmed mechanical, "
        f"{len(failed)} error(s)",
        err=True,
    )

    if failed:
        click.echo("\nFailed entries:", err=True)
        for e in failed:
            d = e["abbreviation"] or e["driver_id"]
            click.echo(f"  Year {e['year']} Rd {e['round']} {d}", err=True)

    if not reclassified:
        click.echo("No updates needed.", err=True)
        return

    if dry_run:
        click.echo("\n[DRY RUN] Would reclassify:", err=True)
        for e in reclassified:
            d = e["abbreviation"] or e["driver_id"]
            click.echo(f"  Year {e['year']} Rd {e['round']} {d}: mechanical → crash", err=True)
        return

    updated = _update_dnf_category(data_dir, reclassified)
    click.echo(f"\nUpdated {updated} record(s) in {data_dir}", err=True)


@click.command()
@click.option("--year", required=True, type=int, help="F1 season year (>= 2023)")
@click.option(
    "--round",
    "round_numbers",
    default=None,
    type=int,
    multiple=True,
    help="Round number(s) to review (repeatable, default: all rounds)",
)
@click.option(
    "--data-dir",
    "data_dir_str",
    default=None,
    type=str,
    help="Path to data directory containing Parquet files (default: bundled data/)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print proposed changes without writing to Parquet files",
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
    round_numbers: tuple[int, ...],
    data_dir_str: str | None,
    dry_run: bool,
    model_override: str | None,
) -> None:
    """Review mechanical DNFs for misclassified crashes via LLM web search."""
    model = model_override or _DEFAULT_MODEL

    if year < 2023:
        click.echo("This script targets years >= 2023 where Ergast collapses DNF reasons.", err=True)
        raise SystemExit(1)

    data_dir = Path(data_dir_str) if data_dir_str else get_data_dir()
    init_data_dir(data_dir)
    click.echo(f"Data dir: {data_dir}", err=True)

    entries = _fetch_mechanical_dnfs(data_dir, year, round_numbers or None)
    rounds_label = f" rounds {sorted(round_numbers)}" if round_numbers else ""
    click.echo(
        f"Found {len(entries)} mechanical DNF(s) for {year}{rounds_label}",
        err=True,
    )
    if not entries:
        return

    asyncio.run(_review_async(data_dir, entries, dry_run, model))


if __name__ == "__main__":
    review_mechanical_dnfs()
