from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .analytics import publishing_history, publishing_stats
from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .publish_service import publish_draft
from .publishing import PublishingError
from .research.runner import run_research
from .scheduler import run_due_schedules
from .scheduling import cancel_draft_schedule, schedule_draft, schedules

app = FastAPI(title="AI Social Agent", version="0.9.1")

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

def _authorize(x_api_key: str | None) -> None:
    expected = get_settings().internal_api_key
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="invalid API key")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-social-agent"}

@app.post("/research/run")
def research_run(x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    result = run_research(get_settings())
    return {"discovered": result.discovered, "saved": result.saved, "duplicates": result.duplicates, "failed_sources": result.failed_sources}

@app.post("/analysis/run")
def analysis_run(limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit)
    return {"analyzed": result.analyzed, "auto_publish_candidates": result.auto_publish_candidates, "approval_queue": result.approval_queue, "discarded": result.discarded, "failed": result.failed}

@app.post("/content/generate")
def content_generate(limit: int = 10, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try: return generate_content(get_settings(), limit=limit)
    except ContentGenerationError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/approval/queue")
def approval_queue(status: str = "pending_approval", limit: int = 25, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if status not in {"pending_approval", "approved", "rejected", "published"}: raise HTTPException(status_code=400, detail="invalid status")
    if not 1 <= limit <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"items": queue(get_settings(), status=status, limit=limit)}

@app.post("/approval/{draft_id}")
def approval_decision(draft_id: int, request: ApprovalRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: changed = set_decision(get_settings(), draft_id, request.action, request.reason)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed: raise HTTPException(status_code=404, detail="draft not found")
    return {"id": draft_id, "status": request.action}

@app.post("/publish/{draft_id}")
def publish(draft_id: int, provider: str = "linkedin", x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: return publish_draft(get_settings(), draft_id, provider)
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/publish/{draft_id}/image")
def publish_image(draft_id: int, request: MediaPublishRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: return publish_draft(get_settings(), draft_id, request.provider, media_paths=[request.image_path], media_type="image")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/publish/{draft_id}/multi-image")
def publish_multi_image(draft_id: int, request: MultiImagePublishRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: return publish_draft(get_settings(), draft_id, request.provider, media_paths=request.image_paths, media_type="multi_image")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/publish/{draft_id}/document")
def publish_document(draft_id: int, request: DocumentPublishRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: return publish_draft(get_settings(), draft_id, request.provider, media_paths=[request.document_path], media_type="document")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/publish/{draft_id}/video")
def publish_video(draft_id: int, request: VideoPublishRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try: return publish_draft(get_settings(), draft_id, request.provider, media_paths=[request.video_path], media_type="video")
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/schedule/{draft_id}")
def schedule(draft_id: int, request: ScheduleRequest, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    try:
        return schedule_draft(get_settings(), draft_id, request.provider, request.scheduled_for, request.max_attempts, request.media_type, request.media_paths)
    except (ValueError, PublishingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/schedules")
def schedule_list(status: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if not 1 <= limit <= 200: raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"items": schedules(get_settings(), status=status, limit=limit)}

@app.delete("/schedule/{schedule_id}")
def schedule_cancel(schedule_id: int, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if not cancel_draft_schedule(get_settings(), schedule_id): raise HTTPException(status_code=404, detail="active schedule not found")
    return {"schedule_id": schedule_id, "status": "cancelled"}

@app.post("/worker/run")
def worker_run(limit: int | None = None, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    batch = limit or get_settings().worker_batch_size
    if not 1 <= batch <= 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return run_due_schedules(get_settings(), limit=batch)

@app.get("/publishing/history")
def history(provider: str | None = None, limit: int = 50, x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    if not 1 <= limit <= 200: raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    return {"items": publishing_history(get_settings().database_url, limit=limit, provider=provider)}

@app.get("/publishing/stats")
def stats(x_api_key: str | None = Header(default=None)) -> dict:
    _authorize(x_api_key)
    return publishing_stats(get_settings().database_url)
