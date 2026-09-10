from fastapi import FastAPI

from .config import get_settings
from .research.runner import run_research

app = FastAPI(title="AI Social Agent", version="0.1.0")


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
