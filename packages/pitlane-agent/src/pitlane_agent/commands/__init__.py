"""Commands for F1 data fetching, analysis, and workspace management.

This package contains all command modules organized by category:
- fetch: Data fetching commands
- analyze: Visualization and analysis commands
- workspace: Workspace management commands
"""

# Import all command functions for convenience
from pitlane_agent.commands.analyze import (
    generate_lap_times_chart,
    generate_lap_times_distribution_chart,
    generate_position_changes_chart,
    generate_speed_trace_chart,
    generate_tyre_strategy_chart,
)
from pitlane_agent.commands.fetch import (
    get_constructor_standings,
    get_driver_info,
    get_driver_standings,
    get_event_schedule,
    get_session_info,
)
from pitlane_agent.commands.workspace import (
    clean_workspaces,
    create_conversation,
    create_workspace,
    generate_session_id,
    get_active_conversation,
    get_workspace_info,
    get_workspace_path,
    list_workspaces,
    load_conversations,
    remove_workspace,
    set_active_conversation,
    update_conversation,
    update_workspace_metadata,
    workspace_exists,
)

__all__ = [
    # Fetch commands
    "get_session_info",
    "get_driver_info",
    "get_event_schedule",
    "get_driver_standings",
    "get_constructor_standings",
    # Analyze commands
    "generate_lap_times_chart",
    "generate_lap_times_distribution_chart",
    "generate_tyre_strategy_chart",
    "generate_speed_trace_chart",
    "generate_position_changes_chart",
    # Workspace commands
    "create_workspace",
    "list_workspaces",
    "get_workspace_path",
    "get_workspace_info",
    "workspace_exists",
    "remove_workspace",
    "clean_workspaces",
    "generate_session_id",
    "update_workspace_metadata",
    "create_conversation",
    "update_conversation",
    "get_active_conversation",
    "set_active_conversation",
    "load_conversations",
]
