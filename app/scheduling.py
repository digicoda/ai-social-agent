from __future__ import annotations

from datetime import datetime, timezone

from .config import Settings
from .database import cancel_schedule, connect, create_schedule, list_schedules
from .publishing import PublishingError, get_publisher


def _validate_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("scheduled_for must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError("scheduled_for must include a timezone")
    if parsed <= datetime.now(timezone.utc):
        raise ValueError("scheduled_for must be in the future")
    return parsed.astimezone(timezone.utc).isoformat()


def schedule_draft(settings: Settings, draft_id: int, provider: str, scheduled_for: str, max_attempts: int = 3) -> dict:
    scheduled_for = _validate_time(scheduled_for)
    if max_attempts < 1 or max_attempts > 10:
        raise ValueError("max_attempts must be between 1 and 10")
    get_publisher(settings, provider)
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise ValueError("draft not found")
        if row["status"] != "approved":
            raise ValueError("only approved drafts can be scheduled")
        existing = connection.execute(
            "SELECT id FROM publish_schedules WHERE draft_id = ? AND provider = ? AND status IN ('scheduled', 'retrying', 'running') LIMIT 1",
            (draft_id, provider),
        ).fetchone()
        if existing is not None:
            raise ValueError("draft already has an active schedule for this provider")
        schedule_id = create_schedule(connection, draft_id, provider, scheduled_for, max_attempts)
        return {"schedule_id": schedule_id, "draft_id": draft_id, "provider": provider, "scheduled_for": scheduled_for, "max_attempts": max_attempts}
    finally:
        connection.close()


def cancel_draft_schedule(settings: Settings, schedule_id: int) -> bool:
    return cancel_schedule(settings.database_url, schedule_id)


def schedules(settings: Settings, status: str | None = None, limit: int = 50) -> list[dict]:
    return [dict(row) for row in list_schedules(settings.database_url, status=status, limit=limit)]
