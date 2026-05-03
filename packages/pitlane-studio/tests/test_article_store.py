"""PKG-04 integration test — ArticleStore against real SQLite file (no mocks).

XFAIL until Plan 04 creates pitlane_studio.store.article_store.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.xfail(
    reason="pitlane_studio.store.article_store not yet implemented (lands in Plan 04)",
    strict=False,
    run=True,
)


class TestArticleStoreLifecycle:
    def test_create_returns_draft(self, tmp_store):
        article_id = str(uuid.uuid4())
        tmp_store.create(article_id, race_year=2026, race_round=5)
        record = tmp_store.get(article_id)
        assert record.status == "draft"
        assert record.race_year == 2026
        assert record.race_round == 5

    def test_full_lifecycle_draft_to_published(self, tmp_store):
        article_id = str(uuid.uuid4())
        tmp_store.create(article_id, race_year=2026, race_round=5)
        tmp_store.transition_status(article_id, "outline_generated")
        tmp_store.transition_status(article_id, "outline_approved")
        tmp_store.transition_status(article_id, "published")
        assert tmp_store.get(article_id).status == "published"

    def test_skip_to_published_raises_value_error(self, tmp_store):
        article_id = str(uuid.uuid4())
        tmp_store.create(article_id, race_year=2026, race_round=5)
        with pytest.raises(ValueError):
            tmp_store.transition_status(article_id, "published")

    def test_skip_to_outline_approved_raises_value_error(self, tmp_store):
        article_id = str(uuid.uuid4())
        tmp_store.create(article_id, race_year=2026, race_round=5)
        with pytest.raises(ValueError):
            tmp_store.transition_status(article_id, "outline_approved")

    def test_reverse_transition_raises_value_error(self, tmp_store):
        article_id = str(uuid.uuid4())
        tmp_store.create(article_id, race_year=2026, race_round=5)
        tmp_store.transition_status(article_id, "outline_generated")
        with pytest.raises(ValueError):
            tmp_store.transition_status(article_id, "draft")

    def test_unknown_id_raises_value_error(self, tmp_store):
        with pytest.raises(ValueError):
            tmp_store.transition_status("does-not-exist", "outline_generated")


class TestArticleStorePersistence:
    def test_articles_db_file_created_in_db_path(self, tmp_db_path: Path):
        from pitlane_studio.store.article_store import ArticleStore

        store = ArticleStore(db_path=tmp_db_path)
        store.create(str(uuid.uuid4()), race_year=2026, race_round=1)
        assert tmp_db_path.exists()
