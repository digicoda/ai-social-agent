import json

import pytest

from app.config import Settings
from app.database import connect
from app.publish_service import publish_draft
from app.publishing import PublishResult, Publisher, PublishingError
import app.publish_service as service


class FakePublisher(Publisher):
    provider = "fake"

    def publish(self, title, body, hashtags):
        return PublishResult(provider="fake", remote_id="remote-123")


def test_publish_service_marks_approved_draft_published(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    connection = connect(settings.database_url)
    connection.execute("INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES ('t', '1', 'x', 'https://example.com', '2026-01-01', 'fp')")
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    connection.execute("INSERT INTO content_drafts (problem_id, title, body, hashtags, status, created_at, updated_at) VALUES (?, 'x', 'body', ?, 'approved', '2026-01-01', '2026-01-01')", (problem_id, json.dumps(["tag"])))
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()
    monkeypatch.setattr(service, "get_publisher", lambda settings, name: FakePublisher())

    result = publish_draft(settings, draft_id, "fake")

    assert result["remote_id"] == "remote-123"
    connection = connect(settings.database_url)
    assert connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()[0] == "published"
    assert connection.execute("SELECT status, remote_id FROM publishing_attempts WHERE draft_id = ?", (draft_id,)).fetchone()[:2] == ("published", "remote-123")
    connection.close()
