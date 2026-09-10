import json
from dataclasses import dataclass

import httpx

from .ai import GeminiError, ProblemAnalysis
from .config import Settings
from .database import get_analysis, list_problems, save_draft


@dataclass(slots=True)
class ContentDraft:
    title: str
    body: str
    hashtags: list[str]
    call_to_action: str
    confidence: int


class ContentGenerationError(RuntimeError):
    pass


def _generate(client: httpx.Client, settings: Settings, problem, analysis: ProblemAnalysis) -> ContentDraft:
    prompt = f"""Create one high-quality educational social media draft from this researched technical problem.
The draft must be useful first, never fabricate facts, never claim personal experience, and never sound like an advertisement.
Return ONLY JSON with exactly these keys:
title (string), body (string), hashtags (array of 3-6 strings without #), call_to_action (string), confidence (integer 0-100).
Use a clear hook, explain the underlying problem briefly, provide practical steps or insight, and end with a natural discussion question.
Keep the body concise enough for a general professional social post (roughly 150-280 words).

Problem title: {problem.title}
Source: {problem.source}
Original context: {problem.body[:10000]}
Pain point: {analysis.pain_point}
Audience: {analysis.audience}
Root cause: {analysis.root_cause}
Solution angle: {analysis.solution_angle}
Hooks: {json.dumps(analysis.hooks, ensure_ascii=False)}
Risks: {json.dumps(analysis.risks, ensure_ascii=False)}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    response = client.post(
        url,
        headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
        },
    )
    response.raise_for_status()
    payload = response.json()
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        title = str(data["title"]).strip()
        body = str(data["body"]).strip()
        hashtags = [str(item).strip().lstrip("#") for item in data["hashtags"] if str(item).strip()]
        cta = str(data["call_to_action"]).strip()
        if not title or not body or not hashtags or not cta:
            raise ValueError("incomplete content draft")
        return ContentDraft(title, body, hashtags[:6], cta, max(0, min(100, int(data["confidence"]))))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ContentGenerationError("Gemini returned an invalid content payload") from exc


def generate_content(settings: Settings, limit: int = 10) -> dict[str, int]:
    if not settings.gemini_api_key:
        raise ContentGenerationError("GEMINI_API_KEY is not configured")

    generated = 0
    skipped = 0
    failed = 0
    with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
        connection = __import__("app.database", fromlist=["connect"]).connect(settings.database_url)
        try:
            for problem_id, problem in list_problems(connection, limit=limit):
                existing = connection.execute(
                    "SELECT 1 FROM content_drafts WHERE problem_id = ? AND status != 'rejected' LIMIT 1",
                    (problem_id,),
                ).fetchone()
                if existing:
                    skipped += 1
                    continue
                analyzed = get_analysis(connection, problem_id)
                if analyzed is None or analyzed[1] == "discard":
                    skipped += 1
                    continue
                analysis, _decision = analyzed
                try:
                    draft = _generate(client, settings, problem, analysis)
                    save_draft(connection, problem_id, "generic", draft.title, draft.body,
                                draft.hashtags, draft.call_to_action, draft.confidence)
                    generated += 1
                except (httpx.HTTPError, GeminiError, ContentGenerationError, ValueError):
                    failed += 1
        finally:
            connection.close()
    return {"generated": generated, "skipped": skipped, "failed": failed}
