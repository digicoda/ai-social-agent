import app.linkedin_document as document_module
import app.publishing as publishing
from app.config import Settings


def test_linkedin_document_post(monkeypatch, tmp_path):
    document = tmp_path / "guide.pdf"
    document.write_bytes(b"pdf-bytes")
    calls = []

    class Response:
        def __init__(self, payload=None, status="AVAILABLE", post=False):
            self._payload = payload or {"status": status}
            self.headers = {"x-restli-id": "urn:li:share:789"} if post else {}

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        calls.append(("post", url, kwargs))
        if url.endswith("/documents"):
            return Response({"value": {"uploadUrl": "https://upload.example/document", "document": "urn:li:document:123"}})
        return Response(post=True)

    def fake_put(url, **kwargs):
        calls.append(("put", url, kwargs))
        return Response()

    def fake_get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return Response(status="AVAILABLE")

    monkeypatch.setattr(document_module.httpx, "post", fake_post)
    monkeypatch.setattr(document_module.httpx, "put", fake_put)
    monkeypatch.setattr(document_module.httpx, "get", fake_get)
    monkeypatch.setattr(publishing.httpx, "post", fake_post)

    publisher = publishing.LinkedInPublisher(
        Settings(linkedin_access_token="token", linkedin_author_urn="urn:li:person:1")
    )
    result = publisher.publish("Guide", "Body", ["tag"], media_paths=[str(document)], media_type="document")

    assert result.remote_id == "urn:li:share:789"
    assert calls[0][1].endswith("/documents")
    assert calls[0][2]["params"] == {"action": "initializeUpload"}
    assert calls[0][2]["json"]["initializeUploadRequest"]["owner"] == "urn:li:person:1"
    assert calls[1][0] == "put"
    assert calls[1][1] == "https://upload.example/document"
    assert calls[1][2]["content"] == b"pdf-bytes"
    assert calls[2][0] == "get"
    assert calls[3][1].endswith("/posts")
    assert calls[3][2]["json"]["content"]["media"]["id"] == "urn:li:document:123"
    assert calls[3][2]["json"]["content"]["media"]["title"] == "Guide"


def test_document_requires_existing_file(tmp_path):
    client = document_module.LinkedInDocumentClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_document(str(tmp_path / "missing.pdf"))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")


def test_document_rejects_unsupported_type(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not a document")
    client = document_module.LinkedInDocumentClient("token", "urn:li:person:1", "202608", 20)
    try:
        client.upload_document(str(path))
    except publishing.PublishingError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected PublishingError")
