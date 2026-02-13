"""Integration tests for track map generation with real FastF1 data.

These tests make real API calls to FastF1 to load session and circuit data.
"""

from pathlib import Path

import pytest
from pitlane_agent.commands.analyze.track_map import generate_track_map_chart


@pytest.mark.integration
@pytest.mark.slow
class TestTrackMapIntegration:
    """Integration tests for track map with real FastF1."""

    @pytest.mark.timeout(300)
    def test_track_map_generation_monaco(self, fastf1_cache_dir, stable_test_data, tmp_path):
        """Test track map generation for Monaco — a circuit with many corners."""
        result = generate_track_map_chart(
            year=stable_test_data["year"],
            gp=stable_test_data["test_gp"],
            session_type="Q",
            workspace_dir=tmp_path,
        )

        # Verify result structure
        assert result["year"] == stable_test_data["year"]
        assert result["event_name"] is not None
        assert result["session_name"] == "Qualifying"
        assert result["num_corners"] > 0
        assert len(result["corner_details"]) == result["num_corners"]

        # Verify chart file exists and is valid PNG
        chart_path = Path(result["chart_path"])
        assert chart_path.exists()
        assert chart_path.suffix == ".png"
        assert chart_path.stat().st_size > 0

        # Verify corner details structure
        for corner in result["corner_details"]:
            assert "number" in corner
            assert "letter" in corner
            assert isinstance(corner["number"], int)

    @pytest.mark.timeout(300)
    def test_track_map_generation_bahrain(self, fastf1_cache_dir, recent_race_data, tmp_path):
        """Test track map generation for Bahrain — a different circuit layout."""
        result = generate_track_map_chart(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            workspace_dir=tmp_path,
        )

        assert result["year"] == recent_race_data["year"]
        assert result["num_corners"] > 0

        chart_path = Path(result["chart_path"])
        assert chart_path.exists()
        assert chart_path.stat().st_size > 0

    @pytest.mark.timeout(120)
    def test_circuit_info_data_structure(self, fastf1_cache_dir, stable_test_data):
        """Test that FastF1 circuit info has expected data structure."""
        import fastf1

        session = fastf1.get_session(stable_test_data["year"], stable_test_data["test_gp"], "Q")
        session.load()

        circuit_info = session.get_circuit_info()

        # Verify corners DataFrame has expected columns
        expected_columns = {"X", "Y", "Number", "Letter", "Angle", "Distance"}
        assert expected_columns.issubset(set(circuit_info.corners.columns))

        # Verify rotation is a numeric value
        assert isinstance(circuit_info.rotation, (int, float))

        # Verify corners have valid data
        assert len(circuit_info.corners) > 0
        assert circuit_info.corners["Number"].dtype in ["int64", "float64"]
