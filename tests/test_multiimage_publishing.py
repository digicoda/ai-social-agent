from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.errors import PublishingError
from app.linkedin_multiimage import LinkedInMultiImageClient
from app.publishing import LinkedInPublisher


def settings() -> Settings:
    return Settings(linkedin_access_token="token", linkedin_author_urn="urn:li:organization:1", database_url="sqlite:///./test.db")


def test_multiimage_client_uploads_all_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    first = tmp_path / "one.jpg"
    second = tmp_path / "two.png"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    client = LinkedInMultiImageClient("token", "urn:li:organization:1", "202608", 5)
    calls: list[str] = []

    def upload(path: str) -> str:
        calls.append(path)
        return f"urn:li:image:{len(calls)}"

    monkeypatch.setattr(client.client, "upload_image", upload)
    assert client.upload_images([str(first), str(second)]) == ["urn:li:image:1", "urn:li:image:2"]
    assert calls == [str(first), str(second)]


def test_multiimage_publisher_builds_native_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher = LinkedInPublisher(settings())
    monkeypatch.setattr(LinkedInMultiImageClient, "upload_images", lambda self, paths: ["urn:li:image:1", "urn:li:image:2"])
    captured: dict = {}

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return httpx.Response(201, headers={"x-restli-id": "urn:li:share:1"}, request=httpx.Request("POST", "https://api.linkedin.com/rest/posts"))

    monkeypatch.setattr("app.publishing.httpx.post", fake_post)
    result = publisher.publish("Title", "Body", ["tag"], media_paths=["one.jpg", "two.jpg"], media_type="multi_image")
    assert result.remote_id == "urn:li:share:1"
    assert captured["json"]["content"]["multiImage"]["images"] == [
        {"id": "urn:li:image:1"},
        {"id": "urn:li:image:2"},
    ]


def test_multiimage_rejects_single_image(tmp_path: Path) -> None:
    image = tmp_path / "one.jpg"
    image.write_bytes(b"image")
    client = LinkedInMultiImageClient("token", "urn:li:organization:1", "202608", 5)
    with pytest.raises(PublishingError) as exc:
        client.upload_images([str(image)])
    assert exc.value.retryable is False
