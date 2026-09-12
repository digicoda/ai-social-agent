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
