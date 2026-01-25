"""PitLane AI CLI - Unified command interface for F1 data analysis tools.

Usage:
    pitlane --help
    pitlane session-info --year 2024 --gp Monaco --session R
    pitlane lap-times --year 2024 --gp Monaco --session Q --drivers VER --drivers HAM
    pitlane tyre-strategy --year 2024 --gp Monaco --session R
    pitlane event-schedule --year 2024
    pitlane driver-info --driver-code VER
"""

import click

from pitlane_agent.scripts.driver_info import cli as driver_info_cli
from pitlane_agent.scripts.event_schedule import cli as event_schedule_cli
from pitlane_agent.scripts.lap_times import cli as lap_times_cli
from pitlane_agent.scripts.session_info import cli as session_info_cli
from pitlane_agent.scripts.tyre_strategy import cli as tyre_strategy_cli


@click.group()
def pitlane():
    """PitLane AI - F1 data analysis tools powered by FastF1 and Claude."""
    pass


# Register subcommands
pitlane.add_command(driver_info_cli, name="driver-info")
pitlane.add_command(event_schedule_cli, name="event-schedule")
pitlane.add_command(lap_times_cli, name="lap-times")
pitlane.add_command(session_info_cli, name="session-info")
pitlane.add_command(tyre_strategy_cli, name="tyre-strategy")


if __name__ == "__main__":
    pitlane()
