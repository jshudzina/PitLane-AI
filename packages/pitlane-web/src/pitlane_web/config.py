"""Configuration constants for PitLane AI web application."""

import os

# ============================================================================
# Session Configuration
# ============================================================================

SESSION_COOKIE_NAME = "pitlane_session"
SESSION_MAX_AGE = int(os.getenv("PITLANE_SESSION_MAX_AGE", str(86400 * 7)))  # 7 days default
SESSION_COOKIE_SECURE = os.getenv("PITLANE_HTTPS_ENABLED", "false").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "lax"

# ============================================================================
# Agent Cache Configuration
# ============================================================================

AGENT_CACHE_MAX_SIZE = 100  # Maximum concurrent sessions
