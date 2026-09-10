import json

from app.ai import ProblemAnalysis
from app.approval import queue, set_decision
from app.config import Settings
from app.database import connect, save_analysis, save_problem
from app.models import Problem


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "title": "A practical fix",
                                        "body": "Here is a concise educational post about the issue and how to approach it.",
                                        "hashtags": ["webdev", "debugging", "software"],
                                        "call_to_action": "What would you check first?",
                                        "confidence": 91,
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }


def test_generate_parses_structured_draft(monkeypatch, tmp_path):
    from app import content

    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", gemini_api_key="key")
    connection = connect(settings.database_url)
    problem = Problem(source="test", external_id="1", title="Example", url="https://example.com")
    assert save_problem(connection, problem)
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    save_analysis(
        connection,
        problem_id,
        ProblemAnalysis("pain", "audience", "cause", "angle", ["h1", "h2", "h3"], [], 90),
        "auto_publish_candidate",
    )
    connection.close()

    monkeypatch.setattr(content.httpx, "post", lambda *args, **kwargs: FakeResponse())
    result = content.generate_content(settings, limit=1)
    assert result[0]["title"] == "A practical fix"
    assert result[0]["confidence"] == 91


def test_approval_queue_and_rejection(tmp_path):
    db = tmp_path / "test.db"
    settings = Settings(database_url=f"sqlite:///{db}")
    connection = connect(settings.database_url)
    problem = Problem(source="test", external_id="1", title="Approval test", url="https://example.com")
    assert save_problem(connection, problem)
    problem_id = connection.execute("SELECT id FROM problems").fetchone()[0]
    save_analysis(
        connection,
        problem_id,
        ProblemAnalysis("pain", "audience", "cause", "angle", ["h1", "h2", "h3"], [], 80),
        "approval_queue",
    )
    connection.execute(
        "INSERT INTO content_drafts (problem_id, platform, title, body, hashtags, call_to_action, status, generation_confidence, created_at, updated_at) VALUES (?, 'generic', 'Draft', 'Body', ?, 'Question?', 'pending_approval', 80, '2026-01-01', '2026-01-01')",
        (problem_id, json.dumps(["tag"])),
    )
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()

    assert len(queue(settings)) == 1
    assert set_decision(settings, draft_id, "rejected", "Needs a clearer example")
    assert queue(settings) == []
    rejected = queue(settings, status="rejected")[0]
    assert rejected["status"] == "rejected"
    assert rejected["rejection_reason"] == "Needs a clearer example"
