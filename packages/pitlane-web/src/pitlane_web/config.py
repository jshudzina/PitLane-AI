"""Configuration constants for PitLane AI web application."""

import os

# ============================================================================
# Session Configuration
# ============================================================================

SESSION_COOKIE_NAME = "pitlane_session"
SESSION_MAX_AGE = int(os.getenv("PITLANE_SESSION_MAX_AGE", str(86400 * 7)))  # 7 days default

# Environment detection for smart defaults
PITLANE_ENV = os.getenv("PITLANE_ENV", "production")  # production | development | test

# Cookie secure flag: defaults to True unless in development mode
# Can be explicitly overridden with PITLANE_HTTPS_ENABLED
if os.getenv("PITLANE_HTTPS_ENABLED") is not None:
    # Explicit override takes precedence
    SESSION_COOKIE_SECURE = os.getenv("PITLANE_HTTPS_ENABLED").lower() == "true"
else:
    # Default based on environment: secure in production, insecure in development
    SESSION_COOKIE_SECURE = PITLANE_ENV != "development"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "lax"

# ============================================================================
# Agent Cache Configuration
# ============================================================================

AGENT_CACHE_MAX_SIZE = 100  # Maximum concurrent sessions

# ============================================================================
# Rate Limiting Configuration
# ============================================================================

RATE_LIMIT_ENABLED = os.getenv("PITLANE_RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_SESSION_CREATE = os.getenv("PITLANE_RATE_LIMIT_SESSION", "10/minute")
RATE_LIMIT_CHAT = os.getenv("PITLANE_RATE_LIMIT_CHAT", "30/minute")
RATE_LIMIT_CHART = os.getenv("PITLANE_RATE_LIMIT_CHART", "100/minute")
