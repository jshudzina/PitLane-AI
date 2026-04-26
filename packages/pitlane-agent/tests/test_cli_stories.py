"""Unit tests for pitlane_agent.cli_stories (detect and season commands)."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner
from pitlane_agent.cli_stories import stories
from pitlane_elo.stories.signals import StorySignal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    driver_id: str = "VER",
    value: float = 0.8,
    signal_type: str = "hot_streak",
    year: int = 2024,
    round_num: int = 5,
) -> StorySignal:
    return StorySignal(
        signal_type=signal_type,
        driver_id=driver_id,
        year=year,
        round=round_num,
        value=value,
        threshold=0.5,
        narrative=f"{driver_id} signal",
        context={},
    )


def _make_entry(year: int, round_num: int, driver_id: str = "VER") -> dict:
    return {
        "year": year,
        "round": round_num,
        "session_type": "R",
        "driver_id": driver_id,
        "team": "Red Bull Racing",
    }


_ENV = {"PITLANE_WORKSPACE_ID": "test-workspace"}


# ---------------------------------------------------------------------------
# stories detect
# ---------------------------------------------------------------------------


class TestStoriesDetectCommand:
    def test_help_shows_options(self):
        result = CliRunner().invoke(stories, ["detect", "--help"])
        assert result.exit_code == 0
        assert "--year" in result.output
        assert "--round" in result.output
        assert "--session-type" in result.output
        assert "--trend-lookback" in result.output

    def test_missing_year_is_error(self):
        result = CliRunner().invoke(stories, ["detect", "--round", "5"], env=_ENV)
        assert result.exit_code != 0

    def test_missing_round_is_error(self):
        result = CliRunner().invoke(stories, ["detect", "--year", "2024"], env=_ENV)
        assert result.exit_code != 0

    @patch("pitlane_agent.cli_stories.workspace_exists")
    def test_workspace_not_found_exits_1(self, mock_exists):
        mock_exists.return_value = False
        result = CliRunner().invoke(
            stories,
            ["detect", "--year", "2024", "--round", "5"],
            env={"PITLANE_WORKSPACE_ID": "ghost"},
        )
        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "ghost" in err["error"]

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_success_stdout_structure(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = [_make_signal("VER"), _make_signal("HAM", -0.7, "slump")]

        result = CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["year"] == 2024
        assert out["round"] == 5
        assert out["story_count"] == 2
        assert "data_file" in out

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_writes_json_file_with_correct_name(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = [_make_signal()]

        CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        output_file = tmp_path / "data" / "stories_2024_5.json"
        assert output_file.exists()

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_written_payload_matches_signals(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = [_make_signal("VER"), _make_signal("LEC", 0.6)]

        CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        payload = json.loads((tmp_path / "data" / "stories_2024_5.json").read_text())
        assert payload["year"] == 2024
        assert payload["round"] == 5
        assert payload["story_count"] == 2
        assert len(payload["signals"]) == 2
        assert payload["signals"][0]["driver_id"] == "VER"

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_no_signals_adds_message_to_payload(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = []

        CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        payload = json.loads((tmp_path / "data" / "stories_2024_5.json").read_text())
        assert payload["story_count"] == 0
        assert "message" in payload

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_default_session_type_is_r(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = []

        CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        _, kwargs = mock_detect.call_args
        assert kwargs["session_type"] == "R"

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_session_type_s_forwarded(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = []

        result = CliRunner().invoke(
            stories,
            ["detect", "--year", "2024", "--round", "5", "--session-type", "S"],
            env=_ENV,
        )

        assert result.exit_code == 0
        _, kwargs = mock_detect.call_args
        assert kwargs["session_type"] == "S"

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_trend_lookback_forwarded(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = []

        CliRunner().invoke(
            stories,
            ["detect", "--year", "2024", "--round", "5", "--trend-lookback", "5"],
            env=_ENV,
        )

        _, kwargs = mock_detect.call_args
        assert kwargs["trend_lookback"] == 5

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_data_file_path_in_stdout(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.return_value = []

        result = CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "7"], env=_ENV)

        out = json.loads(result.output)
        assert "stories_2024_7.json" in out["data_file"]

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_detect_stories_exception_exits_1_with_error_json(self, mock_detect, mock_path, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_detect.side_effect = RuntimeError("snapshot missing")

        result = CliRunner().invoke(stories, ["detect", "--year", "2024", "--round", "5"], env=_ENV)

        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "snapshot missing" in err["error"]


# ---------------------------------------------------------------------------
# stories season
# ---------------------------------------------------------------------------


class TestStoriesSeasonCommand:
    def test_help_shows_options(self):
        result = CliRunner().invoke(stories, ["season", "--help"])
        assert result.exit_code == 0
        assert "--year" in result.output
        assert "--session-type" in result.output
        assert "--trend-lookback" in result.output

    def test_missing_year_is_error(self):
        result = CliRunner().invoke(stories, ["season"], env=_ENV)
        assert result.exit_code != 0

    @patch("pitlane_agent.cli_stories.workspace_exists")
    def test_workspace_not_found_exits_1(self, mock_exists):
        mock_exists.return_value = False
        result = CliRunner().invoke(
            stories,
            ["season", "--year", "2024"],
            env={"PITLANE_WORKSPACE_ID": "ghost"},
        )
        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    def test_no_entries_exits_1_with_error(self, mock_entries, mock_data_dir, mock_exists, tmp_path):
        mock_exists.return_value = True
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = []

        result = CliRunner().invoke(stories, ["season", "--year", "2024"], env=_ENV)

        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "2024" in err["error"]

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    @patch("pitlane_elo.data.group_entries_by_race")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_success_stdout_structure(
        self,
        mock_detect,
        mock_group,
        mock_entries,
        mock_data_dir,
        mock_path,
        mock_exists,
        tmp_path,
    ):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = [_make_entry(2024, 1), _make_entry(2024, 2)]
        mock_group.return_value = [
            [_make_entry(2024, 1)],
            [_make_entry(2024, 2)],
        ]
        mock_detect.side_effect = [
            [_make_signal("VER"), _make_signal("HAM", -0.7, "slump")],
            [_make_signal("LEC")],
        ]

        result = CliRunner().invoke(stories, ["season", "--year", "2024"], env=_ENV)

        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["year"] == 2024
        assert out["total_races"] == 2
        assert out["total_signals"] == 3
        assert "data_file" in out

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    @patch("pitlane_elo.data.group_entries_by_race")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_writes_season_json_file(
        self,
        mock_detect,
        mock_group,
        mock_entries,
        mock_data_dir,
        mock_path,
        mock_exists,
        tmp_path,
    ):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = [_make_entry(2025, 1)]
        mock_group.return_value = [[_make_entry(2025, 1)]]
        mock_detect.return_value = []

        CliRunner().invoke(stories, ["season", "--year", "2025"], env=_ENV)

        assert (tmp_path / "data" / "stories_2025_season.json").exists()

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    @patch("pitlane_elo.data.group_entries_by_race")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_season_json_payload_structure(
        self,
        mock_detect,
        mock_group,
        mock_entries,
        mock_data_dir,
        mock_path,
        mock_exists,
        tmp_path,
    ):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = [_make_entry(2024, 3)]
        mock_group.return_value = [[_make_entry(2024, 3)]]
        mock_detect.return_value = [_make_signal("SAI", year=2024, round_num=3)]

        CliRunner().invoke(stories, ["season", "--year", "2024"], env=_ENV)

        payload = json.loads((tmp_path / "data" / "stories_2024_season.json").read_text())
        assert payload["year"] == 2024
        assert payload["total_races"] == 1
        assert len(payload["races"]) == 1
        race = payload["races"][0]
        assert race["year"] == 2024
        assert race["round"] == 3
        assert race["story_count"] == 1
        assert len(race["signals"]) == 1

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    @patch("pitlane_elo.data.group_entries_by_race")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_total_signals_is_sum_across_races(
        self,
        mock_detect,
        mock_group,
        mock_entries,
        mock_data_dir,
        mock_path,
        mock_exists,
        tmp_path,
    ):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = [_make_entry(2024, i) for i in range(1, 4)]
        mock_group.return_value = [[_make_entry(2024, i)] for i in range(1, 4)]
        mock_detect.side_effect = [
            [_make_signal()],  # round 1: 1 signal
            [],  # round 2: 0 signals
            [_make_signal(), _make_signal("HAM")],  # round 3: 2 signals
        ]

        result = CliRunner().invoke(stories, ["season", "--year", "2024"], env=_ENV)

        assert result.exit_code == 0
        assert json.loads(result.output)["total_signals"] == 3

    @patch("pitlane_agent.cli_stories.workspace_exists")
    @patch("pitlane_agent.cli_stories.get_workspace_path")
    @patch("pitlane_elo.data.get_data_dir")
    @patch("pitlane_elo.data.get_race_entries")
    @patch("pitlane_elo.data.group_entries_by_race")
    @patch("pitlane_elo.stories.signals.detect_stories")
    def test_exception_exits_1_with_error_json(
        self,
        mock_detect,
        mock_group,
        mock_entries,
        mock_data_dir,
        mock_path,
        mock_exists,
        tmp_path,
    ):
        mock_exists.return_value = True
        mock_path.return_value = tmp_path
        mock_data_dir.return_value = tmp_path
        mock_entries.return_value = [_make_entry(2024, 1)]
        mock_group.return_value = [[_make_entry(2024, 1)]]
        mock_detect.side_effect = RuntimeError("duckdb error")

        result = CliRunner().invoke(stories, ["season", "--year", "2024"], env=_ENV)

        assert result.exit_code == 1
        err = json.loads(result.output)
        assert "error" in err
        assert "duckdb error" in err["error"]
