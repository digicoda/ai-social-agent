import os
import subprocess
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from .analytics import publishing_history, publishing_stats
from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .dashboard import dashboard_login, dashboard_logout, dashboard_page
from .publish_service import publish_draft
from .publishing import PublishingError
from .readiness import check_readiness
from .research.runner import run_research
from .research.profiles import delete_profile, get_profile, list_profiles, save_profile
from .research.search import SearchRequest, search as run_profile_search
from .scheduler import run_due_schedules
from .scheduling import cancel_draft_schedule, schedule_draft, schedules
from .system_settings import provider_status, read_settings, save_settings, test_provider
app = FastAPI(title="AI Social Agent", version="1.2.2")
app.add_middleware(SessionMiddleware, secret_key=get_settings().session_secret or "development-only-session-secret", session_cookie="ai_social_session", same_site="lax", https_only=get_settings().app_env.lower() == "production")
class ApprovalRequest(BaseModel): action: str = Field(pattern="^(approved|rejected)$"); reason: str = ""
class ScheduleRequest(BaseModel): provider: str = "linkedin"; scheduled_for: str; max_attempts: int = Field(default=3, ge=1, le=10); media_type: str = Field(default="none", pattern="^(none|image|document|video|multi_image)$"); media_paths: list[str] = Field(default_factory=list, max_length=20)
class MediaPublishRequest(BaseModel): provider: str = "linkedin"; image_path: str = Field(min_length=1)
class MultiImagePublishRequest(BaseModel): provider: str = "linkedin"; image_paths: list[str] = Field(min_length=2, max_length=20)
class DocumentPublishRequest(BaseModel): provider: str = "linkedin"; document_path: str = Field(min_length=1)
class VideoPublishRequest(BaseModel): provider: str = "linkedin"; video_path: str = Field(min_length=1)
class LoginRequest(BaseModel): username: str = Field(min_length=1, max_length=128); password: str = Field(min_length=1, max_length=256)
class SettingsRequest(BaseModel): values: dict[str, object] = Field(default_factory=dict)
class ProfileRequest(BaseModel): values: dict[str, object] = Field(default_factory=dict)
class ResearchSearchRequest(BaseModel):
    profile_id: int | None = None; topic: str = Field(default="", max_length=500); mode: str = "standard"; category: str = Field(default="", max_length=120); intents: list[str] = Field(default_factory=list, max_length=20); sources: list[str] = Field(default_factory=list, max_length=10); time_range: str = "30d"; limit: int = Field(default=30, ge=1, le=100)
def _authorize(x_api_key: str | None, request: Request) -> None:
    expected = get_settings().internal_api_key
    if expected and x_api_key == expected: return
    if request.session.get("authenticated") is True: return
    if expected: raise HTTPException(status_code=401, detail="invalid API key or dashboard session")
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request): return dashboard_page(request)
@app.post("/dashboard/login")
def dashboard_login_route(request: Request, payload: LoginRequest) -> dict[str, bool]:
    if not dashboard_login(request, payload.username, payload.password): raise HTTPException(status_code=401, detail="invalid credentials or dashboard is not configured")
    return {"authenticated": True}
@app.post("/dashboard/logout")
def dashboard_logout_route(request: Request) -> dict[str, bool]: dashboard_logout(request); return {"authenticated": False}
@app.get("/health")
def health() -> dict[str, str]: return {"status": "ok", "service": "ai-social-agent"}
@app.get("/ready")
def ready(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return check_readiness(get_settings())
@app.get("/system/settings")
def system_settings(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return {"settings": read_settings(), "providers": provider_status()}
@app.put("/system/settings")
def system_settings_update(request: Request, payload: SettingsRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return {"settings": save_settings(payload.values), "providers": provider_status()}
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/system/test/{provider}")
def system_test_provider(provider: str, request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return test_provider(provider)
@app.post("/system/update")
def system_update(request: Request, x_api_key: str | None = Header(default=None)) -> dict[str, str]:
    _authorize(x_api_key, request)
    if os.name != "nt": raise HTTPException(status_code=400, detail="Automatic Windows updates are available only in the Windows Desktop edition.")
    script = Path(__file__).resolve().parents[1] / "windows" / "update-agent.ps1"
    if not script.exists(): raise HTTPException(status_code=500, detail="Windows updater is missing from this installation.")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], cwd=str(script.parent.parent), creationflags=creationflags, close_fds=True)
    return {"status": "started", "message": "Update started. The service will restart automatically after installation."}
@app.get("/research/profiles")
def research_profiles(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return {"items": list_profiles(get_settings().database_url)}
@app.get("/research/profiles/{profile_id}")
def research_profile(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); item = get_profile(get_settings().database_url, profile_id)
    if not item: raise HTTPException(status_code=404, detail="profile not found")
    return {"item": item}
@app.post("/research/profiles")
def research_profile_create(request: Request, payload: ProfileRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return {"item": save_profile(get_settings().database_url, payload.values)}
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.put("/research/profiles/{profile_id}")
def research_profile_update(profile_id: int, request: Request, payload: ProfileRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return {"item": save_profile(get_settings().database_url, payload.values, profile_id)}
    except (ValueError, TypeError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.delete("/research/profiles/{profile_id}")
def research_profile_delete(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return {"deleted": delete_profile(get_settings().database_url, profile_id)}
@app.post("/research/search")
def research_search(request: Request, payload: ResearchSearchRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    settings=get_settings(); profile=None
    if payload.profile_id is not None:
        profile=get_profile(settings.database_url,payload.profile_id)
        if profile is None: raise HTTPException(status_code=404, detail="profile not found")
    try:
        result=run_profile_search(settings, SearchRequest(payload.profile_id,payload.topic,payload.mode,payload.category,payload.intents,payload.sources,payload.time_range,payload.limit), profile)
        return result
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/research/run")
def research_run(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); result = run_research(get_settings()); return {"discovered": result.discovered, "saved": result.saved, "duplicates": result.duplicates, "failed_sources": result.failed_sources}
@app.post("/analysis/run")
def analysis_run(request: Request, limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit); return {"analyzed": result.analyzed, "auto_publish_candidates": result.auto_publish_candidates, "approval_queue": result.approval_queue, "discarded": result.discarded, "failed": result.failed}
@app.post("/content/generate")
def content_generate(request: Request, limit: int = 10, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try: return generate_content(get_settings(), limit=limit)
    except ContentGenerationError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.get("/approval/queue")
def approval_queue(request: Request, limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return {"items": queue(get_settings().database_url, limit=limit)}
