"""Integration tests for FastF1 event schedule functionality.

These tests make real API calls to FastF1 to verify event schedule integration.
"""

import pytest
from pitlane_agent.scripts.event_schedule import get_event_schedule


@pytest.mark.integration
@pytest.mark.slow
class TestEventScheduleIntegration:
    """Integration tests for event schedule with real FastF1 API."""

    def test_get_full_season_schedule(self, fastf1_cache_dir, stable_test_data):
        """Test fetching complete season schedule from FastF1."""
        result = get_event_schedule(stable_test_data["year"])

        assert result["year"] == stable_test_data["year"]
        assert result["total_events"] == stable_test_data["total_rounds"]
        assert len(result["events"]) == stable_test_data["total_rounds"]

        # Verify first event structure
        first_event = result["events"][0]
        assert "round" in first_event
        assert "country" in first_event
        assert "event_name" in first_event
        assert "sessions" in first_event
        assert len(first_event["sessions"]) >= 3  # At least FP1, Q, R

    def test_get_specific_round(self, fastf1_cache_dir, stable_test_data):
        """Test fetching specific round from schedule."""
        # Get Monaco GP (need to find actual round number)
        full_schedule = get_event_schedule(stable_test_data["year"])

        # Find Monaco round number
        monaco_round = None
        for event in full_schedule["events"]:
            if event["country"] == "Monaco":
                monaco_round = event["round"]
                break

        assert monaco_round is not None, "Monaco GP not found in schedule"

        # Now test filtering by round
        result = get_event_schedule(stable_test_data["year"], round_number=monaco_round)

        assert result["total_events"] == 1
        assert result["events"][0]["country"] == "Monaco"
        assert result["filters"]["round"] == monaco_round

    def test_get_specific_country(self, fastf1_cache_dir, stable_test_data):
        """Test fetching specific country from schedule."""
        result = get_event_schedule(stable_test_data["year"], country="italy")

        assert result["total_events"] >= 1  # At least one Italian race
        # Verify all returned events are in Italy
        for event in result["events"]:
            assert event["country"].lower() == "italy"
        assert result["filters"]["country"] == "italy"

    def test_schedule_has_valid_session_dates(self, fastf1_cache_dir, recent_race_data):
        """Test that schedule contains valid session date information."""
        result = get_event_schedule(recent_race_data["year"], round_number=recent_race_data["round"])

        assert result["total_events"] == 1
        event = result["events"][0]

        # Verify sessions have valid data
        assert len(event["sessions"]) >= 3  # At least Practice, Qualifying, Race
        for session in event["sessions"]:
            assert session["name"] is not None
            assert session["name"] != ""
            # Date fields should be present (may be None for some sessions)
            assert "date_local" in session
            assert "date_utc" in session

    def test_schedule_exclude_testing(self, fastf1_cache_dir, stable_test_data):
        """Test excluding testing sessions from schedule."""
        result = get_event_schedule(stable_test_data["year"], include_testing=False)

        assert result["include_testing"] is False
        # Verify we got race events (testing excluded)
        assert result["total_events"] >= 20  # Should have main season races

    def test_schedule_event_format(self, fastf1_cache_dir, stable_test_data):
        """Test that events have proper format information."""
        result = get_event_schedule(stable_test_data["year"], round_number=1)

        event = result["events"][0]
        assert "event_format" in event
        assert event["event_format"] in ["conventional", "sprint", "sprint_shootout"]
        assert "f1_api_support" in event
        assert isinstance(event["f1_api_support"], bool)
