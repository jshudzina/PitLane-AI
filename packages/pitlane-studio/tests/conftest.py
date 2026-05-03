"""Pytest configuration and shared fixtures for pitlane-studio tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pitlane_studio.store.article_store import ArticleStore


@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> Path:
    """Return a path to a temporary SQLite file (file does not yet exist)."""
    return tmp_path / "articles.db"


@pytest.fixture()
def tmp_store(tmp_db_path: Path) -> ArticleStore:
    """ArticleStore backed by a temporary SQLite file."""
    return ArticleStore(db_path=tmp_db_path)
