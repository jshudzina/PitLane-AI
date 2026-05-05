"""Phase 3 router xfail stubs — ACT-03, UI-01, UI-03, PTW-02 gate.

These stubs establish the test contract for the FastAPI router endpoints.
They will be filled in by Plans 03-03 and 03-05.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="Acts router not yet implemented", strict=True)
def test_acts_route_returns_all_five_acts():
    raise NotImplementedError


@pytest.mark.xfail(reason="Angles route not yet implemented", strict=True)
def test_angles_route():
    raise NotImplementedError


@pytest.mark.xfail(reason="Stream beat gate (409) route not yet implemented", strict=True)
def test_stream_beat_gate_409():
    raise NotImplementedError


@pytest.mark.xfail(reason="Approve outline route not yet implemented", strict=True)
def test_approve_outline():
    raise NotImplementedError


@pytest.mark.xfail(reason="Patch outline route not yet implemented", strict=True)
def test_patch_outline():
    raise NotImplementedError
