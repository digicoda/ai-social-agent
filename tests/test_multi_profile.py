from pathlib import Path

from app.config import Settings, get_settings, reset_active_profile, set_active_profile
from app.database import connect, save_problem
from app.profiles import get_profile, list_profiles, save_profile
from app.schemas import Problem


def test_profiles_persist_and_use_isolated_databases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = "sqlite:///./data/master.db"
    first = save_profile(master, "Brand A", {"ai_provider": "gemini", "ai_model": "gemini-test"})
    second = save_profile(master, "Brand B", {"ai_provider": "openai", "ai_model": "gpt-test"})
    assert first["database_url"] != second["database_url"]
    a = connect(first["database_url"])
    b = connect(second["database_url"])
    save_problem(a, Problem(source="test", external_id="a", title="A only", url="https://a.example"))
    a.close(); b.close()
    assert connect(first["database_url"]).execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 1
    assert connect(second["database_url"]).execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 0
    assert {p["name"] for p in list_profiles(master)} == {"Brand A", "Brand B"}


def test_active_profile_overlays_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = "sqlite:///./data/master.db"
    profile = save_profile(master, "Brand A", {"ai_provider": "openai", "ai_model": "gpt-profile"})
    base = Settings(database_url=master, ai_provider="gemini", gemini_model="gemini-base")
    token = set_active_profile(profile)
    try:
        # get_settings reads environment-backed base settings, so assert the profile's
        # public overlay through a temporary env configuration instead of credentials.
        monkeypatch.setenv("DATABASE_URL", master)
        current = get_settings()
        assert current.database_url == profile["database_url"]
        assert current.ai_provider == "openai"
        assert current.openai_model == "gpt-profile"
    finally:
        reset_active_profile(token)
