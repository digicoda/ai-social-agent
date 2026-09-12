from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .database import cancel_schedule, connect, create_schedule, list_schedules
from .publishing import PublishingError, get_publisher

SUPPORTED_MEDIA = {"none", "image", "document", "video", "multi_image"}
ACTIVE_SCHEDULE_STATUSES = {"scheduled", "retrying", "running"}


def _validate_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("scheduled_for must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError("scheduled_for must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    if parsed <= datetime.now(timezone.utc):
        raise ValueError("scheduled_for must be in the future")
    return parsed.isoformat()


def _validate_media(media_type: str, media_paths: list[str] | None) -> list[str]:
    paths = media_paths or []
    if media_type not in SUPPORTED_MEDIA:
        raise ValueError(f"unsupported media type: {media_type}")
    if media_type == "none":
        if paths:
            raise ValueError("media_paths cannot be supplied when media_type is none")
        return []
    expected = 2 <= len(paths) <= 20 if media_type == "multi_image" else len(paths) == 1
    if not expected:
        raise ValueError("multi_image schedules require 2-20 files; other media schedules require exactly 1 file")
    for path in paths:
        if not Path(path).is_file():
            raise ValueError(f"media file not found: {path}")
    return paths


def _draft_status(connection, draft_id: int) -> str:
    row = connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
    if row is None:
        raise ValueError("draft not found")
    return str(row["status"])


def schedule_draft(settings: Settings, draft_id: int, provider: str, scheduled_for: str, max_attempts: int = 3, media_type: str = "none", media_paths: list[str] | None = None) -> dict:
    scheduled_for = _validate_time(scheduled_for)
    if max_attempts < 1 or max_attempts > 10:
        raise ValueError("max_attempts must be between 1 and 10")
    paths = _validate_media(media_type, media_paths)
    get_publisher(settings, provider)
    connection = connect(settings.database_url)
    try:
        status = _draft_status(connection, draft_id)
        if status != "approved":
            raise ValueError("only approved drafts can be scheduled")
        existing = connection.execute("SELECT id FROM publish_schedules WHERE draft_id = ? AND provider = ? AND status IN ('scheduled', 'retrying', 'running') LIMIT 1", (draft_id, provider)).fetchone()
        if existing is not None:
            raise ValueError("draft already has an active schedule for this provider")
        schedule_id = create_schedule(connection, draft_id, provider, scheduled_for, max_attempts, media_type, paths)
        return {"schedule_id": schedule_id, "draft_id": draft_id, "provider": provider, "scheduled_for": scheduled_for, "max_attempts": max_attempts, "media_type": media_type, "media_paths": paths}
    finally:
        connection.close()


def reschedule_draft(settings: Settings, schedule_id: int, scheduled_for: str) -> dict:
    """Move an active schedule without changing its provider/media configuration."""
    scheduled_for = _validate_time(scheduled_for)
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT * FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()
        if row is None:
            raise ValueError("schedule not found")
        if str(row["status"]) not in {"scheduled", "retrying"}:
            raise ValueError("only scheduled or retrying jobs can be rescheduled")
        status = _draft_status(connection, int(row["draft_id"]))
        if status != "approved":
            raise ValueError("only schedules for approved drafts can be rescheduled")
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE publish_schedules SET scheduled_for = ?, status = 'scheduled', last_error = '', updated_at = ? WHERE id = ? AND status IN ('scheduled', 'retrying')",
            (scheduled_for, now, schedule_id),
        )
        connection.commit()
        if cursor.rowcount != 1:
            raise ValueError("schedule is no longer active")
        return {"schedule_id": schedule_id, "draft_id": int(row["draft_id"]), "provider": str(row["provider"]), "scheduled_for": scheduled_for, "status": "scheduled"}
    finally:
        connection.close()


def cancel_draft_schedule(settings: Settings, schedule_id: int) -> bool:
    return cancel_schedule(settings.database_url, schedule_id)


def schedules(settings: Settings, status: str | None = None, limit: int = 50) -> list[dict]:
    return [dict(row) for row in list_schedules(settings.database_url, status=status, limit=limit)]
