from datetime import datetime, timezone

from app.ai import ProblemAnalysis
from app.config import Settings
from app.content import ContentDraft
from app.database import connect
from app.intelligence import run_intelligence
from app.research import search as research
from app.research.search import search_research
from app.schemas import Problem


def test_search_to_ai_to_content_pipeline(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'pipeline.db'}", gemini_api_key="test-key")

    problem = Problem(
        source="github",
        external_id="search-ai-content-1",
        title="Website update breaks deployment automation",
        url="https://example.com/issues/1",
        body="A recent update broke the deployment workflow and now developers see an error.",
        tags=["deployment", "automation"],
        score=18,
        comments=9,
        published_at=datetime.now(timezone.utc),
    )

    # Search stage: use the real filtering/classification/scoring pipeline with
    # deterministic source data instead of making external network calls.
    monkeypatch.setattr(research, "fetch_github_issues", lambda **kwargs: [problem])
    monkeypatch.setattr(research, "fetch_reddit", lambda **kwargs: [])
    monkeypatch.setattr(research, "fetch_stackoverflow", lambda **kwargs: [])
    monkeypatch.setattr(research, "fetch_rss", lambda *args, **kwargs: [])

    search_result = search_research(
        settings,
        query="deployment automation",
        sources=["github"],
        category="development",
        intent="bug",
        time_range="30d",
        limit=20,
    )
    assert search_result["total"] == 1
    assert search_result["items"][0]["external_id"] == "search-ai-content-1"
    assert search_result["items"][0]["intent"] == "bug"

    # AI stage: run the real persistence, scoring, deduplication and clustering
    # pipeline with a deterministic client implementation.
    class FakeAIClient:
        def analyze(self, problem):
            return ProblemAnalysis(
                pain_point="Updates can unexpectedly break deployment automation.",
                audience="Developers and website operators",
                root_cause="A breaking change was introduced without validating the deployment workflow.",
                solution_angle="Show a safe update-and-rollback checklist for deployment workflows.",
                hooks=["What should you check before applying an update?"],
                risks=["Skipping a rollback plan can increase downtime."],
                confidence=91,
                category="development",
                intent="bug",
                sentiment="negative",
                severity=82,
                frequency_signal=70,
                trend_signal=68,
                content_gap=80,
                related_topics=["deployment", "rollback", "automation"],
                recommended_formats=["carousel", "how_to"],
                evidence=["https://example.com/issues/1"],
                trend_label="rising",
            )

    intelligence_result = run_intelligence(settings, limit=20, client_factory=lambda _settings: FakeAIClient())
    assert intelligence_result.processed == 1
    assert intelligence_result.analyzed == 1
    assert intelligence_result.failed == 0
    assert intelligence_result.clusters == 1
    assert intelligence_result.opportunities == 1

    # Content stage: exercise the real draft persistence path while replacing
    # only the external Gemini generation call with deterministic content.
    monkeypatch.setattr(
        "app.content._generate",
        lambda client, settings, problem, analysis: ContentDraft(
            title="How to make deployment updates safer",
            body="Use a pre-update backup, validate the deployment workflow, and keep a tested rollback path.",
            hashtags=["deployment", "automation", "devops"],
            call_to_action="What is your safest update practice?",
            confidence=94,
        ),
    )

    from app.content import generate_content

    generated = generate_content(settings, limit=20)
    assert generated == {"generated": 1, "skipped": 0, "failed": 0}

    connection = connect(settings.database_url)
    draft = connection.execute(
        "SELECT title, body, status, generation_confidence FROM content_drafts LIMIT 1"
    ).fetchone()
    connection.close()

    assert draft["title"] == "How to make deployment updates safer"
    assert draft["status"] == "pending_approval"
    assert draft["generation_confidence"] == 94
