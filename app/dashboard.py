from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import get_settings

DASHBOARD_DIR = Path(__file__).with_name("dashboard")


def _configured() -> bool:
    settings = get_settings()
    return bool(settings.admin_username and settings.admin_password and settings.session_secret)


def require_dashboard_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="dashboard login required")


def dashboard_login(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if not _configured():
        return False
    valid_user = secrets.compare_digest(username, settings.admin_username)
    valid_password = secrets.compare_digest(password, settings.admin_password)
    if valid_user and valid_password:
        request.session.clear()
        request.session["authenticated"] = True
        return True
    return False


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    path = DASHBOARD_DIR / "index.html"
    html = path.read_text(encoding="utf-8")
    html = html.replace("__AUTH_CONFIGURED__", "true" if _configured() else "false")
    html = html.replace("__AUTHENTICATED__", "true" if request.session.get("authenticated") else "false")
    return HTMLResponse(html)
