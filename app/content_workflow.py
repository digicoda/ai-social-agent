from __future__ import annotations

import json
from typing import Any

import httpx

from .ai import create_ai_client
from .config import Settings
from .content import ContentGenerationError, _content_analysis, _generate
from .database import connect, save_analysis, save_draft
from .schemas import Problem


def _analyze_if_needed(settings: Settings, db, problem_id: int, problem_row) -> tuple[Any, str]:
    analyzed = _content_analysis(db, problem_id)
    if analyzed is not None:
        return analyzed

    problem = Problem(
        source=problem_row["source"],
        external_id=problem_row["external_id"],
        title=problem_row["title"],
        url=problem_row["url"],
        summary=problem_row["summary"],
        body=problem_row["body"],
        tags=json.loads(problem_row["tags"]),
        score=int(problem_row["score"]),
        comments=int(problem_row["comments"]),
        published_at=None,
        discovered_at=__import__("datetime").datetime.fromisoformat(problem_row["discovered_at"]),
        metadata=json.loads(problem_row["metadata"]),
    )
    try:
        analysis = create_ai_client(settings).analyze(problem)
    except Exception as exc:
        raise ContentGenerationError(f"AI analysis failed before content generation: {exc}") from exc
    save_analysis(db, problem_id, analysis, "create")
    return analysis, "create"


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
        analysis, decision = _analyze_if_needed(settings, db, problem_id, problem)
        if decision == "discard":
            return {"generated": 0, "skipped": 1, "failed": 0, "reason": "AI analysis marked this item as discard"}
        p = Problem(
            source=problem["source"], external_id=problem["external_id"], title=problem["title"], url=problem["url"],
            summary=problem["summary"], body=problem["body"], tags=json.loads(problem["tags"]), score=int(problem["score"]),
            comments=int(problem["comments"]), published_at=None,
            discovered_at=__import__("datetime").datetime.fromisoformat(problem["discovered_at"]), metadata=json.loads(problem["metadata"]),
        )
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
