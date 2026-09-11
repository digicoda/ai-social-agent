import json
from dataclasses import dataclass

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


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    """Small REST client for Gemini with explicit error handling and timeouts."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 30.0) -> None:
        if not api_key.strip():
            raise GeminiError("GEMINI_API_KEY is not configured")
        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout

    def analyze(self, problem: Problem) -> ProblemAnalysis:
        prompt = f"""Analyze this technical problem for a social-content research pipeline.
Return ONLY valid JSON with these keys:
pain_point (string), audience (string), root_cause (string), solution_angle (string),
hooks (array of exactly 3 short strings), risks (array of strings), confidence (integer 0-100).
Do not invent facts not supported by the source. Keep the solution angle educational, not promotional.

Source: {problem.source}
Title: {problem.title}
Tags: {', '.join(problem.tags)}
Body:
{problem.body[:12000]}
URL: {problem.url}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise GeminiError(f"Gemini API returned HTTP {exc.response.status_code}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise GeminiError("Gemini API request failed") from exc

        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            hooks = [str(item).strip() for item in data["hooks"]]
            if len(hooks) < 3:
                raise ValueError("Gemini returned fewer than 3 hooks")
            confidence = int(data["confidence"])
            if not 0 <= confidence <= 100:
                raise ValueError("confidence must be between 0 and 100")
            return ProblemAnalysis(
                pain_point=str(data["pain_point"]).strip(),
                audience=str(data["audience"]).strip(),
                root_cause=str(data["root_cause"]).strip(),
                solution_angle=str(data["solution_angle"]).strip(),
                hooks=hooks[:3],
                risks=[str(item).strip() for item in data.get("risks", [])],
                confidence=confidence,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiError("Gemini returned an invalid analysis payload") from exc
