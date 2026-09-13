from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.version import compare_versions, latest_release, version_payload


def test_compare_versions_handles_v_prefix_and_patch_numbers():
    assert compare_versions("1.2.3", "1.2.3") == 0
    assert compare_versions("1.2.3", "1.2.4") == -1
    assert compare_versions("1.3.0", "1.2.9") == 1


def test_latest_release_parses_github_release(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "v1.3.1",
                "name": "AI Social Agent v1.3.1",
                "html_url": "https://github.com/digicoda/ai-social-agent/releases/tag/v1.3.1",
                "published_at": "2026-09-13T00:00:00Z",
                "body": "Release notes",
            }

    monkeypatch.setattr("app.version.httpx.get", lambda *args, **kwargs: Response())
    result = latest_release()

    assert result["ok"] is True
    assert result["version"] == "1.3.1"
    assert result["tag"] == "v1.3.1"


def test_version_payload_reports_update(monkeypatch):
    monkeypatch.setattr(
        "app.version.latest_release",
        lambda **kwargs: {
            "ok": True,
            "version": "1.3.1",
            "tag": "v1.3.1",
            "name": "AI Social Agent v1.3.1",
            "url": "https://github.com/digicoda/ai-social-agent/releases/tag/v1.3.1",
            "published_at": "2026-09-13T00:00:00Z",
            "body": "Release notes",
            "checked_at": "2026-09-13T00:00:00+00:00",
        },
    )
    result = version_payload()

    assert result["version"] == "1.3.0"
    assert result["latest_version"] == "1.3.1"
    assert result["update_available"] is True
    assert result["status"] == "Update available."


def test_version_endpoint_returns_runtime_metadata(monkeypatch):
    monkeypatch.setattr(
        main,
        "version_payload",
        lambda **kwargs: {
            "name": "AI Social Agent",
            "version": "1.3.0",
            "release": "v1.3.0",
            "platform": "server",
            "latest_version": "1.3.0",
            "latest_release": "AI Social Agent v1.3.0",
            "latest_release_url": "https://github.com/digicoda/ai-social-agent/releases/tag/v1.3.0",
            "published_at": "2026-09-13T00:00:00Z",
            "update_available": False,
            "status": "Up to date.",
            "features": [],
            "checked_at": "2026-09-13T00:00:00+00:00",
            "error": None,
        },
    )
    client = TestClient(main.app)
    response = client.get("/system/version")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.3.0"
    assert data["latest_version"] == "1.3.0"
    assert data["status"] == "Up to date."
