import json

import httpx

from app.config import Settings
from app.content import ContentDraft
from app.humanize import _average_sentence_words, _repeated_phrase_count, humanize_content


class _MockClient:
    def __init__(self, payload):
        self.payload = payload

    def post(self, *args, **kwargs):
        return httpx.Response(200, json=self.payload, request=httpx.Request("POST", "https://example.test"))


def _payload(data):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(data)}]}}]}


def test_quality_metrics_detect_repeated_phrases_and_sentence_shape():
    text = "Fix the issue quickly. Fix the issue quickly. Then verify the result."
    assert _repeated_phrase_count(text) == 1
    assert _average_sentence_words(text) > 0


def test_human_quality_preserves_structured_draft_shape():
    draft = ContentDraft(
        title="A useful technical fix",
        body="Start with the actual problem. Then check the configuration before changing code.",
        hashtags=["wordpress", "performance", "webdev"],
        call_to_action="What would you check first?",
        confidence=86,
    )
    edited, report = humanize_content(
        _MockClient(_payload({
            "title": "A practical technical fix",
            "body": "Start with the actual problem. Check the configuration before changing code. Then verify the result.",
            "hashtags": ["wordpress", "performance", "webdev"],
            "call_to_action": "What would you check first?",
            "confidence": 90,
            "improvements": ["Removed filler", "Improved sentence rhythm"],
        })),
        Settings(gemini_api_key="test-key"),
        draft,
    )
    assert edited.title
    assert edited.body
    assert edited.hashtags == ["wordpress", "performance", "webdev"]
    assert edited.call_to_action == "What would you check first?"
    assert 0 <= report.score <= 100
    assert report.improvements


def test_human_quality_rejects_invalid_payload():
    draft = ContentDraft("Title", "Body.", ["tag"], "Question?", 80)
    try:
        humanize_content(_MockClient(_payload({"title": "", "body": ""})), Settings(gemini_api_key="test-key"), draft)
    except Exception as exc:
        assert "invalid human-quality payload" in str(exc)
    else:
        raise AssertionError("invalid human-quality payload should fail")


def test_human_quality_can_be_disabled_without_changing_draft():
    settings = Settings(humanize_content=False)
    assert settings.humanize_content is False
