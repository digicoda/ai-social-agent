from datetime import datetime, timezone

from app.ai import ProblemAnalysis
from app.content import _content_analysis
from app.database import connect, save_analysis, save_problem
from app.schemas import Problem


def test_content_analysis_reads_legacy_analysis(tmp_path):
    db = f"sqlite:///{tmp_path / 'content.db'}"
    connection = connect(db)
    try:
        problem = Problem(source="reddit", external_id="r1", title="Test", url="https://example.com", body="Problem", discovered_at=datetime.now(timezone.utc))
        save_problem(connection, problem)
        row = connection.execute("SELECT id FROM problems WHERE external_id='r1'").fetchone()
        analysis = ProblemAnalysis("pain", "audience", "cause", "angle", ["h1", "h2", "h3"], [])
        save_analysis(connection, int(row["id"]), analysis, "create")
        loaded = _content_analysis(connection, int(row["id"]))
        assert loaded is not None
        assert loaded[0].pain_point == "pain"
        assert loaded[1] == "create"
    finally:
        connection.close()


def test_content_analysis_reads_ai_intelligence(tmp_path):
    db = f"sqlite:///{tmp_path / 'content.db'}"
    connection = connect(db)
    try:
        problem = Problem(source="web", external_id="w1", title="Test", url="https://example.com", body="Problem", discovered_at=datetime.now(timezone.utc))
        save_problem(connection, problem)
        row = connection.execute("SELECT id FROM problems WHERE external_id='w1'").fetchone()
        pid = int(row["id"])
        connection.execute("""CREATE TABLE ai_intelligence (
            problem_id INTEGER PRIMARY KEY, category TEXT, intent TEXT, sentiment TEXT, severity INTEGER,
            frequency_signal INTEGER, trend_signal INTEGER, content_gap INTEGER, opportunity_score INTEGER,
            trend_label TEXT, pain_point TEXT, audience TEXT, root_cause TEXT, solution_angle TEXT,
            hooks TEXT, risks TEXT, related_topics TEXT, recommended_formats TEXT, evidence TEXT,
            confidence INTEGER, duplicate_of INTEGER, cluster_id INTEGER, analyzed_at TEXT
        )""")
        connection.execute("INSERT INTO ai_intelligence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (pid, "seo", "problem", "negative", 70, 60, 50, 40, 75, "rising", "pain", "audience", "cause", "angle", '["h1"]', '[]', '[]', '[]', '[]', 90, None, None, datetime.now(timezone.utc).isoformat()))
        connection.commit()
        loaded = _content_analysis(connection, pid)
        assert loaded is not None
        assert loaded[0].pain_point == "pain"
    finally:
        connection.close()


def test_targeted_generation_auto_analyzes_unanalyzed_item(tmp_path, monkeypatch):
    from app import content_workflow
    from app.config import Settings

    db = f"sqlite:///{tmp_path / 'content.db'}"
    connection = connect(db)
    problem = Problem(source="reddit", external_id="r2", title="Unanalyzed problem", url="https://example.com", body="Useful context", discovered_at=datetime.now(timezone.utc))
    save_problem(connection, problem)
    pid = int(connection.execute("SELECT id FROM problems WHERE external_id='r2'").fetchone()["id"])
    connection.close()

    analysis = ProblemAnalysis("pain", "audience", "cause", "angle", ["h1", "h2", "h3"], [])
    class FakeClient:
        def analyze(self, problem):
            return analysis
    monkeypatch.setattr(content_workflow, "create_ai_client", lambda settings: FakeClient())
    monkeypatch.setattr(content_workflow, "_generate", lambda client, settings, problem, analysis: type("Draft", (), {
        "title": "Generated", "body": "Generated body", "hashtags": ["ai"], "call_to_action": "Thoughts?", "confidence": 90
    })())

    settings = Settings(database_url=db, gemini_api_key="test-key")
    result = content_workflow.generate_for_problem(settings, pid)
    assert result["generated"] == 1
    check = connect(db)
    try:
        assert check.execute("SELECT COUNT(*) AS n FROM problem_analyses WHERE problem_id=?", (pid,)).fetchone()["n"] == 1
        assert check.execute("SELECT COUNT(*) AS n FROM content_drafts WHERE problem_id=?", (pid,)).fetchone()["n"] == 1
    finally:
        check.close()
