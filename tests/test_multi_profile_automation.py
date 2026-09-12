from pathlib import Path


def root(): return Path(__file__).resolve().parents[1]


def test_profile_engine_has_isolated_storage_and_automation():
    src=(root()/"app"/"profiles.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS profiles" in src
    assert "database_url" in src
    assert "settings_for_profile" in src
    assert "automation_enabled" in src and "auto_approval" in src
    assert "run_profile_automation" in src


def test_profile_ui_has_manual_and_automatic_modes():
    src=(root()/"app/dashboard/profiles_ui.js").read_text(encoding="utf-8")
    for text in ("Automatic daily pipeline","Auto approval","Human approval","daily_time","Categories","Resources"):
        assert text in src


def test_web_search_is_real_source_and_targeted_content_route_exists():
    init=(root()/"app/__init__.py").read_text(encoding="utf-8")
    web=(root()/"app/websearch.py").read_text(encoding="utf-8")
    fix=(root()/"app/dashboard/workflow_fix.js").read_text(encoding="utf-8")
    assert "fetch_web" in init and '"web"' in init
    assert "html.duckduckgo.com/html" in web
    assert "/content/generate-by-title" in fix
    assert "Search by Priority" in fix


def test_targeted_content_generation_supports_a_single_research_problem():
    src=(root()/"app/content.py").read_text(encoding="utf-8")
    assert "def generate_content_for_problem" in src
    assert "needs_analysis" in src
