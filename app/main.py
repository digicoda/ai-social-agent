from fastapi import FastAPI, HTTPException

from .analysis import run_analysis
from .config import get_settings
from .research.runner import run_research

app = FastAPI(title="AI Social Agent", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-social-agent"}


@app.post("/research/run")
def research_run() -> dict:
    result = run_research(get_settings())
    return {
        "discovered": result.discovered,
        "saved": result.saved,
        "duplicates": result.duplicates,
        "failed_sources": result.failed_sources,
    }


@app.post("/analysis/run")
def analysis_run(limit: int = 25) -> dict:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    result = run_analysis(get_settings(), limit=limit)
    return {
        "analyzed": result.analyzed,
        "auto_publish_candidates": result.auto_publish_candidates,
        "approval_queue": result.approval_queue,
        "discarded": result.discarded,
        "failed": result.failed,
    }
