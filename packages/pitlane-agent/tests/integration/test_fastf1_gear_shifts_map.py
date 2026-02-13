"""Integration tests for gear shifts map generation with real FastF1 data.

These tests make real API calls to FastF1 to load session and telemetry data.
"""

from pathlib import Path

import pytest
from pitlane_agent.commands.analyze.gear_shifts_map import generate_gear_shifts_map_chart


@pytest.mark.integration
@pytest.mark.slow
class TestGearShiftsMapIntegration:
    """Integration tests for gear shifts map with real FastF1."""

    @pytest.mark.timeout(300)
    def test_gear_shifts_map_generation_monaco_single_driver(self, fastf1_cache_dir, stable_test_data, tmp_path):
        """Test gear shifts map generation for Monaco with a single driver."""
        result = generate_gear_shifts_map_chart(
            year=stable_test_data["year"],
            gp=stable_test_data["test_gp"],
            session_type="Q",
            drivers=["VER"],
            workspace_dir=tmp_path,
        )

        # Verify result structure
        assert result["year"] == stable_test_data["year"]
        assert result["event_name"] is not None
        assert result["session_name"] == "Qualifying"
        assert result["circuit_name"] is not None

        # Verify drivers analyzed
        assert "drivers_analyzed" in result
        assert len(result["drivers_analyzed"]) == 1
        assert result["drivers_analyzed"][0] == "VER"

        # Verify gear statistics
        assert "gear_statistics" in result
        assert len(result["gear_statistics"]) == 1

        driver_stats = result["gear_statistics"][0]
        assert driver_stats["driver"] == "VER"
        assert "gear_distribution" in driver_stats
        assert "most_used_gear" in driver_stats
        assert "highest_gear" in driver_stats
        assert "total_gear_changes" in driver_stats
        assert "lap_number" in driver_stats
        assert "lap_time" in driver_stats

        # Verify gear distribution structure
        assert isinstance(driver_stats["gear_distribution"], dict)
        assert len(driver_stats["gear_distribution"]) > 0

        for gear, stats in driver_stats["gear_distribution"].items():
            assert isinstance(gear, int)
            assert "count" in stats
            assert "percentage" in stats
            assert stats["count"] > 0
            assert 0 <= stats["percentage"] <= 100

        # Verify gear values are reasonable
        assert 1 <= driver_stats["most_used_gear"] <= 8
        assert 1 <= driver_stats["highest_gear"] <= 8
        assert driver_stats["total_gear_changes"] > 0

        # Verify chart file exists and is valid PNG
        chart_path = Path(result["chart_path"])
        assert chart_path.exists()
        assert chart_path.suffix == ".png"
        assert chart_path.stat().st_size > 0

        # Verify chart path follows naming convention
        assert "gear_shifts_map" in chart_path.name
        assert "VER" in chart_path.name

    @pytest.mark.timeout(300)
    def test_gear_shifts_map_generation_bahrain_race(self, fastf1_cache_dir, recent_race_data, tmp_path):
        """Test gear shifts map generation for Bahrain race session."""
        result = generate_gear_shifts_map_chart(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            drivers=["VER"],
            workspace_dir=tmp_path,
        )

        # Verify basic structure
        assert result["year"] == recent_race_data["year"]
        assert result["session_name"] == "Race"
        assert len(result["drivers_analyzed"]) == 1
        assert len(result["gear_statistics"]) == 1

        # Verify chart exists
        chart_path = Path(result["chart_path"])
        assert chart_path.exists()
        assert chart_path.stat().st_size > 0

    @pytest.mark.timeout(300)
    def test_gear_shifts_map_different_driver(self, fastf1_cache_dir, stable_test_data, tmp_path):
        """Test gear shifts map with a different driver."""
        result = generate_gear_shifts_map_chart(
            year=stable_test_data["year"],
            gp=stable_test_data["test_gp"],
            session_type="Q",
            drivers=["NOR"],
            workspace_dir=tmp_path,
        )

        # Verify driver-specific results
        assert result["drivers_analyzed"][0] == "NOR"
        assert result["gear_statistics"][0]["driver"] == "NOR"

        # Verify chart file references correct driver
        chart_path = Path(result["chart_path"])
        assert "NOR" in chart_path.name
        assert chart_path.exists()

    @pytest.mark.timeout(120)
    def test_telemetry_data_structure(self, fastf1_cache_dir, stable_test_data):
        """Test that FastF1 telemetry has expected data structure for gear shifts."""
        import fastf1

        session = fastf1.get_session(stable_test_data["year"], stable_test_data["test_gp"], "Q")
        session.load(telemetry=True)

        # Get fastest lap for a driver
        driver_laps = session.laps.pick_drivers("VER")
        assert not driver_laps.empty, "Driver should have laps"

        fastest_lap = driver_laps.pick_fastest()

        # Verify position data structure
        pos_data = fastest_lap.get_pos_data()
        assert not pos_data.empty, "Position data should not be empty"
        assert "X" in pos_data.columns
        assert "Y" in pos_data.columns

        # Verify car data structure
        car_data = fastest_lap.get_car_data()
        assert not car_data.empty, "Car data should not be empty"
        assert "nGear" in car_data.columns, "Car data should have gear information"
        assert "Speed" in car_data.columns

        # Verify gear values are valid
        assert car_data["nGear"].min() >= 1
        assert car_data["nGear"].max() <= 8

        # Verify circuit info has corners
        circuit_info = session.get_circuit_info()
        assert hasattr(circuit_info, "corners")
        assert len(circuit_info.corners) > 0

    @pytest.mark.timeout(300)
    def test_gear_shifts_validation_error_multiple_drivers(self, fastf1_cache_dir, stable_test_data, tmp_path):
        """Test that multiple drivers raises validation error."""
        with pytest.raises(ValueError, match="maximum 1 driver"):
            generate_gear_shifts_map_chart(
                year=stable_test_data["year"],
                gp=stable_test_data["test_gp"],
                session_type="Q",
                drivers=["VER", "NOR"],
                workspace_dir=tmp_path,
            )
