from pathlib import Path


def test_dashboard_has_eight_pages_and_separated_workspace():
    root = Path(__file__).resolve().parents[1]
    html = (root / "app" / "dashboard" / "index.html").read_text(encoding="utf-8")
    for view in ("overview", "research", "content", "approval", "calendar", "analytics", "integrations", "settings"):
        assert f'data-view="{view}"' in html


def test_dashboard_uses_modern_dark_sidebar_and_compact_grid():
    root = Path(__file__).resolve().parents[1]
    html = (root / "app" / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert "--side:#111216" in html
    assert "--purple:#7c5cff" in html
    assert "grid4" in html


def test_full_ui_covers_workflow_and_dynamic_provider_models():
    root = Path(__file__).resolve().parents[1]
    js = (root / "app" / "dashboard" / "full_ui.js").read_text(encoding="utf-8")
    for label in ("Research Intelligence", "Content Workspace", "Content Approval", "Publishing Calendar", "Analytics", "Integrations", "AI Providers"):
        assert label in js
    for endpoint in ("/research/search", "/intelligence/run", "/content/generate", "/approval/", "/schedule/", "/publishing/stats", "/publishing/history", "/system/settings", "/system/test/"):
        assert endpoint in js
    assert "Load available models" in js
    assert "repeat(2,minmax(0,1fr))" in js


def test_dashboard_owns_the_new_ui_shell_without_legacy_search_injection():
    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "app" / "dashboard.py").read_text(encoding="utf-8")
    assert '"full_ui.js"' in dashboard
    assert '"search_ui.js"' not in dashboard
