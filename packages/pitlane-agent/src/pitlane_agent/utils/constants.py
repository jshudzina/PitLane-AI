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
