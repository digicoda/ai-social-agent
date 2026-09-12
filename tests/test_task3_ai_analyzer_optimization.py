from __future__ import annotations

from datetime import datetime, timezone

from app.ai import ProblemAnalysis
from app.config import Settings
from app.database import connect, save_problem
from app.intelligence import run_intelligence
from app.schemas import Problem


class CountingAnalyzer:
    def __init__(self):
        self.calls = []

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        self.calls.append(problem.title)
        return ProblemAnalysis(
            pain_point=problem.title,
            audience="website owners",
            root_cause="configuration issue",
            solution_angle="Explain the cause and safe fix.",
            hooks=["What changed?"],
            risks=["Verify before changing production."],
            confidence=90,
            category="wordpress" if "wordpress" in problem.title.lower() else "technology",
            intent="bug",
            sentiment="negative",
            severity=80,
            frequency_signal=70,
            trend_signal=65,
            content_gap=75,
            opportunity_score=80,
            trend_label="rising",
            related_topics=["updates", "troubleshooting"],
            recommended_formats=["linkedin"],
            evidence=["Research item contains a concrete problem."],
        )


def _problem(title: str, external_id: str, score: int = 10) -> Problem:
    now = datetime.now(timezone.utc)
    return Problem(
        source="reddit",
        external_id=external_id,
        title=title,
        url=f"https://example.com/{external_id}",
        body=title,
        score=score,
        comments=2,
        discovered_at=now,
    )


def test_second_run_skips_already_analyzed_items(tmp_path):
    db = tmp_path / "agent.db"
    settings = Settings(database_url=f"sqlite:///{db}", gemini_api_key="test")
    connection = connect(settings.database_url)
    save_problem(connection, _problem("WordPress update broke site", "1", 20))
    connection.close()

    analyzer = CountingAnalyzer()
    first = run_intelligence(settings, client_factory=lambda _: analyzer)
    assert first.analyzed == 1
    assert len(analyzer.calls) == 1

    second = run_intelligence(settings, client_factory=lambda _: analyzer)
    assert second.processed == 0
    assert second.analyzed == 0
    assert second.skipped == 1
    assert len(analyzer.calls) == 1


def test_only_new_unanalyzed_research_is_sent_to_ai_and_category_is_saved(tmp_path):
    db = tmp_path / "agent.db"
    settings = Settings(database_url=f"sqlite:///{db}", gemini_api_key="test")
    connection = connect(settings.database_url)
    save_problem(connection, _problem("WordPress update broke site", "1", 20))
    connection.close()

    analyzer = CountingAnalyzer()
    run_intelligence(settings, client_factory=lambda _: analyzer)

    connection = connect(settings.database_url)
    save_problem(connection, _problem("Database query timeout after deployment", "2", 15))
    connection.close()

    analyzer.calls.clear()
    result = run_intelligence(settings, client_factory=lambda _: analyzer)
    assert result.processed == 1
    assert result.analyzed == 1
    assert analyzer.calls == ["Database query timeout after deployment"]

    row = connect(settings.database_url).execute(
        "SELECT category FROM ai_intelligence WHERE problem_id=2"
    ).fetchone()
    assert row["category"] == "technology"
