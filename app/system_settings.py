from __future__ import annotations

import os
from pathlib import Path

from .config import get_settings


EDITABLE_SETTINGS = {
    "gemini_api_key": ("GEMINI_API_KEY", "secret"),
    "gemini_model": ("GEMINI_MODEL", "text"),
    "gemini_timeout_seconds": ("GEMINI_TIMEOUT_SECONDS", "number"),
    "rss_feeds": ("RSS_FEEDS", "text"),
    "research_timeout_seconds": ("RESEARCH_TIMEOUT_SECONDS", "number"),
    "research_limit_per_source": ("RESEARCH_LIMIT_PER_SOURCE", "integer"),
    "linkedin_access_token": ("LINKEDIN_ACCESS_TOKEN", "secret"),
    "linkedin_author_urn": ("LINKEDIN_AUTHOR_URN", "text"),
    "linkedin_api_version": ("LINKEDIN_API_VERSION", "text"),
    "publishing_timeout_seconds": ("PUBLISHING_TIMEOUT_SECONDS", "number"),
    "retry_base_seconds": ("RETRY_BASE_SECONDS", "integer"),
    "retry_max_seconds": ("RETRY_MAX_SECONDS", "integer"),
    "worker_batch_size": ("WORKER_BATCH_SIZE", "integer"),
    "worker_poll_seconds": ("WORKER_POLL_SECONDS", "number"),
}

SECRET_KEYS = {key for key, (_, kind) in EDITABLE_SETTINGS.items() if kind == "secret"}


def config_path() -> Path:
    configured = os.environ.get("AI_SOCIAL_AGENT_CONFIG", "")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / ".env"


def _read_file() -> dict[str, str]:
    path = config_path()
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def _write_file(values: dict[str, str]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={values[key]}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate(key: str, value: str) -> str:
    _, kind = EDITABLE_SETTINGS[key]
    value = str(value).strip()
    if kind == "integer":
        number = int(value)
        if number < 1:
            raise ValueError(f"{key} must be at least 1")
        return str(number)
    if kind == "number":
        number = float(value)
        if number <= 0:
            raise ValueError(f"{key} must be greater than 0")
        return str(number)
    return value


def read_settings() -> dict:
    settings = get_settings()
    raw = _read_file()
    result = {}
    for key, (env_name, kind) in EDITABLE_SETTINGS.items():
        value = getattr(settings, key)
        configured = raw.get(env_name)
        if configured is not None:
            value = configured
        if key in SECRET_KEYS:
            result[key] = {"configured": bool(value), "masked": "••••••••" if value else ""}
        else:
            result[key] = value
    return result


def save_settings(payload: dict) -> dict:
    raw = _read_file()
    for key, value in payload.items():
        if key not in EDITABLE_SETTINGS:
            continue
        if key in SECRET_KEYS and (value is None or str(value) == "••••••••"):
            continue
        validated = _validate(key, str(value))
        env_name, _ = EDITABLE_SETTINGS[key]
        raw[env_name] = validated
        os.environ[env_name] = validated
    _write_file(raw)
    get_settings.cache_clear()
    return read_settings()


def provider_status() -> list[dict[str, object]]:
    settings = get_settings()
    return [
        {"id": "linkedin", "name": "LinkedIn", "status": "configured" if settings.linkedin_access_token and settings.linkedin_author_urn else "not_configured", "supported": True},
        {"id": "facebook", "name": "Facebook Pages", "status": "not_configured", "supported": False},
        {"id": "instagram", "name": "Instagram", "status": "not_configured", "supported": False},
        {"id": "x", "name": "X", "status": "not_configured", "supported": False},
        {"id": "youtube", "name": "YouTube", "status": "not_configured", "supported": False},
    ]
