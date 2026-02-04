"""Temporal context management for F1 Agent.

This module provides real-time awareness of the F1 calendar at multiple granularities:
- Season level: Current year, phase (pre/in/post/off-season)
- Race weekend level: Current/next/last race events
- Session level: Live/recent/upcoming sessions

Public API:
    get_temporal_context() - Get current F1 temporal context
    format_for_system_prompt() - Format context for agent system prompt
"""

from pitlane_agent.temporal.context import (
    F1Season,
    RaceWeekendContext,
    RaceWeekendPhase,
    SessionContext,
    TemporalContext,
    TemporalContextManager,
    get_temporal_context,
)
from pitlane_agent.temporal.formatter import format_for_system_prompt

__all__ = [
    "F1Season",
    "RaceWeekendContext",
    "RaceWeekendPhase",
    "SessionContext",
    "TemporalContext",
    "TemporalContextManager",
    "get_temporal_context",
    "format_for_system_prompt",
]
