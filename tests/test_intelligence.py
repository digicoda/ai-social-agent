from __future__ import annotations

from datetime import datetime, timezone

from app.ai import ProblemAnalysis
from app.config import Settings
from app.database import connect, save_problem
from app.intelligence import list_clusters, list_intelligence, opportunity_score, run_intelligence, semantic_similarity
from app.schemas import Problem


class FakeGemini:
    def analyze(self, problem: Problem) -> ProblemAnalysis:
        title = problem.title.lower()
        category = "wordpress" if "wordpress" in title else "technology"
        intent = "bug" if "error" in title or "broken" in title else "problem"
        return ProblemAnalysis(
            pain_point=problem.title,
            audience="website owners",
            root_cause="configuration or implementation issue",
            solution_angle="Explain the cause, checks, and safe fixes.",
            hooks=["What changed?", "Here is the cause", "Fix it safely"],
            risks=["Avoid unsupported fixes"],
            confidence=91,
            category=category,
            intent=intent,
            sentiment="negative",
            severity=82,
            frequency_signal=70,
            trend_signal=65,
            content_gap=78,
            opportunity_score=80,
            trend_label="rising",
            related_topics=["site errors", "updates", "troubleshooting"],
            recommended_formats=["linkedin", "carousel"],
            evidence=["Source title describes a concrete failure."],
        )


def test_semantic_similarity_and_opportunity_score():
    assert semantic_similarity("WordPress update broke site", "WordPress update breaks website") > 0.45
    problem = Problem(source="reddit", external_id="1", title="Broken site", url="https://example.com", score=20, comments=10)
    analysis = FakeGemini().analyze(problem)
    assert 0 <= opportunity_score(problem, analysis, 4) <= 100


def test_complete_pipeline_persists_analysis_clusters_and_duplicates(tmp_path):
    db = tmp_path / "agent.db"
    settings = Settings(database_url=f"sqlite:///{db}", gemini_api_key="test")
    connection = connect(settings.database_url)
    now = datetime.now(timezone.utc)
    save_problem(connection, Problem(source="reddit", external_id="1", title="WordPress update broke site", url="https://example.com/1", body="Users report the site breaks after an update.", score=25, comments=12, discovered_at=now))
    save_problem(connection, Problem(source="github", external_id="2", title="WordPress update breaks website", url="https://example.com/2", body="Issue describes a broken site after update.", score=20, comments=8, discovered_at=now))
    save_problem(connection, Problem(source="stackoverflow", external_id="3", title="How to optimize a database query", url="https://example.com/3", body="A slow query needs troubleshooting.", score=8, comments=2, discovered_at=now))
    connection.close()

    result = run_intelligence(settings, client_factory=lambda _: FakeGemini())
    assert result.processed == 3
    assert result.analyzed == 2
    assert result.duplicates == 1
    assert result.clusters >= 1
    assert result.assignments >= 2
    assert result.failed == 0

    items = list_intelligence(settings)
    assert len(items) == 3
    duplicate = next(item for item in items if item["duplicate_of"] is not None)
    assert duplicate["duplicate_of"] == 1
    assert all(0 <= item["opportunity_score"] <= 100 for item in items)
    clusters = list_clusters(settings)
    assert clusters
