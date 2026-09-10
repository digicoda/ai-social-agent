import json
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.database import connect
from app.publish_service import publish_draft
from app.publishing import PublishResult, Publisher
from app.scheduler import run_due_schedules
from app.scheduling import schedule_draft
import app.publish_service as publish_service


class FakePublisher(Publisher):
    provider = "fake"

    def publish(self, title, body, hashtags):
        return PublishResult(provider="fake", remote_id="remote-123")


def _approved_draft(settings):
    connection = connect(settings.database_url)
    connection.execute("INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES ('t', '1', 'x', 'https://example.com', '2026-01-01', 'fp')")
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    connection.execute("INSERT INTO content_drafts (problem_id, title, body, hashtags, status, created_at, updated_at) VALUES (?, 'x', 'body', ?, 'approved', '2026-01-01', '2026-01-01')", (problem_id, json.dumps(["tag"])))
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()
    return draft_id


def test_schedule_requires_future_time(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    try:
        schedule_draft(settings, draft_id, "fake", "2020-01-01T00:00:00+00:00")
    except ValueError as exc:
        assert "future" in str(exc)
    else:
        raise AssertionError("expected future-date validation")


def test_worker_publishes_due_schedule_and_is_idempotent(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    monkeypatch.setattr(publish_service, "get_publisher", lambda settings, name: FakePublisher())
    schedule_id = schedule_draft(settings, draft_id, "fake", (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat())['schedule_id']

    connection = connect(settings.database_url)
    connection.execute("UPDATE publish_schedules SET scheduled_for = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), schedule_id))
    connection.commit()
    connection.close()

    result = run_due_schedules(settings, limit=10)
    assert result["published"] == 1
    assert connect(settings.database_url).execute("SELECT status FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()[0] == "published"

    result = publish_draft(settings, draft_id, "fake")
    assert result["idempotent"] is True
