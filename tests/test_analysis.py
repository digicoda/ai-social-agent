import json

import httpx
import pytest

from app.ai import GeminiClient, GeminiError
from app.analysis import decision_for_score
from app.schemas import Problem


def test_decision_thresholds() -> None:
    assert decision_for_score(85) == "auto_publish_candidate"
    assert decision_for_score(70) == "approval_queue"
    assert decision_for_score(69) == "discard"


def test_gemini_client_requires_key() -> None:
    with pytest.raises(GeminiError):
        GeminiClient("")


def test_gemini_client_parses_structured_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(
        200,
        json={
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps({
                        "pain_point": "A failing integration",
                        "audience": "Developers",
                        "root_cause": "Bad credentials",
                        "solution_angle": "Show a safe debugging workflow",
                        "hooks": ["Why did it fail?", "Check this first", "A safer fix"],
                        "risks": ["Do not expose secrets"],
                        "confidence": 92,
                    })}]
                }
            }]
        },
        request=httpx.Request("POST", "https://example.test"),
    )

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    analysis = GeminiClient("test-key").analyze(
        Problem(source="github", external_id="1", title="Integration fails", url="https://example.test")
    )
    assert analysis.confidence == 92
    assert len(analysis.hooks) == 3
