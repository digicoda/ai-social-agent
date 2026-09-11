from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from .analytics import publishing_history, publishing_stats
from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .dashboard import dashboard_login, dashboard_logout, dashboard_page, require_dashboard_session
from .publish_service import publish_draft
from .publishing import PublishingError
from .readiness import check_readiness
from .research.runner import run_research
from .scheduler import run_due_schedules
from .scheduling import cancel_draft_schedule, schedule_draft, schedules

app = FastAPI(title="AI Social Agent", version="1.1.0")

# SessionMiddleware signs the authentication cookie; it does not store secrets in the browser.
# A production deployment must provide a strong SESSION_SECRET.
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().session_secret or "development-only-session-secret",
    session_cookie="ai_social_session",
    same_site="lax",
    https_only=get_settings().app_env.lower() == "production",
)

class ApprovalRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$")
    reason: str = ""

class ScheduleRequest(BaseModel):
    provider: str = "linkedin"
    scheduled_for: str
    max_attempts: int = Field(default=3, ge=1, le=10)
    media_type: str = Field(default="none", pattern="^(none|image|document|video|multi_image)$")
    media_paths: list[str] = Field(default_factory=list, max_length=20)

class MediaPublishRequest(BaseModel):
    provider: str = "linkedin"
    image_path: str = Field(min_length=1)

class MultiImagePublishRequest(BaseModel):
    provider: str = "linkedin"
    image_paths: list[str] = Field(min_length=2, max_length=20)

class DocumentPublishRequest(BaseModel):
    provider: str = "linkedin"
    document_path: str = Field(min_length=1)

class VideoPublishRequest(BaseModel):
    provider: str = "linkedin"
    video_path: str = Field(min_length=1)

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)

def _authorize(x_api_key: str | None, request: Request) -> None:
    expected = get_settings().internal_api_key
    if expected and x_api_key == expected:
        return
    if request.session.get("authenticated") is True:
        return
    if expected:
        raise HTTPException(status_code=401, detail="invalid API key or dashboard session")
    # Development keeps the API convenient when no API key is configured.
    # Production readiness requires INTERNAL_API_KEY.

def _dashboard_authorize(request: Request) -> None:
    require_dashboard_session(request)

@app.get("/dashboard", response_class=__import__("fastapi").responses.HTMLResponse)
def dashboard(request: Request):
    return dashboard_page(request)

@app.post("/dashboard/login")
def dashboard_login_route(request: Request, payload: LoginRequest) -> dict[str, bool]:
    if not dashboard_login(request, payload.username, payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials or dashboard is not configured")
    return {"authenticated": True}

@app.post("/dashboard/logout")
def dashboard_logout_route(request: Request) -> dict[str, bool]:
    dashboard_logout(request)
    return {"authenticated": False}

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-social-agent"}

@app.get("/ready")
def ready(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    return check_readiness(get_settings())

@app.post("/research/run")
def research_run(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    result = run_research(get_settings())
    return {"discovered": result.discovered, "saved": result.saved, "duplicates": result.duplicates, "failed_sources": result.failed_sources}

@app.post("/analysis/run")
def analysis_run(request: Request, limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit)
    return {"analyzed": result.analyzed, "auto_publish_candidates": result.auto_publish_candidates, "approval_queue": result.approval_queue, "discarded": result.discarded, "failed": result.failed}

@app.post("/content/generate")
def content_generate(request: Request, limit: int = 10, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try: return generate_content(get_settings(), limit=limit)
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
    _authorize(x_api_key, request)
    batch = limit or get_settings().worker_batch_size
    if not 1 <= batch <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return run_due_schedules(get_settings(), limit=batch)

@app.get("/publishing/history")
def history(request: Request, provider: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    if not 1 <= limit <= 200: raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"items": publishing_history(get_settings().database_url, limit=limit, provider=provider)}

@app.get("/publishing/stats")
def stats(request: Request, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key, request)
    return publishing_stats(get_settings().database_url)
