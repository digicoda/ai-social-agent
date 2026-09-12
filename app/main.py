import os
import secrets
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
from .content import ContentGenerationError
from .content_workflow import generate_for_problem, generate_from_intelligence
from .dashboard import dashboard_login, dashboard_logout, dashboard_page
from .intelligence import list_clusters, list_intelligence, run_intelligence
from .profile_automation import run_due_profile_automation, run_profile_cycle
from .profiles import delete_profile, get_profile, list_profiles, save_profile
from .publish_service import publish_draft
from .publishing import PublishingError
from .readiness import check_readiness
from .research.runner import run_research
from .research.search_api import router as research_search_router
from .scheduler import run_due_schedules
from .scheduling import cancel_draft_schedule, schedule_draft, schedules
from .system_settings import provider_status, read_settings, save_settings, test_provider
settings = get_settings()
if settings.app_env.lower() == "production" and not settings.session_secret: raise RuntimeError("SESSION_SECRET must be configured in production.")
session_secret = settings.session_secret or secrets.token_urlsafe(32)
app = FastAPI(title="AI Social Agent", version="1.3.0")
app.include_router(research_search_router)
app.add_middleware(SessionMiddleware, secret_key=session_secret, session_cookie="ai_social_session", same_site="lax", https_only=settings.app_env.lower() == "production", max_age=60 * 60 * 8)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    method = request.method.upper()
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = get_settings().internal_api_key
        if not (expected and request.headers.get("x-api-key") == expected):
            origin = request.headers.get("origin"); referer = request.headers.get("referer"); host = request.headers.get("host", "")
            trusted = {f"http://{host}", f"https://{host}"} if host else set()
            if origin and origin not in trusted: return HTMLResponse("CSRF validation failed.", status_code=403)
            if not origin and referer and not any(referer.startswith(value + "/") or referer == value for value in trusted): return HTMLResponse("CSRF validation failed.", status_code=403)
            if not origin and not referer: return HTMLResponse("CSRF validation failed.", status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"; response.headers["X-Frame-Options"] = "DENY"; response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"; response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(("/dashboard", "/system", "/intelligence", "/research", "/profiles")) else response.headers.get("Cache-Control", "")
    if settings.app_env.lower() == "production": response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
class ApprovalRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$"); reason: str = ""
class ScheduleRequest(BaseModel):
    provider: str = "linkedin"; scheduled_for: str; max_attempts: int = Field(default=3, ge=1, le=10); media_type: str = Field(default="none", pattern="^(none|image|document|video|multi_image)$"); media_paths: list[str] = Field(default_factory=list, max_length=20)
class MediaPublishRequest(BaseModel): provider: str = "linkedin"; image_path: str = Field(min_length=1, max_length=1024)
class MultiImagePublishRequest(BaseModel): provider: str = "linkedin"; image_paths: list[str] = Field(min_length=2, max_length=20)
class DocumentPublishRequest(BaseModel): provider: str = "linkedin"; document_path: str = Field(min_length=1, max_length=1024)
class VideoPublishRequest(BaseModel): provider: str = "linkedin"; video_path: str = Field(min_length=1, max_length=1024)
class LoginRequest(BaseModel): username: str = Field(min_length=1, max_length=128); password: str = Field(min_length=1, max_length=256)
class SettingsRequest(BaseModel): values: dict[str, object] = Field(default_factory=dict)
class ProfileRequest(BaseModel): name: str = Field(min_length=1, max_length=100); config: dict[str, object] = Field(default_factory=dict); enabled: bool = True; profile_id: int | None = None
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
@app.get("/profiles")
def profiles_get(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return {"items": list_profiles(get_settings().database_url)}
@app.get("/profiles/{profile_id}")
def profile_get(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); item = get_profile(get_settings().database_url, profile_id)
    if not item: raise HTTPException(status_code=404, detail="profile not found")
    return item
@app.post("/profiles")
def profile_save(request: Request, payload: ProfileRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return save_profile(get_settings().database_url, payload.name, payload.config, None, payload.enabled)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.put("/profiles")
def profile_update(request: Request, payload: ProfileRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return save_profile(get_settings().database_url, payload.name, payload.config, payload.profile_id, payload.enabled)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.delete("/profiles/{profile_id}")
def profile_delete(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not delete_profile(get_settings().database_url, profile_id): raise HTTPException(status_code=404, detail="profile not found")
    return {"deleted": True, "profile_id": profile_id}
@app.post("/profiles/{profile_id}/run")
def profile_run(profile_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); profile = get_profile(get_settings().database_url, profile_id)
    if not profile: raise HTTPException(status_code=404, detail="profile not found")
    return run_profile_cycle(get_settings(), profile)
@app.post("/profiles/run-due")
def profiles_run_due(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return run_due_profile_automation(get_settings())
@app.post("/research/run")
def research_run(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); result = run_research(get_settings()); return {"discovered": result.discovered, "saved": result.saved, "duplicates": result.duplicates, "failed_sources": result.failed_sources}
@app.post("/analysis/run")
def analysis_run(request: Request, limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit); return {"analyzed": result.analyzed, "auto_publish_candidates": result.auto_publish_candidates, "approval_queue": result.approval_queue, "discarded": result.discarded, "failed": result.failed}
@app.post("/intelligence/run")
def intelligence_run(request: Request, limit: int = 100, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 500: raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    try: result = run_intelligence(get_settings(), limit=limit)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"processed": result.processed, "analyzed": result.analyzed, "duplicates": result.duplicates, "clusters": result.clusters, "assignments": result.assignments, "opportunities": result.opportunities, "failed": result.failed}
@app.get("/intelligence/results")
def intelligence_results(request: Request, limit: int = 100, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 500: raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return {"items": list_intelligence(get_settings(), limit=limit), "clusters": list_clusters(get_settings(), limit=min(limit, 100))}
@app.post("/content/generate")
def content_generate(request: Request, limit: int = 10, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try: return generate_from_intelligence(get_settings(), limit=limit)
    except ContentGenerationError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/content/generate/{problem_id}")
def content_generate_problem(problem_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return generate_for_problem(get_settings(), problem_id)
    except ContentGenerationError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.get("/approval/queue")
def approval_queue(request: Request, status: str = "pending_approval", limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if status not in {"pending_approval", "approved", "rejected", "published"}: raise HTTPException(status_code=400, detail="invalid status")
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"items": queue(get_settings(), status=status, limit=limit)}
@app.post("/approval/{draft_id}")
def approval_decision(draft_id: int, request: Request, payload: ApprovalRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: changed = set_decision(get_settings(), draft_id, payload.action, payload.reason)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed: raise HTTPException(status_code=404, detail="draft not found")
    return {"id": draft_id, "status": payload.action}
@app.post("/publish/{draft_id}")
def publish(draft_id: int, request: Request, provider: str = "linkedin", x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return publish_draft(get_settings(), draft_id, provider)
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/publish/{draft_id}/image")
def publish_image(draft_id: int, payload: MediaPublishRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return publish_draft(get_settings(), draft_id, payload.provider, media_paths=[payload.image_path], media_type="image")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/publish/{draft_id}/multi-image")
def publish_multi_image(draft_id: int, payload: MultiImagePublishRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return publish_draft(get_settings(), draft_id, payload.provider, media_paths=payload.image_paths, media_type="multi_image")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/publish/{draft_id}/document")
def publish_document(draft_id: int, payload: DocumentPublishRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return publish_draft(get_settings(), draft_id, payload.provider, media_paths=[payload.document_path], media_type="document")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/publish/{draft_id}/video")
def publish_video(draft_id: int, payload: VideoPublishRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return publish_draft(get_settings(), draft_id, payload.provider, media_paths=[payload.video_path], media_type="video")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.post("/schedule/{draft_id}")
def schedule(draft_id: int, payload: ScheduleRequest, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    try: return schedule_draft(get_settings(), draft_id, payload.provider, payload.scheduled_for, payload.max_attempts, payload.media_type, payload.media_paths)
    except (ValueError, PublishingError) as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
@app.get("/schedules")
def schedule_list(request: Request, status: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 200: raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"items": schedules(get_settings(), status=status, limit=limit)}
@app.delete("/schedule/{schedule_id}")
def schedule_cancel(schedule_id: int, request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not cancel_draft_schedule(get_settings(), schedule_id): raise HTTPException(status_code=404, detail="active schedule not found")
    return {"schedule_id": schedule_id, "status": "cancelled"}
@app.post("/worker/run")
def worker_run(request: Request, limit: int | None = None, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request); batch = limit or get_settings().worker_batch_size
    if not 1 <= batch <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    schedules_result = run_due_schedules(get_settings(), limit=batch); automation = run_due_profile_automation(get_settings())
    return {"schedules": schedules_result, "automation": automation}
@app.get("/publishing/history")
def history(request: Request, provider: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 200: raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"items": publishing_history(get_settings().database_url, limit=limit, provider=provider)}
@app.get("/publishing/stats")
def stats(request: Request, x_api_key: str | None = Header(default=None)) -> dict: _authorize(x_api_key, request); return publishing_stats(get_settings().database_url)
