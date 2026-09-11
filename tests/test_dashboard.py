from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request

from app.dashboard import dashboard_page


def test_dashboard_module_imports():
    from app.dashboard import dashboard_page, require_dashboard_session
    assert callable(dashboard_page)
    assert callable(require_dashboard_session)


def test_dashboard_template_has_one_auth_tab_group():
    html = Path("app/dashboard/index.html").read_text(encoding="utf-8")
    assert html.count('class="auth-tabs"') == 1


def test_dashboard_response_disables_browser_cache(monkeypatch, tmp_path):
    database = f"sqlite:///{tmp_path / 'dashboard.db'}"
    monkeypatch.setattr(
        "app.dashboard.get_settings",
        lambda: SimpleNamespace(session_secret="session-secret", database_url=database),
    )
    request = Request({"type": "http", "method": "GET", "path": "/dashboard", "headers": [], "session": {}})
    response = dashboard_page(request)
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["pragma"] == "no-cache"
