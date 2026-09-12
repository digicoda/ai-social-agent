import json
from datetime import datetime, timezone

from .config import Settings
from .database import connect, list_drafts

VALID_ACTIONS = {"approved", "rejected"}


def _ensure_audit_table(connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS approval_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER NOT NULL, from_status TEXT NOT NULL,
        to_status TEXT NOT NULL, action TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
        FOREIGN KEY(draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE
    )""")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_approval_audit_draft ON approval_audit(draft_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_approval_audit_created ON approval_audit(created_at)")
    connection.commit()


def queue(settings: Settings, status: str | None = "pending_approval", limit: int = 25) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    connection = connect(settings.database_url)
    try:
        _ensure_audit_table(connection)
        rows = list_drafts(connection, status=status, limit=limit)
        return [{"id": int(row["id"]), "problem_id": int(row["problem_id"]), "platform": row["platform"], "title": row["title"], "body": row["body"], "hashtags": json.loads(row["hashtags"]), "call_to_action": row["call_to_action"], "status": row["status"], "generation_confidence": int(row["generation_confidence"]), "created_at": row["created_at"], "updated_at": row["updated_at"], "approved_at": row["approved_at"], "rejected_at": row["rejected_at"], "rejection_reason": row["rejection_reason"]} for row in rows]
    finally:
        connection.close()


def set_decision(settings: Settings, draft_id: int, action: str, reason: str = "") -> bool:
    if action not in VALID_ACTIONS:
        raise ValueError("action must be approved or rejected")
    reason = reason.strip()
    if action == "rejected" and not reason:
        raise ValueError("a rejection reason is required")
    connection = connect(settings.database_url)
    try:
        _ensure_audit_table(connection)
        row = connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            return False
        from_status = str(row["status"])
        if from_status != "pending_approval":
            raise ValueError("only pending_approval drafts can be approved or rejected")
        now = datetime.now(timezone.utc).isoformat()
        timestamp_column = "approved_at" if action == "approved" else "rejected_at"
        cursor = connection.execute(f"UPDATE content_drafts SET status = ?, updated_at = ?, {timestamp_column} = ?, rejection_reason = ? WHERE id = ? AND status = 'pending_approval'", (action, now, now, reason, draft_id))
        if cursor.rowcount != 1:
            connection.rollback()
            raise ValueError("only pending_approval drafts can be approved or rejected")
        connection.execute("INSERT INTO approval_audit (draft_id, from_status, to_status, action, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)", (draft_id, from_status, action, action, reason, now))
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def history(settings: Settings, draft_id: int, limit: int = 25) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    connection = connect(settings.database_url)
    try:
        _ensure_audit_table(connection)
        rows = connection.execute("SELECT id, draft_id, from_status, to_status, action, reason, created_at FROM approval_audit WHERE draft_id = ? ORDER BY created_at DESC, id DESC LIMIT ?", (draft_id, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
