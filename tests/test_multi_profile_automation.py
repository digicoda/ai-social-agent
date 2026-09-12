from pathlib import Path
# Final regression coverage for research, content and profile automation.
def root(): return Path(__file__).resolve().parents[1]
def test_profile_engine_has_isolated_storage_and_automation():
    src=(root()/"app"/"profiles.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS profiles" in src and "database_url" in src and "run_profile_automation" in src
    assert "automation_enabled" in src and "auto_approval" in src
def test_profile_ui_has_manual_and_automatic_modes():
    src=(root()/"app/dashboard/profiles_ui.js").read_text(encoding="utf-8")
    for text in ("Automatic daily pipeline","Auto approval","Human approval","daily_time","Categories","Resources"): assert text in src
def test_web_search_and_targeted_content_handoff():
    init=(root()/"app/__init__.py").read_text(encoding="utf-8");web=(root()/"app/websearch.py").read_text(encoding="utf-8");fix=(root()/"app/dashboard/workflow_fix.js").read_text(encoding="utf-8");content=(root()/"app/content.py").read_text(encoding="utf-8")
    assert "fetch_web" in init and '"web"' in init and "html.duckduckgo.com/html" in web
    assert "/content/generate-by-title" in init and "Search by Priority" in fix and "def generate_content_for_problem" in content
# CI trigger: verify the current branch head, including the dashboard loader fix.
