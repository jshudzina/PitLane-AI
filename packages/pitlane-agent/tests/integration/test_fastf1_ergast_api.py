"""Integration tests for FastF1 Ergast API.

These tests make real API calls to the Ergast API via FastF1 to verify driver info integration.
"""

import pytest
from pitlane_agent.commands.fetch.driver_info import get_driver_info


@pytest.mark.integration
class TestErgastAPIIntegration:
    """Integration tests for Ergast API via FastF1."""

    def test_get_driver_by_code(self, fastf1_cache_dir):
        """Test fetching driver info by code."""
        result = get_driver_info(driver_code="VER")

        assert result["total_drivers"] >= 1
        driver = result["drivers"][0]
        assert driver["driver_code"] == "VER"
        assert "Verstappen" in driver["family_name"]
        assert driver["nationality"] is not None
        assert driver["full_name"] is not None

    def test_get_driver_by_code_case_insensitive(self, fastf1_cache_dir):
        """Test fetching driver info with different case."""
        result = get_driver_info(driver_code="ver")  # lowercase

        assert result["total_drivers"] >= 1
        driver = result["drivers"][0]
        assert driver["driver_code"] == "VER"
        assert "Verstappen" in driver["family_name"]

    def test_get_drivers_by_season(self, fastf1_cache_dir, stable_test_data):
        """Test fetching all drivers from a season."""
        result = get_driver_info(season=stable_test_data["year"])

        assert result["total_drivers"] >= 20  # F1 grid size
        assert result["filters"]["season"] == stable_test_data["year"]

        # Verify all drivers have required fields
        for driver in result["drivers"]:
            assert driver["driver_id"] is not None
            assert driver["full_name"] is not None
            assert driver["driver_code"] is not None

    def test_get_drivers_pagination(self, fastf1_cache_dir, stable_test_data):
        """Test driver info pagination."""
        # Get first page
        page1 = get_driver_info(season=stable_test_data["year"], limit=10, offset=0)
        # Get second page
        page2 = get_driver_info(season=stable_test_data["year"], limit=10, offset=10)

        assert len(page1["drivers"]) == 10
        assert len(page2["drivers"]) >= 10

        # Verify different drivers on different pages
        page1_codes = {d["driver_code"] for d in page1["drivers"]}
        page2_codes = {d["driver_code"] for d in page2["drivers"]}
        assert page1_codes != page2_codes

    def test_driver_data_structure(self, fastf1_cache_dir):
        """Test that driver data has expected structure."""
        result = get_driver_info(driver_code="NOR")

        assert result["total_drivers"] >= 1
        driver = result["drivers"][0]

        # Verify all expected fields exist
        expected_fields = [
            "driver_id",
            "driver_code",
            "full_name",
            "given_name",
            "family_name",
            "nationality",
            "date_of_birth",
        ]
        for field in expected_fields:
            assert field in driver, f"Missing field: {field}"

    def test_multiple_drivers_same_name(self, fastf1_cache_dir):
        """Test handling of drivers with same family name."""
        # Search for Michael Schumacher using driver ID
        result = get_driver_info(driver_code="michael_schumacher")

        # Should find Michael Schumacher
        assert result["total_drivers"] >= 1
        assert any("Schumacher" in d["family_name"] for d in result["drivers"])
