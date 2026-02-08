"""Constants for FastF1 data processing.

This module contains constant values used across the PitLane Agent,
particularly for interpreting FastF1 data structures.
"""

# Track Status Codes
# Reference: https://docs.fastf1.dev/core.html#fastf1.core.SessionResults.track_status
TRACK_STATUS_ALL_CLEAR = "1"
TRACK_STATUS_YELLOW = "2"
TRACK_STATUS_GREEN = "3"
TRACK_STATUS_SAFETY_CAR = "4"
TRACK_STATUS_RED_FLAG = "5"
TRACK_STATUS_VSC_DEPLOYED = "6"
TRACK_STATUS_VSC_ENDING = "7"

# Matplotlib Dark Theme Configuration
# Used by visualization commands for consistent F1-style dark theme
MATPLOTLIB_DARK_THEME = {
    "figure.facecolor": "#1e1e1e",
    "axes.facecolor": "#2d2d2d",
    "axes.edgecolor": "#555555",
    "axes.labelcolor": "#ffffff",
    "text.color": "#ffffff",
    "xtick.color": "#ffffff",
    "ytick.color": "#ffffff",
    "grid.color": "#444444",
    "grid.alpha": 0.3,
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
}

# Tyre Compound Colors (F1 2024 style)
COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFF200",
    "HARD": "#EBEBEB",
    "INTERMEDIATE": "#43B02A",
    "WET": "#0067AD",
    "UNKNOWN": "#888888",
}

# Figure Dimensions and Styling
FIGURE_WIDTH = 14
FIGURE_HEIGHT = 8
DEFAULT_DPI = 150
LINE_WIDTH = 2
MARKER_SIZE = 3
PIT_MARKER_SIZE = 100
ALPHA_VALUE = 0.8
GRID_ALPHA = 0.3

# F1 Historical Constraints
MIN_F1_YEAR = 1950
FINAL_ROUND = "last"

# Championship Points
# Maximum points per race weekend (2024 and earlier): 25 (win) + 1 (fastest lap)
MAX_RACE_POINTS_PER_WEEKEND_WITH_FASTEST_LAP = 26
# Maximum points per race weekend (2025 onwards): 25 (win) - fastest lap point removed
MAX_RACE_POINTS_PER_WEEKEND_NO_FASTEST_LAP = 25
# Maximum points per sprint race: 8 (win)
MAX_SPRINT_POINTS = 8
# Year when fastest lap point was removed
FASTEST_LAP_POINT_REMOVED_YEAR = 2025

# Championship Possibility Colors
CHAMPIONSHIP_VIABLE_COLOR = "#43B02A"  # Green for competitors who can still win
CHAMPIONSHIP_ELIMINATED_COLOR = "#888888"  # Gray for eliminated competitors

# Validation Constants
MAX_DRIVER_CODE_LENGTH = 3
MIN_SPEED_TRACE_DRIVERS = 2
MAX_SPEED_TRACE_DRIVERS = 5

# Race Control Message Categories
# Reference: https://docs.fastf1.dev/api_reference/legacy/f1_api.html#fastf1.api.race_control_messages
MESSAGE_CATEGORY_FLAG = "Flag"
MESSAGE_CATEGORY_OTHER = "Other"
MESSAGE_CATEGORY_DRS = "Drs"
MESSAGE_CATEGORY_SAFETY_CAR = "SafetyCar"

# Race Control Flag Types
FLAG_RED = "RED"
FLAG_YELLOW = "YELLOW"
FLAG_DOUBLE_YELLOW = "DOUBLE YELLOW"
FLAG_GREEN = "GREEN"
FLAG_BLUE = "BLUE"
FLAG_CLEAR = "CLEAR"
FLAG_CHEQUERED = "CHEQUERED"
