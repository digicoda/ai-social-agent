import json

from .config import Settings
from .database import connect, list_drafts, update_draft_status

VALID_ACTIONS = {"approved", "rejected"}


def queue(settings: Settings, status: str | None = "pending_approval", limit: int = 25) -> list[dict]:
    connection = connect(settings.database_url)
    try:
        rows = list_drafts(connection, status=status, limit=limit)
        return [
            {
                "id": int(row["id"]),
                "problem_id": int(row["problem_id"]),
                "platform": row["platform"],
                "title": row["title"],
                "body": row["body"],
                "hashtags": json.loads(row["hashtags"]),
                "call_to_action": row["call_to_action"],
                "status": row["status"],
                "generation_confidence": int(row["generation_confidence"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "approved_at": row["approved_at"],
                "rejected_at": row["rejected_at"],
                "rejection_reason": row["rejection_reason"],
            }
            for row in rows
        ]
    finally:
        connection.close()


def set_decision(settings: Settings, draft_id: int, action: str, reason: str = "") -> bool:
    if action not in VALID_ACTIONS:
        raise ValueError("action must be approved or rejected")
    if action == "rejected" and not reason.strip():
        raise ValueError("a rejection reason is required")
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            return False
        if row["status"] != "pending_approval":
            raise ValueError("only pending_approval drafts can be approved or rejected")
        return update_draft_status(connection, draft_id, action, reason.strip())
    finally:
        connection.close()
