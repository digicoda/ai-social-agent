from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .publish_service import publish_draft
from .publishing import PublishingError
from .research.runner import run_research

app = FastAPI(title="AI Social Agent", version="0.4.0")


class ApprovalRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$")
    reason: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-social-agent"}


@app.post("/research/run")
def research_run() -> dict:
    result = run_research(get_settings())
    return {"discovered": result.discovered, "saved": result.saved, "duplicates": result.duplicates, "failed_sources": result.failed_sources}


@app.post("/analysis/run")
def analysis_run(limit: int = 25) -> dict:
    if limit < 1 or limit > 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit)
    return {"analyzed": result.analyzed, "auto_publish_candidates": result.auto_publish_candidates, "approval_queue": result.approval_queue, "discarded": result.discarded, "failed": result.failed}


@app.post("/content/generate")
def content_generate(limit: int = 10) -> dict:
    if limit < 1 or limit > 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    try: return generate_content(get_settings(), limit=limit)
    except ContentGenerationError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/approval/queue")
def approval_queue(status: str = "pending_approval", limit: int = 25) -> dict:
    if status not in {"pending_approval", "approved", "rejected", "published"}: raise HTTPException(status_code=400, detail="invalid status")
    if limit < 1 or limit > 100: raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"items": queue(get_settings(), status=status, limit=limit)}


@app.post("/approval/{draft_id}")
def approval_decision(draft_id: int, request: ApprovalRequest) -> dict:
    try: changed = set_decision(get_settings(), draft_id, request.action, request.reason)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed: raise HTTPException(status_code=404, detail="draft not found")
    return {"id": draft_id, "status": request.action}


@app.post("/publish/{draft_id}")
def publish(draft_id: int, provider: str = "linkedin") -> dict:
    try: return publish_draft(get_settings(), draft_id, provider)
    except PublishingError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
