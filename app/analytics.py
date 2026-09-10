from __future__ import annotations

from .database import connect


def publishing_history(database_url: str, limit: int = 50, provider: str | None = None) -> list[dict]:
    connection = connect(database_url)
    try:
        if provider:
            rows = connection.execute(
                """SELECT pa.*, cd.title FROM publishing_attempts pa
                   JOIN content_drafts cd ON cd.id = pa.draft_id
                   WHERE pa.provider = ? ORDER BY pa.attempted_at DESC LIMIT ?""",
                (provider, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT pa.*, cd.title FROM publishing_attempts pa
                   JOIN content_drafts cd ON cd.id = pa.draft_id
                   ORDER BY pa.attempted_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def publishing_stats(database_url: str) -> dict:
    connection = connect(database_url)
    try:
        attempts = connection.execute(
            "SELECT COUNT(*) AS total, SUM(status = 'published') AS published, SUM(status = 'failed') AS failed FROM publishing_attempts"
        ).fetchone()
        schedules = connection.execute(
            "SELECT status, COUNT(*) AS count FROM publish_schedules GROUP BY status"
        ).fetchall()
        drafts = connection.execute(
            "SELECT status, COUNT(*) AS count FROM content_drafts GROUP BY status"
        ).fetchall()
        return {
            "publishing_attempts": {
                "total": int(attempts["total"] or 0),
                "published": int(attempts["published"] or 0),
                "failed": int(attempts["failed"] or 0),
            },
            "schedules": {row["status"]: int(row["count"]) for row in schedules},
            "drafts": {row["status"]: int(row["count"]) for row in drafts},
        }
    finally:
        connection.close()
