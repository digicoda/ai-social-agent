import json
from dataclasses import dataclass, field

import httpx

from .schemas import Problem


@dataclass(slots=True)
class ProblemAnalysis:
    pain_point: str
    audience: str
    root_cause: str
    solution_angle: str
    hooks: list[str]
    risks: list[str]
    confidence: int
    category: str = "other"
    intent: str = "problem"
    sentiment: str = "neutral"
    severity: int = 0
    frequency_signal: int = 0
    trend_signal: int = 0
    content_gap: int = 0
    opportunity_score: int = 0
    trend_label: str = "stable"
    related_topics: list[str] = field(default_factory=list)
    recommended_formats: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    """REST client for Gemini structured research analysis."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 30.0) -> None:
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        prompt = f"""You are the intelligence layer of a social-content research system.
Analyze the source item below. Return ONLY valid JSON. Never invent facts.

Required keys:
pain_point, audience, root_cause, solution_angle: strings
hooks: exactly 3 short strings
risks: array of strings
confidence: integer 0-100
category: one of business, technology, ai, marketing, seo, ecommerce, wordpress, development, design, security, productivity, finance, education, news, other
intent: one of problem, question, trend, complaint, feature_request, tutorial, review, opinion, bug, opportunity
sentiment: one of positive, neutral, mixed, negative
severity, frequency_signal, trend_signal, content_gap, opportunity_score: integers 0-100
trend_label: one of rising, declining, new, recurring, stable
related_topics: 3-8 short topic strings
recommended_formats: array using values such as linkedin, x, facebook, instagram, carousel, short_video, long_form
 evidence: 2-5 short source-grounded observations

Scoring guidance:
- severity = impact/urgency visible in the source
- frequency_signal = evidence of repeated/common occurrence in the source itself
- trend_signal = evidence of recency/change, not guesswork
- content_gap = how much useful educational coverage appears missing from the source context
- opportunity_score = balanced 0-100 estimate combining relevance, severity, engagement potential, recurrence, trend and content gap

Source: {problem.source}
Title: {problem.title}
Tags: {', '.join(problem.tags)}
Score: {problem.score}
Comments: {problem.comments}
Published: {problem.published_at.isoformat() if problem.published_at else ''}
Body:
{problem.body[:12000]}
URL: {problem.url}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = httpx.post(
            url,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            hooks = [str(item).strip() for item in data["hooks"]]
            if len(hooks) < 3:
                raise ValueError("Gemini returned fewer than 3 hooks")
            allowed_categories = {"business", "technology", "ai", "marketing", "seo", "ecommerce", "wordpress", "development", "design", "security", "productivity", "finance", "education", "news", "other"}
            allowed_intents = {"problem", "question", "trend", "complaint", "feature_request", "tutorial", "review", "opinion", "bug", "opportunity"}
            allowed_sentiments = {"positive", "neutral", "mixed", "negative"}
            allowed_trends = {"rising", "declining", "new", "recurring", "stable"}
            return ProblemAnalysis(
                pain_point=str(data["pain_point"]).strip(),
                audience=str(data["audience"]).strip(),
                root_cause=str(data["root_cause"]).strip(),
                solution_angle=str(data["solution_angle"]).strip(),
                hooks=hooks[:3],
                risks=[str(item).strip() for item in data.get("risks", [])],
                confidence=max(0, min(100, int(data["confidence"]))),
                category=str(data.get("category", "other")).strip() if str(data.get("category", "other")).strip() in allowed_categories else "other",
                intent=str(data.get("intent", "problem")).strip() if str(data.get("intent", "problem")).strip() in allowed_intents else "problem",
                sentiment=str(data.get("sentiment", "neutral")).strip() if str(data.get("sentiment", "neutral")).strip() in allowed_sentiments else "neutral",
                severity=max(0, min(100, int(data.get("severity", 0)))),
                frequency_signal=max(0, min(100, int(data.get("frequency_signal", 0)))),
                trend_signal=max(0, min(100, int(data.get("trend_signal", 0)))),
                content_gap=max(0, min(100, int(data.get("content_gap", 0)))),
                opportunity_score=max(0, min(100, int(data.get("opportunity_score", 0)))),
                trend_label=str(data.get("trend_label", "stable")).strip() if str(data.get("trend_label", "stable")).strip() in allowed_trends else "stable",
                related_topics=[str(item).strip() for item in data.get("related_topics", [])][:8],
                recommended_formats=[str(item).strip() for item in data.get("recommended_formats", [])][:8],
                evidence=[str(item).strip() for item in data.get("evidence", [])][:5],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiError("Gemini returned an invalid analysis payload") from exc
