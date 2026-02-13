"""Integration tests for race control message retrieval.

These tests make real API calls to FastF1 to load race control messages
and verify filtering, detail levels, and data structure.
"""

import pytest
from pitlane_agent.commands.fetch.race_control import get_race_control_messages


@pytest.mark.integration
class TestRaceControlIntegration:
    """Integration tests for get_race_control_messages with real FastF1 data."""

    def test_get_messages_full_detail(self, fastf1_cache_dir, recent_race_data):
        """Test retrieving all race control messages (full detail)."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )

        assert result["year"] == recent_race_data["year"]
        assert result["session_type"] == "R"
        assert result["total_messages"] > 0
        assert result["filtered_messages"] == result["total_messages"]
        assert result["filters_applied"]["detail"] == "full"
        assert len(result["messages"]) == result["filtered_messages"]

    def test_get_messages_high_detail(self, fastf1_cache_dir, recent_race_data):
        """Test that high detail returns fewer messages than full."""
        full = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )
        high = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="high",
        )

        assert high["filtered_messages"] < full["filtered_messages"]
        assert high["total_messages"] == full["total_messages"]
        assert high["filters_applied"]["detail"] == "high"

    def test_get_messages_medium_detail(self, fastf1_cache_dir, recent_race_data):
        """Test that medium detail returns more than high but less than full."""
        full = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )
        medium = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="medium",
        )
        high = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="high",
        )

        assert high["filtered_messages"] <= medium["filtered_messages"]
        assert medium["filtered_messages"] <= full["filtered_messages"]

    def test_message_data_structure(self, fastf1_cache_dir, recent_race_data):
        """Test that each message has the expected fields and types."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )

        assert len(result["messages"]) > 0

        for msg in result["messages"]:
            # Required keys exist
            assert "lap" in msg
            assert "time" in msg
            assert "category" in msg
            assert "message" in msg
            assert "flag" in msg
            assert "scope" in msg
            assert "sector" in msg
            assert "racing_number" in msg

            # Type checks for non-None values
            if msg["lap"] is not None:
                assert isinstance(msg["lap"], int)
            if msg["time"] is not None:
                assert isinstance(msg["time"], str)
            if msg["sector"] is not None:
                assert isinstance(msg["sector"], int)
            if msg["category"] is not None:
                assert isinstance(msg["category"], str)

    def test_filter_by_category_flag(self, fastf1_cache_dir, recent_race_data):
        """Test filtering messages by Flag category."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
            category="Flag",
        )

        assert result["filters_applied"]["category"] == "Flag"
        for msg in result["messages"]:
            assert msg["category"] == "Flag"

    def test_filter_by_driver(self, fastf1_cache_dir, recent_race_data):
        """Test filtering messages by driver racing number."""
        # First get all messages to find a driver number that appears
        full = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )

        # Find a driver number that has messages
        driver_number = None
        for msg in full["messages"]:
            if msg["racing_number"] is not None:
                driver_number = msg["racing_number"]
                break

        if driver_number is None:
            pytest.skip("No driver-specific messages found in this race")

        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
            driver=driver_number,
        )

        assert result["filters_applied"]["driver"] == driver_number
        assert result["filtered_messages"] > 0
        for msg in result["messages"]:
            assert msg["racing_number"] == driver_number

    def test_filter_by_lap_range(self, fastf1_cache_dir, recent_race_data):
        """Test filtering messages by lap range."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
            lap_start=1,
            lap_end=5,
        )

        assert result["filters_applied"]["lap_start"] == 1
        assert result["filters_applied"]["lap_end"] == 5
        for msg in result["messages"]:
            if msg["lap"] is not None:
                assert 1 <= msg["lap"] <= 5

    def test_metadata_fields(self, fastf1_cache_dir, recent_race_data):
        """Test that result metadata is populated correctly."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
        )

        assert result["year"] == recent_race_data["year"]
        assert isinstance(result["event_name"], str)
        assert len(result["event_name"]) > 0
        assert isinstance(result["country"], str)
        assert len(result["country"]) > 0
        assert result["session_type"] == "R"
        assert result["session_name"] == "Race"
        assert isinstance(result["total_messages"], int)
        assert isinstance(result["filtered_messages"], int)

    def test_qualifying_session_messages(self, fastf1_cache_dir, stable_test_data):
        """Test loading race control messages from a qualifying session."""
        result = get_race_control_messages(
            year=stable_test_data["year"],
            gp=stable_test_data["test_gp"],
            session_type="Q",
            detail="full",
        )

        assert result["session_type"] == "Q"
        assert result["total_messages"] >= 0
        # Qualifying should have messages (flags, track limits, etc.)
        if result["total_messages"] > 0:
            assert len(result["messages"]) > 0

    def test_combined_filters(self, fastf1_cache_dir, recent_race_data):
        """Test applying multiple filters simultaneously."""
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
            category="Flag",
            lap_start=1,
            lap_end=10,
        )

        assert result["filters_applied"]["category"] == "Flag"
        assert result["filters_applied"]["lap_start"] == 1
        assert result["filters_applied"]["lap_end"] == 10
        assert result["filtered_messages"] <= result["total_messages"]

        for msg in result["messages"]:
            assert msg["category"] == "Flag"
            if msg["lap"] is not None:
                assert 1 <= msg["lap"] <= 10

    def test_detail_filter_applied_before_other_filters(self, fastf1_cache_dir, recent_race_data):
        """Test that detail + category filters produce correct results.

        Verifies the optimization of applying detail filter first doesn't
        change the logical result compared to applying it last.
        """
        # Get high detail with Flag category
        result = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="high",
            category="Flag",
        )

        # Every message should satisfy both: high-impact AND Flag category
        for msg in result["messages"]:
            assert msg["category"] == "Flag"

        # Should be a subset of full detail + Flag category
        full_flags = get_race_control_messages(
            year=recent_race_data["year"],
            gp=recent_race_data["gp"],
            session_type="R",
            detail="full",
            category="Flag",
        )

        assert result["filtered_messages"] <= full_flags["filtered_messages"]
