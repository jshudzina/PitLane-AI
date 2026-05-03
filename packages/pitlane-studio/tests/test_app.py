"""PKG-01 smoke test — pitlane-studio CLI/app health endpoint returns 200.

XFAIL until Plan 02 creates pitlane_studio.app:app.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.xfail(
    reason="pitlane_studio.app not yet implemented (lands in Plan 02)",
    strict=False,
    run=True,
)


def test_health_endpoint_returns_200():
    """GET /health returns {'status': 'ok'} with HTTP 200."""
    from fastapi.testclient import TestClient

    from pitlane_studio.app import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
