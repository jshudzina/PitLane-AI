"""Pytest configuration and shared fixtures for pitlane-agent tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Provide a temporary workspace directory.

    The workspace will have data/ and charts/ subdirectories created by functions.
    """
    return tmp_path


@pytest.fixture
def mock_fastf1_session():
    """Mock FastF1 session object."""
    session = MagicMock()
    session.event = {"EventName": "Monaco Grand Prix", "Country": "Monaco"}
    session.name = "Qualifying"
    session.date = MagicMock()
    session.date.date.return_value = "2024-05-25"
    session.total_laps = 78
    return session


@pytest.fixture
def mock_fastf1_cache(monkeypatch):
    """Mock FastF1 cache to prevent actual caching."""
    mock_cache = MagicMock()
    monkeypatch.setattr("fastf1.Cache.enable_cache", mock_cache)
    return mock_cache


@pytest.fixture
def sample_driver_data():
    """Sample driver data for testing."""
    return {
        "drivers": ["VER", "HAM", "LEC"],
        "year": 2024,
        "gp": "Monaco",
        "session": "Q",
    }


@pytest.fixture
def enable_tracing(monkeypatch):
    """Enable tracing for specific tests."""
    from pitlane_agent import tracing

    monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
    # Reset global state
    tracing._tracing_enabled = None
    tracing._tracer = None
    tracing._provider_initialized = False
    yield
    # Cleanup after test
    tracing._tracing_enabled = None
    tracing._tracer = None
    tracing._provider_initialized = False


@pytest.fixture
def disable_tracing(monkeypatch):
    """Ensure tracing is disabled for specific tests."""
    from pitlane_agent import tracing

    monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)
    tracing._tracing_enabled = None
    tracing._tracer = None
    tracing._provider_initialized = False
    yield
