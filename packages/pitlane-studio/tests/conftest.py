"""Pytest configuration and shared fixtures for pitlane-studio tests.

Wave 0 scope: only fixtures that have zero dependency on production code
yet to be written. The `tmp_store` fixture is added by Plan 04 (Wave 2),
after `pitlane_studio.store.article_store.ArticleStore` exists, so its
import lives at the top of the file (per CLAUDE.md imports-at-top rule).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db_path(tmp_path: Path) -> Path:
    """Return a path to a temporary SQLite file (file does not yet exist)."""
    return tmp_path / "articles.db"
