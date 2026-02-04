"""Pytest fixtures for FastF1 integration tests.

These fixtures support integration tests that make real API calls to FastF1 and Ergast.
"""

import socket

import fastf1
import pytest


@pytest.fixture(scope="session")
def fastf1_cache_dir(tmp_path_factory):
    """Provide isolated cache directory for integration tests.

    Uses session scope to share cache across all integration tests,
    reducing API calls and test time.
    """
    cache_dir = tmp_path_factory.mktemp("fastf1_cache")
    fastf1.Cache.enable_cache(str(cache_dir))
    return cache_dir


@pytest.fixture(scope="session")
def stable_test_data():
    """Provide stable historical F1 data that won't change.

    Using 2025 season data as it's the most recent complete season.
    Avoids current season data which may be incomplete.
    """
    return {
        "year": 2025,
        "test_gp": "Monaco",  # Classic race with good data
        "test_drivers": ["VER", "NOR", "LEC"],  # Top drivers from 2025
        "total_rounds": 25,  # 2025 season rounds
    }


@pytest.fixture(scope="session")
def recent_race_data():
    """Provide recent but stable race data for testing.

    2025 Bahrain GP - first race of 2025, complete data.
    """
    return {
        "year": 2025,
        "gp": "Bahrain",
        "round": 1,
    }


@pytest.fixture
def skip_if_no_internet(request):
    """Skip test if no internet connection available."""
    try:
        socket.create_connection(("ergast.com", 80), timeout=3)
    except OSError:
        pytest.skip("No internet connection available")
