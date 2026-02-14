"""Integration tests for season summary command.

These tests make real API calls to FastF1 to load multiple race sessions
and compute season summary statistics.
"""

import pytest
from pitlane_agent.commands.fetch.season_summary import get_season_summary


@pytest.mark.integration
@pytest.mark.slow
class TestSeasonSummaryIntegration:
    """Integration tests for season summary with real FastF1 data."""

    @pytest.mark.timeout(600)  # 10 minute timeout - loads multiple races
    def test_season_summary_structure(self, fastf1_cache_dir):
        """Test season summary returns expected structure for a complete season.

        Uses 2024 season (complete, stable data).
        """
        result = get_season_summary(2024)

        assert result["year"] == 2024
        # 2024 had 24 races + 6 sprints = 30 entries
        assert result["total_races"] >= 28

        # Verify race structure
        for race in result["races"]:
            assert "round" in race
            assert "event_name" in race
            assert "country" in race
            assert "date" in race
            assert "session_type" in race
            assert race["session_type"] in ("R", "S")
            assert "podium" in race
            assert "race_summary" in race
            assert "wildness_score" in race
            assert "num_safety_cars" in race
            assert "num_virtual_safety_cars" in race
            assert "num_red_flags" in race

            # Podium should have up to 3 drivers
            assert len(race["podium"]) <= 3
            assert len(race["podium"]) >= 1
            for driver in race["podium"]:
                assert isinstance(driver, str)
                assert len(driver) == 3  # Driver abbreviations are 3 chars

            # Race summary stats should be non-negative
            summary = race["race_summary"]
            assert summary["total_overtakes"] >= 0
            assert summary["total_position_changes"] >= 0
            assert summary["average_volatility"] >= 0
            assert summary["mean_pit_stops"] >= 0

            # Wildness score should be 0-1
            assert 0 <= race["wildness_score"] <= 1

        # Races should be sorted by wildness score descending
        scores = [r["wildness_score"] for r in result["races"]]
        assert scores == sorted(scores, reverse=True)

        # Should include sprint entries (2024 had 6 sprint weekends)
        sprint_entries = [r for r in result["races"] if r["session_type"] == "S"]
        assert len(sprint_entries) >= 4  # Allow some tolerance for data issues

        # Season averages should be present and non-negative
        avgs = result["season_averages"]
        assert avgs["total_overtakes"] >= 0
        assert avgs["total_position_changes"] >= 0
        assert avgs["average_volatility"] >= 0
        assert avgs["mean_pit_stops"] >= 0
