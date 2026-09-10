import app.linkedin_media as media_module
import app.publishing as publishing
from app.config import Settings


def test_linkedin_image_post(monkeypatch, tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"image-bytes")
    calls = []

    class Response:
        def __init__(self, image=False):
            self.headers = {"x-restli-id": "urn:li:image:123" if image else "urn:li:share:456"}
        def raise_for_status(self): pass

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response(image=url.endswith("/images"))

    monkeypatch.setattr(media_module.httpx, "post", fake_post)
    monkeypatch.setattr(publishing.httpx, "post", fake_post)
    publisher = publishing.LinkedInPublisher(Settings(linkedin_access_token="token", linkedin_author_urn="urn:li:person:1"))
    result = publisher.publish("Title", "Body", ["tag"], media_paths=[str(image)])

    assert result.remote_id == "urn:li:share:456"
    assert calls[0][0].endswith("/images")
    assert calls[0][1]["content"] == b"image-bytes"
    assert calls[1][0].endswith("/posts")
    assert calls[1][1]["json"]["media"]["id"] == "urn:li:image:123"


def test_linkedin_image_requires_existing_file(tmp_path):
    client = media_module.LinkedInMediaClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_image(str(tmp_path / "missing.png"))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")
