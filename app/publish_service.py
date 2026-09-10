import json

from .config import Settings
from .database import connect, existing_published_attempt, mark_draft_published, save_publishing_attempt
from .publishing import PublishingError, get_publisher


def publish_draft(settings: Settings, draft_id: int, provider_name: str) -> dict:
    connection = connect(settings.database_url)
    try:
        row = connection.execute(
            "SELECT id, title, body, hashtags, status FROM content_drafts WHERE id = ?", (draft_id,)
        ).fetchone()
        if row is None:
            raise PublishingError("draft not found")

        previous = existing_published_attempt(connection, draft_id, provider_name)
        if previous is not None:
            if row["status"] == "approved":
                mark_draft_published(connection, draft_id)
            return {
                "draft_id": draft_id,
                "provider": provider_name,
                "remote_id": previous["remote_id"],
                "url": "",
                "idempotent": True,
            }

        if row["status"] != "approved":
            raise PublishingError("only approved drafts can be published")

        publisher = get_publisher(settings, provider_name)
        try:
            result = publisher.publish(row["title"], row["body"], json.loads(row["hashtags"]))
        except PublishingError as exc:
            save_publishing_attempt(connection, draft_id, provider_name, "failed", error=str(exc))
            raise

        save_publishing_attempt(connection, draft_id, provider_name, "published", remote_id=result.remote_id)
        if not mark_draft_published(connection, draft_id):
            raise PublishingError("draft was published but its local state could not be updated")
        return {"draft_id": draft_id, "provider": result.provider, "remote_id": result.remote_id, "url": result.url, "idempotent": False}
    finally:
        connection.close()
