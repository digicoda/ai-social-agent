from __future__ import annotations

from datetime import datetime, timezone

from .database import connect
from .publishing import PublishingError


def claim_draft_for_publish(database_url: str, draft_id: int) -> None:
    """Atomically reserve an approved draft for one publisher process."""
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE content_drafts SET status = 'publishing', updated_at = ? "
            "WHERE id = ? AND status = 'approved'",
            (now, draft_id),
        )
        connection.commit()
        if cursor.rowcount != 1:
            row = connection.execute(
                "SELECT status FROM content_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
            if row is None:
                raise PublishingError("draft not found", retryable=False)
            if row["status"] == "publishing":
                raise PublishingError("draft is already being published", retryable=False)
            raise PublishingError("only approved drafts can be published", retryable=False)
    finally:
        connection.close()


def release_draft_publish_claim(database_url: str, draft_id: int) -> None:
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "UPDATE content_drafts SET status = 'approved', updated_at = ? "
            "WHERE id = ? AND status = 'publishing'",
            (now, draft_id),
        )
        connection.commit()
    finally:
        connection.close()


def mark_draft_published_from_claim(database_url: str, draft_id: int) -> bool:
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE content_drafts SET status = 'published', updated_at = ? "
            "WHERE id = ? AND status = 'publishing'",
            (now, draft_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()
