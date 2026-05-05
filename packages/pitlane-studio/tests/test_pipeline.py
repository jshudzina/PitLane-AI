"""Phase 3 pipeline xfail stubs — PTW-01, PTW-02, PTW-03, PTW-04.

These stubs establish the test contract for PipelineOrchestrator and SSE streaming.
They will be filled in by Plans 03-02 and 03-03.

Note: pytest-asyncio is NOT yet installed (added in Plan 03-04).
All stubs here are sync-only.
"""

from __future__ import annotations

import pytest


@pytest.mark.xfail(reason="PipelineOrchestrator not yet implemented", strict=True)
def test_generate_outline():
    raise NotImplementedError("PipelineOrchestrator not yet implemented")


@pytest.mark.xfail(reason="PipelineOrchestrator.stream_beat not yet implemented", strict=True)
def test_stream_beat_events():
    raise NotImplementedError("PipelineOrchestrator.stream_beat not yet implemented")


@pytest.mark.xfail(reason="SSE format not yet implemented", strict=True)
def test_sse_format():
    raise NotImplementedError("SSE format not yet implemented")


@pytest.mark.xfail(reason="Placeholder detection not yet implemented", strict=True)
def test_placeholder_detection():
    raise NotImplementedError("Placeholder detection not yet implemented")


@pytest.mark.xfail(reason="beat_done payload not yet implemented", strict=True)
def test_beat_done_payload():
    raise NotImplementedError("beat_done payload not yet implemented")
