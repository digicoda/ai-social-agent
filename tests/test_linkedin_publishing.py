import app.publishing as publishing
from app.config import Settings


def test_linkedin_publish_payload(monkeypatch):
    captured = {}

    class Response:
        headers = {"x-restli-id": "urn:li:share:test"}

        def raise_for_status(self):
            pass

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return Response()

    monkeypatch.setattr(publishing.httpx, "post", fake_post)
    publisher = publishing.LinkedInPublisher(Settings(linkedin_access_token="secret", linkedin_author_urn="urn:li:person:123"))
    result = publisher.publish("Title", "Body", ["python", "webdev"])

    assert result.remote_id == "urn:li:share:test"
    assert captured["url"] == "https://api.linkedin.com/rest/posts"
    assert captured["kwargs"]["headers"]["Authorization"] == "Bearer secret"
    assert captured["kwargs"]["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
    assert captured["kwargs"]["json"]["author"] == "urn:li:person:123"
    assert "#python #webdev" in captured["kwargs"]["json"]["commentary"]
