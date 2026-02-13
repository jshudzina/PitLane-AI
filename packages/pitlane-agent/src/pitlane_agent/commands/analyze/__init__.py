"""Analyze commands for generating F1 data visualizations.

This module provides commands for generating F1 visualizations including
lap times, tyre strategies, speed traces, position changes, and championship possibilities.
"""

from pitlane_agent.commands.analyze.championship_possibilities import generate_championship_possibilities_chart
from pitlane_agent.commands.analyze.gear_shifts_map import generate_gear_shifts_map_chart
from pitlane_agent.commands.analyze.lap_times import generate_lap_times_chart
from pitlane_agent.commands.analyze.lap_times_distribution import generate_lap_times_distribution_chart
from pitlane_agent.commands.analyze.position_changes import generate_position_changes_chart
from pitlane_agent.commands.analyze.speed_trace import generate_speed_trace_chart
from pitlane_agent.commands.analyze.track_map import generate_track_map_chart
from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart

__all__ = [
    "generate_championship_possibilities_chart",
    "generate_gear_shifts_map_chart",
    "generate_lap_times_chart",
    "generate_lap_times_distribution_chart",
    "generate_tyre_strategy_chart",
    "generate_speed_trace_chart",
    "generate_position_changes_chart",
    "generate_track_map_chart",
]
