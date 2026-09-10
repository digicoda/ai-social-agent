import app.linkedin_media as media_module
import app.publishing as publishing
from app.config import Settings


class Response:
    def __init__(self, payload=None, headers=None):
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_linkedin_image_post_uses_initialize_upload_and_status(monkeypatch, tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"image-bytes")
    calls = []

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        if url.endswith("/images"):
            return Response({"value": {"uploadUrl": "https://uploads.example/image", "image": "urn:li:image:123"}})
        return Response(headers={"x-restli-id": "urn:li:share:456"})

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return Response()

    def fake_get(url, **kwargs):
        calls.append(("GET", url, kwargs))
        return Response({"status": "AVAILABLE", "id": "urn:li:image:123"})

    monkeypatch.setattr(media_module.httpx, "post", fake_post)
    monkeypatch.setattr(media_module.httpx, "put", fake_put)
    monkeypatch.setattr(media_module.httpx, "get", fake_get)
    monkeypatch.setattr(publishing.httpx, "post", fake_post)

    settings = Settings(
        linkedin_access_token="token",
        linkedin_author_urn="urn:li:person:1",
        linkedin_media_poll_seconds=0,
    )
    publisher = publishing.LinkedInPublisher(settings)
    result = publisher.publish("Title", "Body", ["tag"], media_paths=[str(image)])

    assert result.remote_id == "urn:li:share:456"
    assert calls[0][0:2] == ("POST", "https://api.linkedin.com/rest/images")
    assert calls[0][2]["params"] == {"action": "initializeUpload"}
    assert calls[0][2]["json"] == {"initializeUploadRequest": {"owner": "urn:li:person:1"}}
    assert calls[1][0:2] == ("PUT", "https://uploads.example/image")
    assert calls[1][2]["content"] == b"image-bytes"
    assert calls[1][2]["headers"]["Content-Type"] == "image/png"
    assert calls[2][0] == "GET"
    assert "urn%3Ali%3Aimage%3A123" in calls[2][1]
    assert calls[3][0:2] == ("POST", "https://api.linkedin.com/rest/posts")
    assert calls[3][2]["json"]["content"]["media"]["id"] == "urn:li:image:123"


def test_linkedin_image_waits_for_available(monkeypatch, tmp_path):
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image-bytes")
    statuses = iter(["PROCESSING", "AVAILABLE"])
    monkeypatch.setattr(
        media_module.httpx,
        "post",
        lambda *args, **kwargs: Response({"value": {"uploadUrl": "https://uploads.example/image", "image": "urn:li:image:123"}}),
    )
    monkeypatch.setattr(media_module.httpx, "put", lambda *args, **kwargs: Response())
    monkeypatch.setattr(media_module.httpx, "get", lambda *args, **kwargs: Response({"status": next(statuses)}))
    monkeypatch.setattr(media_module.time, "sleep", lambda *_: None)

    client = media_module.LinkedInMediaClient("token", "urn:li:person:1", "202608", 20, poll_seconds=1)
    assert client.upload_image(str(image)) == "urn:li:image:123"


def test_linkedin_image_processing_failure_is_permanent(monkeypatch, tmp_path):
    image = tmp_path / "image.gif"
    image.write_bytes(b"image-bytes")
    monkeypatch.setattr(
        media_module.httpx,
        "post",
        lambda *args, **kwargs: Response({"value": {"uploadUrl": "https://uploads.example/image", "image": "urn:li:image:123"}}),
    )
    monkeypatch.setattr(media_module.httpx, "put", lambda *args, **kwargs: Response())
    monkeypatch.setattr(media_module.httpx, "get", lambda *args, **kwargs: Response({"status": "PROCESSING_FAILED"}))

    client = media_module.LinkedInMediaClient("token", "urn:li:person:1", "202608", 20, poll_seconds=0)
    try:
        client.upload_image(str(image))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
        assert "PROCESSING_FAILED" in str(exc)
    else:
        raise AssertionError("expected PublishingError")


def test_linkedin_image_requires_existing_file(tmp_path):
    client = media_module.LinkedInMediaClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_image(str(tmp_path / "missing.png"))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")


def test_linkedin_image_rejects_unsupported_format(tmp_path):
    image = tmp_path / "image.webp"
    image.write_bytes(b"image-bytes")
    client = media_module.LinkedInMediaClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_image(str(image))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
        assert "JPEG, PNG, and GIF" in str(exc)
    else:
        raise AssertionError("expected PublishingError")
