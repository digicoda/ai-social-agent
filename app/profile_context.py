from __future__ import annotations

from starlette.requests import Request

from .config import reset_active_profile, set_active_profile
from .profiles import get_profile

COOKIE_NAME = "ai_social_profile"


def install_profile_context(app) -> None:
    if getattr(app, "_ai_profile_context_installed", False):
        return

    @app.middleware("http")
    async def profile_context_middleware(request: Request, call_next):
        path = request.url.path
        # Profile management itself always runs against the master database.
        if path.startswith("/profiles") or path in {"/dashboard", "/dashboard/login", "/dashboard/logout", "/health", "/ready"}:
            return await call_next(request)
        raw = request.cookies.get(COOKIE_NAME)
        token = None
        try:
            if raw and raw.isdigit():
                profile = get_profile(__import__("app.config", fromlist=["get_settings"]).get_settings().database_url, int(raw))
                if profile:
                    token = set_active_profile(profile)
            return await call_next(request)
        finally:
            if token is not None:
                reset_active_profile(token)

    app._ai_profile_context_installed = True
