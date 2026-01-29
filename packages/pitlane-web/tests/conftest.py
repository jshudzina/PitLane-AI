"""Pytest configuration and shared fixtures for pitlane-web tests."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_session_id():
    """Provide a valid test session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def invalid_session_ids():
    """Provide various invalid session ID formats for testing."""
    return [
        "not-a-uuid",
        "12345",
        "",
        "../../../../etc/passwd",
        "null",
        None,
        123,  # Not a string
        "g0000000-0000-0000-0000-000000000000",  # Invalid UUID (g is not hex)
        "00000000-0000-0000-0000-00000000000",  # Too short
        "00000000-0000-0000-0000-0000000000000",  # Too long
    ]


@pytest.fixture
def tmp_workspace(tmp_path, test_session_id):
    """Create a temporary workspace directory structure."""
    workspace = tmp_path / "workspaces" / test_session_id
    workspace.mkdir(parents=True)
    (workspace / "charts").mkdir()
    (workspace / "data").mkdir()

    # Create metadata file
    metadata = {
        "session_id": test_session_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_accessed": datetime.utcnow().isoformat() + "Z",
    }

    with open(workspace / ".metadata.json", "w") as f:
        json.dump(metadata, f)

    return workspace


@pytest.fixture
def sample_chart_file(tmp_workspace):
    """Create a sample PNG chart file."""
    chart_path = tmp_workspace / "charts" / "lap_times.png"
    # Create a minimal valid PNG (1x1 transparent pixel)
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    chart_path.write_bytes(png_data)
    return chart_path


@pytest.fixture
def mock_agent():
    """Mock F1Agent instance."""
    agent = MagicMock()
    agent.chat_full = AsyncMock(return_value="Mocked agent response")
    agent.session_id = "test-session-123"
    agent.workspace_dir = Path("/tmp/test-workspace")
    return agent


@pytest.fixture
def mock_workspace_functions(monkeypatch, test_session_id, tmp_workspace):
    """Mock workspace management functions."""
    monkeypatch.setattr("pitlane_web.session.workspace_exists", MagicMock(return_value=True))
    monkeypatch.setattr("pitlane_web.session.generate_session_id", MagicMock(return_value=test_session_id))
    monkeypatch.setattr(
        "pitlane_agent.scripts.workspace.get_workspace_path",
        MagicMock(return_value=tmp_workspace),
    )
    monkeypatch.setattr("pitlane_web.session.update_workspace_metadata", MagicMock())


@pytest.fixture
def app_client(mock_workspace_functions, monkeypatch, mock_agent):
    """FastAPI TestClient for endpoint testing."""
    # Mock the agent cache to return our mock agent
    # Patch both locations to ensure consistency across all tests
    from pitlane_web import agent_manager
    from pitlane_web import app as web_app

    mock_cache = MagicMock()
    mock_cache.get_or_create = MagicMock(return_value=mock_agent)
    monkeypatch.setattr(agent_manager, "_agent_cache", mock_cache)
    monkeypatch.setattr(web_app, "_agent_cache", mock_cache)

    return TestClient(web_app.app)


@pytest.fixture
def mock_templates():
    """Mock Jinja2Templates instance."""
    templates = MagicMock()
    templates.env = MagicMock()
    templates.env.filters = {}
    return templates
