import json
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from .config import Settings
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


class AIAnalysisClient(Protocol):
    def analyze(self, problem: Problem) -> ProblemAnalysis: ...


class AIProviderError(RuntimeError):
    pass


ANALYSIS_INSTRUCTIONS = """You are the intelligence layer of a social-content research system.
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
"""


def _prompt(problem: Problem) -> str:
    return f"""{ANALYSIS_INSTRUCTIONS}

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


def _analysis_from_data(data: dict) -> ProblemAnalysis:
    allowed_categories = {"business", "technology", "ai", "marketing", "seo", "ecommerce", "wordpress", "development", "design", "security", "productivity", "finance", "education", "news", "other"}
    allowed_intents = {"problem", "question", "trend", "complaint", "feature_request", "tutorial", "review", "opinion", "bug", "opportunity"}
    allowed_sentiments = {"positive", "neutral", "mixed", "negative"}
    allowed_trends = {"rising", "declining", "new", "recurring", "stable"}
    hooks = [str(item).strip() for item in data.get("hooks", [])]
    if len(hooks) < 3:
        raise ValueError("AI provider returned fewer than 3 hooks")
    category = str(data.get("category", "other")).strip()
    intent = str(data.get("intent", "problem")).strip()
    sentiment = str(data.get("sentiment", "neutral")).strip()
    trend = str(data.get("trend_label", "stable")).strip()
    return ProblemAnalysis(
        pain_point=str(data["pain_point"]).strip(), audience=str(data["audience"]).strip(),
        root_cause=str(data["root_cause"]).strip(), solution_angle=str(data["solution_angle"]).strip(),
        hooks=hooks[:3], risks=[str(x).strip() for x in data.get("risks", [])],
        confidence=max(0, min(100, int(data["confidence"]))),
        category=category if category in allowed_categories else "other",
        intent=intent if intent in allowed_intents else "problem",
        sentiment=sentiment if sentiment in allowed_sentiments else "neutral",
        severity=max(0, min(100, int(data.get("severity", 0)))),
        frequency_signal=max(0, min(100, int(data.get("frequency_signal", 0)))),
        trend_signal=max(0, min(100, int(data.get("trend_signal", 0)))),
        content_gap=max(0, min(100, int(data.get("content_gap", 0)))),
        opportunity_score=max(0, min(100, int(data.get("opportunity_score", 0)))),
        trend_label=trend if trend in allowed_trends else "stable",
        related_topics=[str(x).strip() for x in data.get("related_topics", [])][:8],
        recommended_formats=[str(x).strip() for x in data.get("recommended_formats", [])][:8],
        evidence=[str(x).strip() for x in data.get("evidence", [])][:5],
    )


class GeminiError(AIProviderError):
    pass


class GeminiClient:
    """REST client for Gemini structured research analysis."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 30.0) -> None:
        if not api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": _prompt(problem)}]}], "generationConfig": {"temperature": 0.15, "responseMimeType": "application/json"}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _analysis_from_data(json.loads(text))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiError("Gemini returned an invalid analysis payload") from exc


class OpenAICompatibleClient:
    """Small HTTP-only client for OpenAI and OpenAI-compatible endpoints such as Hugging Face."""

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 30.0, provider_name: str = "AI") -> None:
        if not api_key:
            raise AIProviderError(f"{provider_name} API key is not configured")
        self.api_key, self.model, self.base_url, self.timeout, self.provider_name = api_key, model, base_url.rstrip("/"), timeout, provider_name

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": [{"role": "system", "content": ANALYSIS_INSTRUCTIONS}, {"role": "user", "content": _prompt(problem)}], "temperature": 0.15, "response_format": {"type": "json_object"}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            text = response.json()["choices"][0]["message"]["content"]
            if isinstance(text, list):
                text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in text)
            return _analysis_from_data(json.loads(text))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError(f"{self.provider_name} returned an invalid analysis payload") from exc


def create_ai_client(settings: Settings) -> AIAnalysisClient:
    provider = settings.ai_provider.strip().lower()
    if provider == "gemini":
        return GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.gemini_timeout_seconds)
    if provider == "openai":
        return OpenAICompatibleClient(settings.openai_api_key, settings.openai_model, settings.openai_base_url, settings.gemini_timeout_seconds, "OpenAI")
    if provider in {"huggingface", "hf"}:
        return OpenAICompatibleClient(settings.huggingface_api_key, settings.huggingface_model, settings.huggingface_base_url, settings.gemini_timeout_seconds, "Hugging Face")
    raise AIProviderError("Unsupported AI provider. Choose gemini, openai, or huggingface.")
