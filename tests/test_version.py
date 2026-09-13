from pathlib import Path

from app import main
from app.version import APP_VERSION, compare_versions, latest_release, version_payload


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

    assert result["version"] == APP_VERSION
    assert result["latest_version"] == "1.3.1"
    assert result["update_available"] is True
    assert result["status"] == "Update available."


def test_installer_version_matches_application_version():
    installer = Path(__file__).parents[1] / "installer" / "AI-Social-Agent.iss"
    text = installer.read_text(encoding="utf-8")
    marker = '#define AppVersion "'
    start = text.index(marker) + len(marker)
    installed_version = text[start : text.index('"', start)]
    assert installed_version == APP_VERSION


def test_fastapi_version_uses_application_version():
    assert main.app.version == APP_VERSION
    assert any(route.path == "/system/version" for route in main.app.routes)


def test_version_endpoint_handler_returns_runtime_metadata(monkeypatch):
    expected = {
        "name": "AI Social Agent",
        "version": APP_VERSION,
        "release": f"v{APP_VERSION}",
        "platform": "server",
        "latest_version": APP_VERSION,
        "latest_release": f"AI Social Agent v{APP_VERSION}",
        "latest_release_url": f"https://github.com/digicoda/ai-social-agent/releases/tag/v{APP_VERSION}",
        "published_at": "2026-09-13T00:00:00Z",
        "update_available": False,
        "status": "Up to date.",
        "features": [],
        "checked_at": "2026-09-13T00:00:00+00:00",
        "error": None,
    }
    monkeypatch.setattr(main, "version_payload", lambda **kwargs: expected)

    assert main.system_version() == expected
