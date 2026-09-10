import app.linkedin_video as video_module
import app.publishing as publishing
from app.config import Settings


def test_linkedin_video_multipart_post(monkeypatch, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"abcdefghij")
    calls = []

    class Response:
        def __init__(self, payload=None, etag=None, post=False):
            self._payload = payload or {"status": "AVAILABLE"}
            self.headers = {}
            if etag:
                self.headers["etag"] = f'"{etag}"'
            if post:
                self.headers["x-restli-id"] = "urn:li:share:999"

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls.append(("post", url, kwargs))
        if url.endswith("/videos") and kwargs["params"]["action"] == "initializeUpload":
            return Response({"value": {"video": "urn:li:video:123", "uploadToken": "token", "uploadInstructions": [
                {"uploadUrl": "https://upload.example/1", "firstByte": 0, "lastByte": 4},
                {"uploadUrl": "https://upload.example/2", "firstByte": 5, "lastByte": 9},
            ]}})
        if url.endswith("/videos") and kwargs["params"]["action"] == "finalizeUpload":
            return Response({"value": {"video": "urn:li:video:123"}})
        return Response(post=True)

    def fake_put(url, **kwargs):
        calls.append(("put", url, kwargs))
        return Response(etag="etag-1" if url.endswith("/1") else "etag-2")

    def fake_get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return Response({"status": "AVAILABLE"})

    monkeypatch.setattr(video_module.httpx, "post", fake_post)
    monkeypatch.setattr(video_module.httpx, "put", fake_put)
    monkeypatch.setattr(video_module.httpx, "get", fake_get)
    monkeypatch.setattr(publishing.httpx, "post", fake_post)

    publisher = publishing.LinkedInPublisher(Settings(linkedin_access_token="token", linkedin_author_urn="urn:li:person:1"))
    result = publisher.publish("Clip", "Body", ["tag"], media_paths=[str(video)], media_type="video")

    assert result.remote_id == "urn:li:share:999"
    assert calls[0][2]["json"]["initializeUploadRequest"]["fileSizeBytes"] == 10
    assert calls[1][0] == "put"
    assert calls[1][2]["content"] == b"abcde"
    assert calls[1][2]["headers"]["Content-Range"] == "bytes 0-4/*"
    assert calls[2][2]["content"] == b"fghij"
    assert calls[2][2]["headers"]["Content-Range"] == "bytes 5-9/*"
    assert calls[3][2]["json"]["finalizeUploadRequest"]["uploadedPartIds"] == ["etag-1", "etag-2"]
    assert calls[4][0] == "get"
    assert calls[5][2]["json"]["content"]["media"]["id"] == "urn:li:video:123"


def test_video_requires_existing_file(tmp_path):
    client = video_module.LinkedInVideoClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_video(str(tmp_path / "missing.mp4"))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")


def test_video_rejects_unsupported_type(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a video")
    client = video_module.LinkedInVideoClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_video(str(path))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")
