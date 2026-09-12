from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .content import ContentGenerationError, _content_analysis, _generate
from .database import connect, save_draft


def generate_for_problem(settings: Settings, problem_id: int) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise ContentGenerationError("GEMINI_API_KEY is not configured")
    db = connect(settings.database_url)
    try:
        problem = db.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
        if problem is None:
            raise ContentGenerationError("research item was not found")
        existing = db.execute("SELECT id,status FROM content_drafts WHERE problem_id=? AND status!='rejected' LIMIT 1", (problem_id,)).fetchone()
        if existing:
            return {"generated": 0, "skipped": 1, "failed": 0, "reason": "draft already exists", "draft_id": int(existing["id"])}
        analyzed = _content_analysis(db, problem_id)
        if analyzed is None:
            return {"generated": 0, "skipped": 1, "failed": 0, "reason": "research item has not been AI analyzed"}
        analysis, decision = analyzed
        if decision == "discard":
            return {"generated": 0, "skipped": 1, "failed": 0, "reason": "AI analysis marked this item as discard"}
        class ProblemRow:
            pass
        p = ProblemRow()
        for key in ("title", "source", "body"):
            setattr(p, key, problem[key])
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            draft = _generate(client, settings, p, analysis)
        draft_id = save_draft(db, problem_id, "generic", draft.title, draft.body, draft.hashtags, draft.call_to_action, draft.confidence)
        return {"generated": 1, "skipped": 0, "failed": 0, "draft_id": draft_id}
    except httpx.HTTPError as exc:
        raise ContentGenerationError(f"content provider request failed: {exc}") from exc
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ContentGenerationError(f"content generation failed: {exc}") from exc
    finally:
        db.close()


def generate_from_intelligence(settings: Settings, limit: int = 10) -> dict[str, int]:
    if not settings.gemini_api_key:
        raise ContentGenerationError("GEMINI_API_KEY is not configured")
    db = connect(settings.database_url)
    try:
        rows = db.execute("""SELECT p.id FROM problems p JOIN ai_intelligence a ON a.problem_id=p.id
            LEFT JOIN content_drafts d ON d.problem_id=p.id AND d.status!='rejected'
            WHERE d.id IS NULL ORDER BY a.opportunity_score DESC, a.confidence DESC, p.discovered_at DESC LIMIT ?""", (limit,)).fetchall()
        ids = [int(r["id"]) for r in rows]
    finally:
        db.close()
    result = {"generated": 0, "skipped": 0, "failed": 0}
    for problem_id in ids:
        try:
            item = generate_for_problem(settings, problem_id)
            for key in result:
                result[key] += int(item.get(key, 0))
        except ContentGenerationError:
            result["failed"] += 1
    return result
