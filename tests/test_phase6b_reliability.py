import json
import threading
import time
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.database import connect
from app.publish_service import publish_draft
from app.publishing import PublishResult, Publisher, PublishingError
from app.scheduler import run_due_schedules
import app.publish_service as publish_service


class SlowPublisher(Publisher):
    provider = "fake"
    calls = 0
    lock = threading.Lock()

    def publish(self, title, body, hashtags):
        with self.lock:
            type(self).calls += 1
        time.sleep(0.1)
        return PublishResult(provider=self.provider, remote_id="remote-123")


class PermanentFailurePublisher(Publisher):
    provider = "fake"

    def publish(self, title, body, hashtags):
        raise PublishingError("invalid credentials", retryable=False)


class TransientFailurePublisher(Publisher):
    provider = "fake"

    def publish(self, title, body, hashtags):
        raise PublishingError("temporary upstream failure", retryable=True)


def _approved_draft(settings):
    connection = connect(settings.database_url)
    connection.execute(
        "INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) "
        "VALUES ('t', '1', 'x', 'https://example.com', '2026-01-01', 'fp')"
    )
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    connection.execute(
        "INSERT INTO content_drafts (problem_id, title, body, hashtags, status, created_at, updated_at) "
        "VALUES (?, 'x', 'body', ?, 'approved', '2026-01-01', '2026-01-01')",
        (problem_id, json.dumps(["tag"])),
    )
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()
    return draft_id


def test_concurrent_publish_allows_only_one_remote_call(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    SlowPublisher.calls = 0
    monkeypatch.setattr(publish_service, "get_publisher", lambda settings, name: SlowPublisher())

    results = []
    errors = []

    def run():
        try:
            results.append(publish_draft(settings, draft_id, "fake"))
        except PublishingError as exc:
            errors.append(exc)

    first = threading.Thread(target=run)
    second = threading.Thread(target=run)
    first.start()
    time.sleep(0.02)
    second.start()
    first.join()
    second.join()

    assert SlowPublisher.calls == 1
    assert len(results) == 1
    assert len(errors) == 1
    assert "already being published" in str(errors[0])

    connection = connect(settings.database_url)
    assert connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()[0] == "published"
    connection.close()


def test_permanent_publish_failure_is_not_retried(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    monkeypatch.setattr(publish_service, "get_publisher", lambda settings, name: PermanentFailurePublisher())

    schedule_connection = connect(settings.database_url)
    now = datetime.now(timezone.utc).isoformat()
    schedule_connection.execute(
        "INSERT INTO publish_schedules (draft_id, provider, scheduled_for, status, attempts, max_attempts, created_at, updated_at) "
        "VALUES (?, 'fake', ?, 'scheduled', 0, 3, ?, ?)",
        (draft_id, now, now, now),
    )
    schedule_connection.commit()
    schedule_connection.close()

    result = run_due_schedules(settings)
    assert result == {"processed": 1, "published": 0, "retried": 0, "failed": 1}

    connection = connect(settings.database_url)
    assert connection.execute("SELECT status FROM publish_schedules").fetchone()[0] == "failed"
    assert connection.execute("SELECT attempts FROM publish_schedules").fetchone()[0] == 1
    connection.close()


def test_transient_publish_failure_is_retried(tmp_path, monkeypatch):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
        retry_base_seconds=60,
        retry_max_seconds=3600,
    )
    draft_id = _approved_draft(settings)
    monkeypatch.setattr(publish_service, "get_publisher", lambda settings, name: TransientFailurePublisher())

    connection = connect(settings.database_url)
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO publish_schedules (draft_id, provider, scheduled_for, status, attempts, max_attempts, created_at, updated_at) "
        "VALUES (?, 'fake', ?, 'scheduled', 0, 3, ?, ?)",
        (draft_id, now, now, now),
    )
    connection.commit()
    connection.close()

    result = run_due_schedules(settings)
    assert result == {"processed": 1, "published": 0, "retried": 1, "failed": 0}

    connection = connect(settings.database_url)
    row = connection.execute("SELECT status, attempts, scheduled_for FROM publish_schedules").fetchone()
    assert row[0] == "retrying"
    assert row[1] == 1
    assert datetime.fromisoformat(row[2]) > datetime.now(timezone.utc)
    connection.close()
