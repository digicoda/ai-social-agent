from app.config import get_settings, reset_active_profile, set_active_profile
from app.database import connect, save_problem
from app.profiles import list_profiles, save_profile
from app.schemas import Problem


def test_profiles_persist_and_use_isolated_databases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = "sqlite:///./data/master.db"
    first = save_profile(master, "Brand A", {"ai_provider": "gemini", "ai_model": "gemini-test"})
    second = save_profile(master, "Brand B", {"ai_provider": "openai", "ai_model": "gpt-test"})
    assert first["database_url"] != second["database_url"]
    a = connect(first["database_url"]); b = connect(second["database_url"])
    try:
        save_problem(a, Problem(source="test", external_id="a", title="A only", url="https://a.example"))
    finally:
        a.close(); b.close()
    a = connect(first["database_url"]); b = connect(second["database_url"])
    try:
        assert a.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 1
        assert b.execute("SELECT COUNT(*) FROM problems").fetchone()[0] == 0
    finally:
        a.close(); b.close()
    assert {p["name"] for p in list_profiles(master)} == {"Brand A", "Brand B"}


def test_active_profile_overlays_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    master = "sqlite:///./data/master.db"
    profile = save_profile(master, "Brand A", {"ai_provider": "openai", "ai_model": "gpt-profile"})
    monkeypatch.setenv("DATABASE_URL", master)
    token = set_active_profile(profile)
    try:
        current = get_settings()
        assert current.database_url == profile["database_url"]
        assert current.ai_provider == "openai"
        assert current.openai_model == "gpt-profile"
    finally:
        reset_active_profile(token)
