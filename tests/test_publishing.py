import json

import pytest

from app.config import Settings
from app.database import connect
from app.publish_service import publish_draft
from app.publishing import PublishResult, Publisher, PublishingError, get_publisher


def test_publish_requires_approved_draft(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    connection = connect(settings.database_url)
    connection.execute("INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES ('t', '1', 'x', 'https://example.com', '2026-01-01', 'fp')")
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    connection.execute("INSERT INTO content_drafts (problem_id, title, body, hashtags, status, created_at, updated_at) VALUES (?, 'x', 'body', ?, 'pending_approval', '2026-01-01', '2026-01-01')", (problem_id, json.dumps([])))
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()

    with pytest.raises(PublishingError, match="only approved"):
        publish_draft(settings, draft_id, "linkedin")


def test_unknown_provider_rejected():
    with pytest.raises(PublishingError, match="unsupported"):
        get_publisher(Settings(), "unknown")
