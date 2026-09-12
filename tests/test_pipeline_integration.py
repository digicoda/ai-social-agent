from datetime import datetime, timedelta, timezone
import json

from app.approval import set_decision
from app.config import Settings
from app.database import connect, save_analysis, save_problem
from app.publish_service import publish_draft
from app.scheduling import schedule_draft
from app.schemas import Problem


def _seed_approved_draft(settings: Settings) -> int:
    connection = connect(settings.database_url)
    problem = Problem(source="test", external_id="integration-1", title="Pipeline integration problem", url="https://example.com/problem")
    assert save_problem(connection, problem)
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    from app.ai import ProblemAnalysis
    save_analysis(
        connection,
        problem_id,
        ProblemAnalysis("pain", "developers", "configuration", "fix configuration", ["hook"], [], 92),
        "approval_queue",
    )
    connection.execute(
        "INSERT INTO content_drafts (problem_id, platform, title, body, hashtags, call_to_action, status, generation_confidence, created_at, updated_at) VALUES (?, 'generic', 'Integration draft', 'Useful body', ?, 'Question?', 'pending_approval', 92, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (problem_id, json.dumps(["python", "automation"])),
    )
    connection.commit()
    draft_id = int(connection.execute("SELECT id FROM content_drafts").fetchone()[0])
    connection.close()
    assert set_decision(settings, draft_id, "approved")
    return draft_id


def test_approval_to_schedule_to_publish_is_idempotent(tmp_path, monkeypatch):
    db = tmp_path / "integration.db"
    settings = Settings(database_url=f"sqlite:///{db}")
    draft_id = _seed_approved_draft(settings)

    class FakePublisher:
        def publish(self, title, body, hashtags, **kwargs):
            from app.publishing import PublishResult
            return PublishResult(provider="test", remote_id="remote-123", url="https://example.com/post")

    monkeypatch.setattr("app.scheduling.get_publisher", lambda settings, provider: FakePublisher())
    monkeypatch.setattr("app.publish_service.get_publisher", lambda settings, provider: FakePublisher())

    scheduled_for = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    scheduled = schedule_draft(settings, draft_id, "test", scheduled_for)
    assert scheduled["draft_id"] == draft_id
    assert scheduled["provider"] == "test"

    result = publish_draft(settings, draft_id, "test")
    assert result["remote_id"] == "remote-123"
    assert result["idempotent"] is False

    second = publish_draft(settings, draft_id, "test")
    assert second["remote_id"] == "remote-123"
    assert second["idempotent"] is True

    connection = connect(settings.database_url)
    status = connection.execute("SELECT status FROM content_drafts WHERE id = ?", (draft_id,)).fetchone()[0]
    attempts = connection.execute("SELECT COUNT(*) FROM publishing_attempts WHERE draft_id = ?", (draft_id,)).fetchone()[0]
    connection.close()
    assert status == "published"
    assert attempts == 1
