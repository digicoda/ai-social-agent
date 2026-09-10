import json
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.database import connect
from app.publish_service import publish_draft
from app.publishing import PublishResult, Publisher
from app.scheduler import run_due_schedules
from app.scheduling import schedule_draft
import app.publish_service as publish_service
import app.scheduling as scheduling


class FakePublisher(Publisher):
    provider = "fake"

    def publish(self, title, body, hashtags, media_paths=None, media_type="image"):
        return PublishResult(provider="fake", remote_id=f"remote-{media_type}-{len(media_paths or [])}")


def _approved_draft(settings):
    connection = connect(settings.database_url)
    connection.execute("INSERT INTO problems (source, external_id, title, url, discovered_at, fingerprint) VALUES ('t', '1', 'x', 'https://example.com', '2026-01-01', 'fp')")
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    connection.execute("INSERT INTO content_drafts (problem_id, title, body, hashtags, status, created_at, updated_at) VALUES (?, 'x', 'body', ?, 'approved', '2026-01-01', '2026-01-01')", (problem_id, json.dumps(["tag"])))
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()
    return draft_id


def test_schedule_persists_media_and_worker_replays_it(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    image_one = tmp_path / "one.png"
    image_two = tmp_path / "two.png"
    image_one.write_bytes(b"x")
    image_two.write_bytes(b"y")
    monkeypatch.setattr(scheduling, "get_publisher", lambda settings, name: FakePublisher())
    monkeypatch.setattr(publish_service, "get_publisher", lambda settings, name: FakePublisher())

    schedule_id = schedule_draft(
        settings, draft_id, "fake",
        (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
        media_type="multi_image",
        media_paths=[str(image_one), str(image_two)],
    )["schedule_id"]

    connection = connect(settings.database_url)
    row = connection.execute("SELECT media_type, media_paths FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()
    assert row["media_type"] == "multi_image"
    assert json.loads(row["media_paths"]) == [str(image_one), str(image_two)]
    connection.execute("UPDATE publish_schedules SET scheduled_for = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), schedule_id))
    connection.commit()
    connection.close()

    result = run_due_schedules(settings, limit=10)
    assert result["published"] == 1
    connection = connect(settings.database_url)
    attempt = connection.execute("SELECT remote_id FROM publishing_attempts WHERE draft_id = ?", (draft_id,)).fetchone()
    assert attempt["remote_id"] == "remote-multi_image-2"
    connection.close()


def test_media_schedule_rejects_missing_files(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
    draft_id = _approved_draft(settings)
    monkeypatch.setattr(scheduling, "get_publisher", lambda settings, name: FakePublisher())
    try:
        schedule_draft(
            settings, draft_id, "fake",
            (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
            media_type="image", media_paths=[str(tmp_path / "missing.png")],
        )
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected missing media validation")


def test_existing_database_gets_schedule_media_columns(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    connection = connect(database_url)
    connection.execute("CREATE TABLE legacy_marker (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()
    connection = connect(database_url)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(publish_schedules)").fetchall()}
    assert {"media_type", "media_paths"}.issubset(columns)
    connection.close()
