import json

from app import profile_automation
from app.config import Settings
from app.database import connect
from app.profile_automation import run_profile_cycle


def _settings(db_url):
    return Settings(database_url=db_url, ai_provider="gemini", app_env="test")


def test_automatic_pipeline_runs_stages_in_order_without_bypassing_human_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_url = "sqlite:///./data/master.db"
    settings = _settings(db_url)
    profile = {
        "id": 7,
        "name": "Tech Brand",
        "database_url": db_url,
        "config": {
            "categories": ["ai"],
            "sources": ["web", "github", "reddit"],
            "query": "agent automation",
            "research_limit": 5,
            "content_limit": 2,
            "approval_mode": "human",
            "auto_publish": False,
            "publish_provider": "linkedin",
            "daily_time": "09:00",
            "timezone": "UTC",
            "ai_provider": "gemini",
            "ai_model": "gemini-2.5-flash",
            "time_range": "7d",
        },
    }
    calls = []

    def research(*args, **kwargs):
        calls.append("research")
        assert kwargs["category"] == "ai"
        assert kwargs["sources"] == ["web", "github", "reddit"]
        return {"items": [], "failed_sources": []}

    monkeypatch.setattr(profile_automation, "search_research", research)
    monkeypatch.setattr(profile_automation, "run_intelligence", lambda *a, **k: calls.append("ai") or type("R", (), {"processed": 0, "analyzed": 0, "duplicates": 0, "failed": 0})())
    monkeypatch.setattr(profile_automation, "_generate_profile_drafts", lambda *a, **k: calls.append("content") or {"generated": 0, "skipped": 0, "failed": 0})

    result = run_profile_cycle(settings, profile)

    assert calls == ["research", "content"]
    assert result["status"] == "completed"
    assert result["research_items"] == 0
    assert result["generated"] == 0
    assert result["scheduled"] == 0

    db = connect(db_url)
    try:
        row = db.execute("SELECT status, stages FROM pipeline_runs WHERE id=?", (result["pipeline_run_id"],)).fetchone()
        assert row["status"] == "completed"
        stages = json.loads(row["stages"])
        assert list(stages) == ["research", "ai_analysis", "content_generation", "approval", "scheduling", "publishing"]
        assert stages["research"]["categories"] == ["ai"]
        assert stages["research"]["sources"] == ["web", "github", "reddit"]
        assert stages["ai_analysis"]["status"] == "skipped"
        assert stages["approval"]["status"] == "pending_human"
        assert stages["scheduling"]["status"] == "disabled"
        assert stages["publishing"]["status"] == "waiting_for_schedule"
    finally:
        db.close()


def test_automatic_pipeline_never_schedules_when_auto_publish_is_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_url = "sqlite:///./data/master.db"
    settings = _settings(db_url)
    profile = {
        "id": 8,
        "name": "Manual Approval Brand",
        "database_url": db_url,
        "config": {
            "categories": ["technology"],
            "sources": ["rss"],
            "approval_mode": "auto",
            "auto_publish": False,
            "daily_time": "09:00",
            "timezone": "UTC",
            "ai_provider": "gemini",
            "ai_model": "gemini-2.5-flash",
        },
    }
    monkeypatch.setattr(profile_automation, "search_research", lambda *a, **k: {"items": [], "failed_sources": []})
    monkeypatch.setattr(profile_automation, "run_intelligence", lambda *a, **k: type("R", (), {"processed": 0, "analyzed": 0, "duplicates": 0, "failed": 0})())
    monkeypatch.setattr(profile_automation, "_generate_profile_drafts", lambda *a, **k: {"generated": 0, "skipped": 0, "failed": 0})
    schedule_calls = []
    monkeypatch.setattr(profile_automation, "schedule_draft", lambda *a, **k: schedule_calls.append((a, k)))

    result = run_profile_cycle(settings, profile)

    assert schedule_calls == []
    assert result["scheduled"] == 0
