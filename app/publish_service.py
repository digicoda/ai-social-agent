import json

from .config import Settings
from .database import connect, existing_published_attempt, save_publishing_attempt
from .publish_lock import claim_draft_for_publish, mark_draft_published_from_claim, release_draft_publish_claim
from .publishing import PublishingError, get_publisher


def publish_draft(settings: Settings, draft_id: int, provider_name: str, media_paths: list[str] | None = None) -> dict:
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT id, title, body, hashtags, status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise PublishingError("draft not found", retryable=False)
        previous = existing_published_attempt(connection, draft_id, provider_name)
        if previous is not None:
            if row["status"] in {"approved", "publishing"}:
                connection.execute("UPDATE content_drafts SET status = 'published', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (draft_id,))
                connection.commit()
            return {"draft_id": draft_id, "provider": provider_name, "remote_id": previous["remote_id"], "url": "", "idempotent": True}
    finally:
        connection.close()

    claim_draft_for_publish(settings.database_url, draft_id)
    connection = connect(settings.database_url)
    try:
        row = connection.execute("SELECT id, title, body, hashtags FROM content_drafts WHERE id = ? AND status = 'publishing'", (draft_id,)).fetchone()
        if row is None:
            raise PublishingError("draft publishing claim was lost", retryable=True)
        try:
            publisher = get_publisher(settings, provider_name)
            result = publisher.publish(row["title"], row["body"], json.loads(row["hashtags"]), media_paths=media_paths)
        except PublishingError as exc:
            save_publishing_attempt(connection, draft_id, provider_name, "failed", error=str(exc))
            raise
        except Exception as exc:
            save_publishing_attempt(connection, draft_id, provider_name, "failed", error=str(exc))
            raise PublishingError(f"unexpected publishing error: {exc}", retryable=True) from exc
        save_publishing_attempt(connection, draft_id, provider_name, "published", remote_id=result.remote_id)
    except Exception:
        release_draft_publish_claim(settings.database_url, draft_id)
        raise
    finally:
        connection.close()

    if not mark_draft_published_from_claim(settings.database_url, draft_id):
        raise PublishingError("draft was published but its local state could not be updated", retryable=True)
    return {"draft_id": draft_id, "provider": result.provider, "remote_id": result.remote_id, "url": result.url, "idempotent": False}
