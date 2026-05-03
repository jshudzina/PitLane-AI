"""PKG-02 integration test — pitlane_elo.studio_api.detect_stories with real data.

XFAIL until Plan 03 creates pitlane_elo.studio_api.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.xfail(
    reason="pitlane_elo.studio_api not yet implemented (lands in Plan 03)",
    strict=False,
    run=True,
)


def test_detect_stories_latest_2026_race():
    """Integration test: detect_stories() with real cached 2026 data, no mocks."""
    from pitlane_elo.data import get_race_entries
    from pitlane_elo.studio_api import StorySignal, detect_stories

    entries = get_race_entries(2026, session_type="R")
    if not entries:
        pytest.skip("No 2026 race data cached — run ELO pipeline first")
    latest_round = max(e["round"] for e in entries)
    signals = detect_stories(year=2026, round=latest_round)
    assert isinstance(signals, list)
    assert all(isinstance(s, StorySignal) for s in signals)


def test_studio_api_exports():
    """Module exposes detect_stories and StorySignal in __all__."""
    from pitlane_elo import studio_api

    assert "detect_stories" in studio_api.__all__
    assert "StorySignal" in studio_api.__all__
