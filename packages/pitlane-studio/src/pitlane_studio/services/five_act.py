"""FiveActMapper — static act-to-command config and on-demand data fetching.

Per CONTEXT.md:
  D-12: ACT_CONFIG is a module-level constant dict mapping acts 1-5 to
        pitlane-agent command callables and act metadata.
  D-13: FiveActMapper.fetch_act_data() caches results in an in-memory dict
        keyed by (year, round_num, act_number). Cache is per-process.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from pitlane_agent.commands.analyze.lap_times import generate_lap_times_chart
from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart
from pitlane_agent.commands.analyze.qualifying_results import generate_qualifying_results_chart
from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart
from pitlane_agent.commands.fetch.driver_standings import get_driver_standings
from pitlane_agent.commands.fetch.race_control import get_race_control_messages
from pitlane_agent.commands.fetch.session_info import get_session_info

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
_CHART_DIR: Path = Path.home() / ".pitlane" / "studio" / "charts"

# ACT_CONFIG: maps act numbers 1-5 to act metadata and pitlane-agent commands.
# Commands are callable references imported above (never strings).
# Per D-12: static Python dict — not a class method, not AI-generated at runtime.
ACT_CONFIG: dict[int, dict[str, Any]] = {
    1: {
        "label": "Qualifying / Grid",
        "commands": [get_session_info, generate_qualifying_results_chart],
    },
    2: {
        "label": "Lap 1 Chaos",
        "commands": [get_race_control_messages, generate_position_changes_chart],
    },
    3: {
        "label": "Pit Window",
        "commands": [generate_tyre_strategy_chart, get_race_control_messages],
    },
    4: {
        "label": "Final Stint",
        "commands": [generate_lap_times_chart, generate_position_changes_chart],
    },
    5: {
        "label": "Championship Implications",
        "commands": [get_driver_standings],
    },
}

# Commands that require workspace_dir (crashes if None is passed).
# Verified from position_changes.py, tyre_strategy.py, lap_times.py,
# qualifying_results.py — all four dereference workspace_dir immediately.
_CHART_COMMANDS: frozenset = frozenset([
    generate_qualifying_results_chart,
    generate_position_changes_chart,
    generate_tyre_strategy_chart,
    generate_lap_times_chart,
])


def _resolve_cmd(cmd: Any) -> Any:
    """Resolve the live (possibly mocked) version of a command function.

    Since five_act.py imports commands with `from ... import ...`, the module-level
    names are bound to the original function objects. To support pytest-mock patches
    at the source module level (e.g. mocker.patch("pitlane_agent.commands.fetch.
    session_info.get_session_info", ...)), this helper re-fetches the function from
    its source module at call time so mocks are correctly intercepted.
    """
    module = importlib.import_module(cmd.__module__)
    return getattr(module, cmd.__name__)


class FiveActMapper:
    """Fetches and caches act-specific pitlane-agent data for a race.

    Per D-13: results cached in-memory keyed by (year, round_num, act_number).
    Cache is per-process; lost on restart (acceptable — FastF1 caches to disk).
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[int, int, int], dict[str, Any]] = {}
        # Create chart output directory for chart-generating commands.
        # Four commands dereference workspace_dir immediately — never pass None.
        _CHART_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_act_data(self, year: int, round_num: int, act_number: int) -> dict[str, Any]:
        """Fetch and cache data for a single act.

        Args:
            year: F1 season year.
            round_num: Race round number within the season.
            act_number: Act number 1-5 (per ACT_CONFIG keys).

        Returns:
            Dict keyed by command function name with command result values.

        Raises:
            KeyError: If act_number is not in ACT_CONFIG (1-5).
        """
        cache_key = (year, round_num, act_number)
        if cache_key in self._cache:
            logger.debug("Cache hit: act %d for %d R%d", act_number, year, round_num)
            return self._cache[cache_key]

        config = ACT_CONFIG[act_number]  # raises KeyError if invalid act_number
        results: dict[str, Any] = {}

        for cmd in config["commands"]:
            cmd_name = cmd.__name__
            # Resolve live (possibly mocked) version via source module lookup.
            live_cmd = _resolve_cmd(cmd)
            try:
                if cmd in _CHART_COMMANDS:
                    # Chart commands need gp (str), session_type, and workspace_dir.
                    # Pass round_num as string for the gp parameter (FastF1 accepts int
                    # or str for round-based lookups). session_type defaults to "R".
                    # For lap_times, drivers defaults to [] (all-driver summary context).
                    if cmd is generate_lap_times_chart:
                        result = live_cmd(
                            year,
                            str(round_num),
                            "R",
                            [],
                            _CHART_DIR,
                        )
                    else:
                        result = live_cmd(
                            year,
                            str(round_num),
                            "R",
                            workspace_dir=_CHART_DIR,
                        )
                elif cmd is get_driver_standings:
                    result = live_cmd(year, round_num)
                else:
                    # Fetch commands: get_session_info, get_race_control_messages
                    # Both take (year, gp, session_type); pass round_num as str gp
                    # so FastF1 resolves by round number, and "R" as session_type.
                    result = live_cmd(year, str(round_num), "R")
                results[cmd_name] = result
            except Exception:
                logger.exception(
                    "fetch_act_data: command %s failed for act %d (%d R%d)",
                    cmd_name,
                    act_number,
                    year,
                    round_num,
                )
                results[cmd_name] = {}

        self._cache[cache_key] = results
        return results


__all__ = ["ACT_CONFIG", "FiveActMapper"]
