from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass(slots=True)
class HumanQualityReport:
    score: int
    improvements: list[str]
    sentence_count: int
    average_sentence_words: float
    repeated_phrase_count: int


def _sentence_count(text: str) -> int:
    return max(1, len(re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text.strip()))) if text.strip() else 0


def _average_sentence_words(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not sentences:
        return 0.0
    return round(sum(len(re.findall(r"\b[\w’'-]+\b", s)) for s in sentences) / len(sentences), 1)


def _repeated_phrase_count(text: str) -> int:
    words = re.findall(r"\b[a-zA-Z][a-zA-Z’'-]+\b", text.lower())
    phrases = [" ".join(words[i : i + 3]) for i in range(max(0, len(words) - 2))]
    counts: dict[str, int] = {}
    for phrase in phrases:
        counts[phrase] = counts.get(phrase, 0) + 1
    return sum(1 for count in counts.values() if count > 1)


def _quality_report(draft, improvements: list[str]) -> HumanQualityReport:
    repeated = _repeated_phrase_count(draft.body)
    sentences = _sentence_count(draft.body)
    avg = _average_sentence_words(draft.body)
    score = 100
    if repeated:
        score -= min(20, repeated * 5)
    if avg < 8 or avg > 32:
        score -= 8
    score = max(0, min(100, score))
    return HumanQualityReport(score, improvements[:8], sentences, avg, repeated)


def humanize_content(client: httpx.Client, settings: Settings, draft) -> tuple[object, HumanQualityReport]:
    """Apply a second editorial pass focused on natural, audience-friendly writing.

    This is a quality/editorial transformation, not a detector-evasion routine. It
    must preserve the factual meaning and intent of the generated draft.
    """
    # Imported lazily because content.py calls this module while defining/loading
    # ContentDraft; a module-level import would create a circular dependency.
    from .content import ContentDraft, ContentGenerationError

    prompt = f"""Act as a senior human editor for a professional social-media post.

Rewrite the supplied draft so it reads naturally and confidently, as if it was edited by a skilled subject-matter writer. Improve clarity, usefulness, specificity, rhythm, and audience fit while preserving the original factual meaning, claims, topic, and practical advice.

Editorial rules:
- Remove generic filler, empty introductions, repetitive conclusions, and unnecessary transitions.
- Avoid formulaic or overly symmetrical paragraph and sentence structures.
- Vary sentence length naturally without adding awkward mistakes.
- Prefer concrete wording over vague claims.
- Keep the professional tone; do not become casual, slang-heavy, or ungrammatical.
- Do not invent facts, statistics, quotations, personal experiences, customers, or sources.
- Do not add claims that are not supported by the supplied draft/context.
- Keep the main hook, solution, and user value intact.
- Keep the body within roughly 150-280 words unless the original is shorter.
- Keep hashtags relevant and limited to 3-6.
- Make the call to action feel natural rather than promotional or repetitive.
- Do not mention AI, detectors, humanization, rewriting, or this instruction.

Return ONLY valid JSON with exactly:
title (string), body (string), hashtags (array of 3-6 strings without #), call_to_action (string), confidence (integer 0-100), improvements (array of short strings).

Original draft:
Title: {draft.title}
Body: {draft.body}
Hashtags: {json.dumps(draft.hashtags, ensure_ascii=False)}
Call to action: {draft.call_to_action}
Confidence: {draft.confidence}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    response = client.post(
        url,
        headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.55, "responseMimeType": "application/json"},
        },
    )
    response.raise_for_status()
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
        title = str(data["title"]).strip()
        body = str(data["body"]).strip()
        hashtags = [str(item).strip().lstrip("#") for item in data["hashtags"] if str(item).strip()]
        cta = str(data["call_to_action"]).strip()
        improvements = [str(item).strip() for item in data.get("improvements", []) if str(item).strip()]
        if not title or not body or not hashtags or not cta:
            raise ValueError("incomplete human-quality draft")
        edited = ContentDraft(
            title=title,
            body=body,
            hashtags=hashtags[:6],
            call_to_action=cta,
            confidence=max(0, min(100, int(data["confidence"]))),
        )
        return edited, _quality_report(edited, improvements)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ContentGenerationError("Gemini returned an invalid human-quality payload") from exc
