from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import authenticate, create_admin, has_users
from .config import get_settings

DASHBOARD_DIR = Path(__file__).with_name("dashboard")


def _configured() -> bool:
    return bool(get_settings().session_secret)


def require_dashboard_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="dashboard login required")


def dashboard_login(request: Request, username: str, password: str) -> bool:
    settings = get_settings()
    if not _configured():
        return False
    if not has_users(settings.database_url):
        if not create_admin(settings.database_url, username, password):
            return False
    elif not authenticate(settings.database_url, username, password):
        return False
    request.session.clear()
    request.session["authenticated"] = True
    request.session["role"] = "admin"
    return True


def dashboard_signup(request: Request, username: str, password: str) -> bool:
    if has_users(get_settings().database_url):
        return False
    return dashboard_login(request, username, password)


def dashboard_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/dashboard", status_code=303)


def dashboard_page(request: Request) -> HTMLResponse:
    html = (DASHBOARD_DIR / "index.html").read_text(encoding="utf-8")
    settings = get_settings()
    account_exists = has_users(settings.database_url)
    for key, value in {"__AUTH_CONFIGURED__": "true" if _configured() else "false", "__HAS_ACCOUNT__": "true" if account_exists else "false", "__AUTHENTICATED__": "true" if request.session.get("authenticated") else "false"}.items():
        html = html.replace(key, value)
    scripts = ["full_ui.js", "ui_polish.js", "workflow_polish.js", "workflow_research.js", "bugfix_ui.js", "profile_ui.js", "profile_compat.js", "final_workflow_fix.js", "profile_switcher.js", "image_profile_ui.js", "profile_research_sync.js", "final_fixes.js", "stability_1_3_1.js", "profile_analyzer_fix.js"]
    payload = '<script>window.current=window.current||"overview";</script>' + "".join((DASHBOARD_DIR / name).read_text(encoding="utf-8") for name in scripts)
    html = html.replace("</body>", payload + "</body>", 1)
    if not account_exists:
        html = html.replace("</body>", "<script>setAuthMode(true,'Create your first admin account.');</script></body>", 1)
    else:
        html = html.replace("</body>", "<script>(function(){const b=document.getElementById('signUpTab');if(b)b.style.display='none';})();</script></body>", 1)
    return HTMLResponse(html)
