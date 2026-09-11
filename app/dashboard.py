from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import authenticate, create_admin, has_users
from .config import get_settings

DASHBOARD_DIR = Path(__file__).with_name("dashboard")


def _configured() -> bool:
    settings = get_settings()
    return bool(settings.session_secret) and has_users(settings.database_url)


def require_dashboard_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="dashboard login required")


def dashboard_login(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if not _configured():
        return False
    if authenticate(settings.database_url, username, password):
        request.session.clear()
        request.session["authenticated"] = True
        request.session["role"] = "admin"
        return True
    return False


def dashboard_signup(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if has_users(settings.database_url):
        return False
    if not create_admin(settings.database_url, username, password):
        return False
    request.session.clear()
    request.session["authenticated"] = True
    request.session["role"] = "admin"
    return True


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")
    return HTMLResponse(html)
