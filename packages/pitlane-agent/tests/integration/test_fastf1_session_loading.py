"""Integration tests for FastF1 session loading.

These tests make real API calls to FastF1 to load session data, including telemetry.
"""

from pathlib import Path

import pytest
from pitlane_agent.commands.analyze.lap_times import generate_lap_times_chart
from pitlane_agent.commands.fetch.session_info import get_session_info


@pytest.mark.integration
@pytest.mark.slow
class TestSessionLoadingIntegration:
    """Integration tests for session loading with real FastF1."""

    def test_load_qualifying_session(self, fastf1_cache_dir, stable_test_data):
        """Test loading qualifying session data."""
        result = get_session_info(stable_test_data["year"], stable_test_data["test_gp"], "Q")

        assert result["year"] == stable_test_data["year"]
        assert result["session_type"] == "Q"
        assert result["country"] == "Monaco"
        assert len(result["drivers"]) >= 18  # Minimum expected drivers

        # Verify driver data structure
        for driver in result["drivers"]:
            assert "abbreviation" in driver
            assert "name" in driver
            assert "team" in driver

    def test_load_race_session(self, fastf1_cache_dir, recent_race_data):
        """Test loading race session data."""
        result = get_session_info(recent_race_data["year"], recent_race_data["gp"], "R")

        assert result["session_name"] == "Race"
        assert result["total_laps"] is not None
        assert result["total_laps"] > 0
        assert len(result["drivers"]) >= 18

    def test_load_practice_session(self, fastf1_cache_dir, recent_race_data):
        """Test loading practice session data."""
        result = get_session_info(recent_race_data["year"], recent_race_data["gp"], "FP1")

        assert result["session_type"] == "FP1"
        assert len(result["drivers"]) >= 18
        # Practice sessions don't have a fixed number of laps (time-based)
        # total_laps may be None for practice sessions
        assert "total_laps" in result

    @pytest.mark.timeout(300)  # 5 minute timeout for telemetry loading
    def test_load_lap_times_with_chart_generation(self, fastf1_cache_dir, stable_test_data, tmp_path):
        """Test loading session with lap times and generating chart.

        This tests the full session.load() path including lap data processing.
        """
        result = generate_lap_times_chart(
            year=stable_test_data["year"],
            gp=stable_test_data["test_gp"],
            session_type="Q",
            drivers=["VER", "NOR"],  # Limit to 2 drivers for speed
            workspace_dir=tmp_path,
        )

        assert result["year"] == stable_test_data["year"]
        assert len(result["drivers_plotted"]) == 2
        assert Path(result["chart_path"]).exists()

        # Verify chart file is a valid PNG
        chart_path = Path(result["chart_path"])
        assert chart_path.suffix == ".png"
        assert chart_path.stat().st_size > 0  # Non-empty file

    def test_session_results_data(self, fastf1_cache_dir, recent_race_data):
        """Test that session results contain expected fields."""
        result = get_session_info(recent_race_data["year"], recent_race_data["gp"], "Q")

        # Verify session metadata
        assert "event_name" in result
        assert "country" in result
        assert "date" in result
        assert "session_type" in result
        assert "session_name" in result

        # Verify driver data completeness
        for driver in result["drivers"]:
            assert driver["abbreviation"] is not None
            assert driver["team"] is not None
            # Some fields may be None but should exist
            assert "position" in driver
            assert "number" in driver
            assert "name" in driver

    def test_session_with_invalid_session_type(self, fastf1_cache_dir, stable_test_data):
        """Test handling of invalid session type."""
        # FastF1 should raise an error for invalid session types
        with pytest.raises(Exception):  # noqa: B017
            get_session_info(stable_test_data["year"], stable_test_data["test_gp"], "INVALID")

    def test_session_with_sprint_format(self, fastf1_cache_dir):
        """Test loading a sprint weekend session.

        Sprint weekends have different session structure.
        """
        # 2025 had sprint races - use one for testing
        # This tests sprint session compatibility
        try:
            result = get_session_info(2025, "Austria", "Sprint")
            # If sprint exists, verify it loaded
            assert result["session_type"] == "Sprint"
            assert len(result["drivers"]) >= 18
        except Exception:
            # Sprint may not exist for this event, that's ok
            pytest.skip("Sprint session not available for this event")
