"""ACT-01..02 tests — FiveActMapper and ACT_CONFIG.

XFAIL until Plan 02 creates pitlane_studio.services.five_act.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.xfail(
    reason="pitlane_studio.services.five_act not yet implemented (lands in Plan 02)",
    strict=False,
    run=True,
)


class TestActConfigStructure:
    """ACT-01: ACT_CONFIG maps all 5 acts to pitlane-agent command callables."""

    def test_all_five_acts_present(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        assert set(ACT_CONFIG.keys()) == {1, 2, 3, 4, 5}

    def test_each_act_has_label(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        for act_num, config in ACT_CONFIG.items():
            assert "label" in config, f"Act {act_num} missing 'label'"
            assert isinstance(config["label"], str)
            assert len(config["label"]) > 0

    def test_each_act_has_commands_list(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        for act_num, config in ACT_CONFIG.items():
            assert "commands" in config, f"Act {act_num} missing 'commands'"
            assert isinstance(config["commands"], list)
            assert len(config["commands"]) >= 1

    def test_commands_are_callable(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        for act_num, config in ACT_CONFIG.items():
            for cmd in config["commands"]:
                assert callable(cmd), f"Act {act_num} command {cmd!r} is not callable"

    def test_act1_label_is_qualifying(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        assert "Qualifying" in ACT_CONFIG[1]["label"] or "Grid" in ACT_CONFIG[1]["label"]

    def test_act5_label_is_championship(self):
        from pitlane_studio.services.five_act import ACT_CONFIG

        assert "Championship" in ACT_CONFIG[5]["label"] or "Implications" in ACT_CONFIG[5]["label"]

    def test_act1_includes_session_info_command(self):
        from pitlane_agent.commands.fetch.session_info import get_session_info

        from pitlane_studio.services.five_act import ACT_CONFIG

        assert get_session_info in ACT_CONFIG[1]["commands"]

    def test_act3_includes_tyre_strategy_command(self):
        from pitlane_agent.commands.analyze.tyre_strategy import generate_tyre_strategy_chart

        from pitlane_studio.services.five_act import ACT_CONFIG

        assert generate_tyre_strategy_chart in ACT_CONFIG[3]["commands"]

    def test_act5_includes_driver_standings_command(self):
        from pitlane_agent.commands.fetch.driver_standings import get_driver_standings

        from pitlane_studio.services.five_act import ACT_CONFIG

        assert get_driver_standings in ACT_CONFIG[5]["commands"]


class TestFetchActData:
    """ACT-02: fetch_act_data() returns a dict and caches subsequent calls."""

    def test_fetch_act_data_returns_dict(self, mocker):
        """fetch_act_data() returns a dict for a valid act number."""
        mocker.patch(
            "pitlane_agent.commands.fetch.session_info.get_session_info",
            return_value={"date": "2026-03-16", "total_laps": 57},
        )
        mocker.patch(
            "pitlane_agent.commands.analyze.qualifying_results.generate_qualifying_results_chart",
            return_value={"results": []},
        )
        from pitlane_studio.services.five_act import FiveActMapper

        mapper = FiveActMapper()
        result = mapper.fetch_act_data(year=2026, round_num=1, act_number=1)
        assert isinstance(result, dict)

    def test_cache_returns_same_object_on_second_call(self, mocker):
        """Second call for same (year, round, act_number) returns cached result."""
        mock_get_session = mocker.patch(
            "pitlane_agent.commands.fetch.session_info.get_session_info",
            return_value={"date": "2026-03-16", "total_laps": 57},
        )
        mocker.patch(
            "pitlane_agent.commands.analyze.qualifying_results.generate_qualifying_results_chart",
            return_value={"results": []},
        )
        from pitlane_studio.services.five_act import FiveActMapper

        mapper = FiveActMapper()
        first = mapper.fetch_act_data(year=2026, round_num=1, act_number=1)
        second = mapper.fetch_act_data(year=2026, round_num=1, act_number=1)
        assert first is second  # same dict object from cache
        # Commands called only once
        assert mock_get_session.call_count == 1

    def test_chart_dir_created_on_init(self, tmp_path, mocker):
        """FiveActMapper.__init__ creates the chart output directory."""
        mocker.patch(
            "pitlane_studio.services.five_act._CHART_DIR",
            tmp_path / "charts",
        )
        from pitlane_studio.services.five_act import FiveActMapper

        mapper = FiveActMapper()
        assert (tmp_path / "charts").exists()

    @pytest.mark.skipif(
        True,  # Replace with: not elo_data_available()
        reason="Skipped by default — requires live FastF1 cache; run manually",
    )
    def test_fetch_act1_real_data(self):
        """Integration: fetch act 1 data for a real race returns non-empty dict."""
        from pitlane_studio.services.five_act import FiveActMapper

        mapper = FiveActMapper()
        data = mapper.fetch_act_data(year=2026, round_num=1, act_number=1)
        assert data  # non-empty
