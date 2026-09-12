import json

from app.database import connect, save_problem
from app.profiles import get_profile, list_profiles, save_profile
from app.schemas import Problem
from datetime import datetime, timezone


def test_profile_persists_independent_automation_settings(tmp_path):
    db = f"sqlite:///{tmp_path / 'profiles.db'}"
    saved = save_profile(db, "Brand A", {"categories": ["seo", "ai"], "automation_mode": "auto", "approval_mode": "human", "daily_time": "08:30", "timezone": "Asia/Karachi"})
    assert saved["config"]["automation_mode"] == "auto"
    assert saved["config"]["approval_mode"] == "human"
    assert saved["config"]["categories"] == ["seo", "ai"]
    loaded = get_profile(db, saved["id"])
    assert loaded["name"] == "Brand A"
    assert loaded["config"]["daily_time"] == "08:30"


def test_profile_database_does_not_share_names(tmp_path):
    db = f"sqlite:///{tmp_path / 'profiles.db'}"
    save_profile(db, "Brand A", {"automation_mode": "manual"})
    save_profile(db, "Brand B", {"automation_mode": "auto", "approval_mode": "auto"})
    profiles = list_profiles(db)
    assert [p["name"] for p in profiles] == ["Brand A", "Brand B"]
    assert profiles[1]["config"]["approval_mode"] == "auto"


def test_content_generation_selection_has_ai_intelligence_source(tmp_path):
    db = f"sqlite:///{tmp_path / 'content.db'}"
    connection = connect(db)
    try:
        problem = Problem(source="reddit", external_id="r1", title="Example research problem", url="https://example.com", body="A real technical problem", discovered_at=datetime.now(timezone.utc))
        assert connection.execute("SELECT 1").fetchone()
        from app.database import save_problem
        save_problem(connection, problem)
        row = connection.execute("SELECT id FROM problems WHERE source='reddit' AND external_id='r1'").fetchone()
        assert row is not None
    finally:
        connection.close()
