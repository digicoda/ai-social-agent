import json

from app.ai import ProblemAnalysis
from app.approval import queue, set_decision
from app.config import Settings
from app.content import _generate
from app.database import connect, save_analysis, save_problem
from app.schemas import Problem


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


class FakeClient:
    def post(self, *args, **kwargs):
        return FakeResponse()


def test_generate_parses_structured_draft(tmp_path):
    settings = Settings(gemini_api_key="test-key")
    problem = Problem(source="test", external_id="1", title="Broken deploy", url="https://example.com")
    analysis = ProblemAnalysis("deploy fails", "developers", "bad config", "check config", ["Why"], [], 90)

    draft = _generate(FakeClient(), settings, problem, analysis)

    assert draft.title == "A practical fix"
    assert draft.hashtags == ["webdev", "debugging", "software"]
    assert draft.confidence == 91


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
        "INSERT INTO content_drafts (problem_id, platform, title, body, hashtags, call_to_action, status, generation_confidence, created_at, updated_at) VALUES (?, 'generic', 'Draft', 'Body', '[\\\"tag\\\"]', 'Question?', 'pending_approval', 80, '2026-01-01', '2026-01-01')",
        (problem_id,),
    )
    connection.commit()
    draft_id = connection.execute("SELECT id FROM content_drafts").fetchone()[0]
    connection.close()

    assert len(queue(settings)) == 1
    assert set_decision(settings, draft_id, "rejected", "Needs a clearer example")
    assert queue(settings) == []
    assert queue(settings, status="rejected")[0]["rejection_reason"] == "Needs a clearer example"
