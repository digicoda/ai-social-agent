from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.database import connect, create_schedule, save_draft
from app.errors import PublishingError
from app.scheduling import reschedule_draft, schedule_draft
from app.scheduler import run_due_schedules


class DummySettings:
    database_url: str
    retry_base_seconds = 1
    retry_max_seconds = 4


def _settings(tmp_path):
    settings = DummySettings()
    settings.database_url = f"sqlite:///{tmp_path / 'task8.db'}"
    return settings


def _draft(settings, status: str = "pending_approval") -> int:
    connection = connect(settings.database_url)
    try:
        connection.execute(
            "INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES (?, ?, ?, ?, ?, ?)",
            ("test", "task8", "Test problem", "https://example.com/task8", datetime.now(timezone.utc).isoformat(), "task8-fingerprint"),
        )
        problem_id = int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])
        draft_id = save_draft(connection, problem_id, "generic", "Test title", "Test body", ["test"], "", 90)
        if status != "pending_approval":
            connection.execute("UPDATE content_drafts SET status = ? WHERE id = ?", (status, draft_id))
            connection.commit()
        return draft_id
    finally:
        connection.close()


def _future(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def test_only_approved_drafts_can_be_scheduled(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    draft_id = _draft(settings)
    monkeypatch.setattr("app.scheduling.get_publisher", lambda *_: object())
    with pytest.raises(ValueError, match="only approved drafts can be scheduled"):
        schedule_draft(settings, draft_id, "linkedin", _future())


def test_approved_schedule_is_normalized_and_duplicate_active_schedule_is_blocked(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    draft_id = _draft(settings, "approved")
    monkeypatch.setattr("app.scheduling.get_publisher", lambda *_: object())
    result = schedule_draft(settings, draft_id, "linkedin", _future(), max_attempts=5)
    assert result["provider"] == "linkedin"
    assert result["max_attempts"] == 5
    assert result["scheduled_for"].endswith("+00:00")
    with pytest.raises(ValueError, match="already has an active schedule"):
        schedule_draft(settings, draft_id, "linkedin", _future())


def test_reschedule_moves_active_job_and_clears_retry_error(tmp_path):
    settings = _settings(tmp_path)
    draft_id = _draft(settings, "approved")
    connection = connect(settings.database_url)
    try:
        schedule_id = create_schedule(connection, draft_id, "linkedin", _future())
        connection.execute("UPDATE publish_schedules SET status = 'retrying', last_error = 'temporary' WHERE id = ?", (schedule_id,))
        connection.commit()
    finally:
        connection.close()
    result = reschedule_draft(settings, schedule_id, _future(60))
    assert result["status"] == "scheduled"
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT status, last_error, scheduled_for FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()
        assert row["status"] == "scheduled"
        assert row["last_error"] == ""
        assert row["scheduled_for"].endswith("+00:00")
    finally:
        connection.close()


def test_reschedule_rejects_published_or_running_jobs(tmp_path):
    settings = _settings(tmp_path)
    draft_id = _draft(settings, "approved")
    connection = connect(settings.database_url)
    try:
        schedule_id = create_schedule(connection, draft_id, "linkedin", _future())
        connection.execute("UPDATE publish_schedules SET status = 'published' WHERE id = ?", (schedule_id,))
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="only scheduled or retrying"):
        reschedule_draft(settings, schedule_id, _future(60))


def test_worker_rejects_unapproved_draft_and_never_marks_published(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    draft_id = _draft(settings, "pending_approval")
    connection = connect(settings.database_url)
    try:
        schedule_id = create_schedule(connection, draft_id, "linkedin", (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
    finally:
        connection.close()

    calls = []

    def guarded_publish(*args, **kwargs):
        calls.append((args, kwargs))
        raise PublishingError("only approved drafts can be published", retryable=False)

    monkeypatch.setattr("app.scheduler.publish_draft", guarded_publish)
    result = run_due_schedules(settings, limit=5)
    assert result["processed"] == 1
    assert result["published"] == 0
    assert len(calls) == 1

    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT status, last_error FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()
        assert row["status"] == "failed"
        assert "approved" in row["last_error"]
    finally:
        connection.close()
