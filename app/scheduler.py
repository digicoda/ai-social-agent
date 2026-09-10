from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .config import Settings
from .database import claim_due_schedule, complete_schedule, fail_schedule, list_due_schedules
from .publish_service import publish_draft
from .publishing import PublishingError


def _retry_time(attempt: int, base_seconds: int, max_seconds: int) -> str:
    delay = min(max_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    return (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()


def run_due_schedules(settings: Settings, limit: int = 10) -> dict[str, int]:
    processed = published = retried = failed = 0
    for schedule in list_due_schedules(settings.database_url, limit=limit):
        schedule_id = int(schedule["id"])
        if not claim_due_schedule(settings.database_url, schedule_id):
            continue
        processed += 1
        try:
            media_type = str(schedule["media_type"] or "none")
            media_paths = json.loads(schedule["media_paths"] or "[]")
            if not isinstance(media_paths, list) or any(not isinstance(path, str) for path in media_paths):
                raise PublishingError("scheduled media_paths is invalid", retryable=False)
            publish_draft(
                settings,
                int(schedule["draft_id"]),
                str(schedule["provider"]),
                media_paths=media_paths or None,
                media_type="image" if media_type == "none" else media_type,
            )
            complete_schedule(settings.database_url, schedule_id)
            published += 1
        except PublishingError as exc:
            attempts = int(schedule["attempts"]) + 1
            max_attempts = int(schedule["max_attempts"])
            if exc.retryable and attempts < max_attempts:
                retry_at = _retry_time(attempts, settings.retry_base_seconds, settings.retry_max_seconds)
                fail_schedule(settings.database_url, schedule_id, str(exc), retry_at, attempts, "retrying")
                retried += 1
            else:
                fail_schedule(settings.database_url, schedule_id, str(exc), None, attempts, "failed")
                failed += 1
        except Exception as exc:
            attempts = int(schedule["attempts"]) + 1
            max_attempts = int(schedule["max_attempts"])
            error = f"unexpected worker error: {exc}"
            if attempts < max_attempts:
                retry_at = _retry_time(attempts, settings.retry_base_seconds, settings.retry_max_seconds)
                fail_schedule(settings.database_url, schedule_id, error, retry_at, attempts, "retrying")
                retried += 1
            else:
                fail_schedule(settings.database_url, schedule_id, error, None, attempts, "failed")
                failed += 1
    return {"processed": processed, "published": published, "retried": retried, "failed": failed}
