from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

APP_NAME = "AI Social Agent"
APP_VERSION = "1.3.1"
RELEASE_TAG = f"v{APP_VERSION}"
REPOSITORY = "digicoda/ai-social-agent"

FEATURES = [
    "Multi-source research: Web Search, GitHub, Reddit, Stack Overflow and RSS",
    "Profile-based research, AI analysis and content generation",
    "Human Quality Engine for natural professional content",
    "AI image generation with creative shortcodes",
    "Approval, scheduling and publishing workflow",
    "Windows desktop installer and automatic update support",
]


def compare_versions(current: str, latest: str) -> int:
    def parts(value: str) -> tuple[int, ...]:
        raw = value.strip().lstrip("vV").split("+")[0].split("-")[0]
        try:
            return tuple(int(part) for part in raw.split("."))
        except ValueError:
            return (0,)

    left, right = parts(current), parts(latest)
    size = max(len(left), len(right))
    left += (0,) * (size - len(left))
    right += (0,) * (size - len(right))
    return (left > right) - (left < right)


def latest_release(token: str = "", timeout: float = 10.0) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Social-Agent",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    tag = str(data.get("tag_name") or "").strip()
    version = tag.lstrip("vV")
    if not version:
        return {"ok": False, "error": "Latest release did not contain a version tag."}
    return {
        "ok": True,
        "version": version,
        "tag": tag,
        "name": str(data.get("name") or tag),
        "url": str(data.get("html_url") or ""),
        "published_at": data.get("published_at"),
        "body": str(data.get("body") or ""),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def version_payload(token: str = "", platform: str = "server") -> dict[str, Any]:
    release = latest_release(token=token)
    payload: dict[str, Any] = {
        "name": APP_NAME,
        "version": APP_VERSION,
        "release": RELEASE_TAG,
        "platform": platform,
        "repository": REPOSITORY,
        "features": FEATURES,
        "latest_version": None,
        "latest_release": None,
        "latest_release_url": "",
        "published_at": None,
        "release_notes": "",
        "update_available": False,
        "status": "Unable to check for the latest published release.",
        "checked_at": release.get("checked_at"),
        "error": release.get("error") if not release.get("ok") else None,
    }
    if not release.get("ok"):
        return payload

    latest = release["version"]
    comparison = compare_versions(APP_VERSION, latest)
    payload.update(
        {
            "latest_version": latest,
            "latest_release": release["name"],
            "latest_release_url": release["url"],
            "published_at": release["published_at"],
            "release_notes": release["body"],
            "update_available": comparison < 0,
            "status": (
                "Update available."
                if comparison < 0
                else "Up to date."
                if comparison == 0
                else "Development build is ahead of the latest published stable release."
            ),
            "error": None,
        }
    )
    return payload
