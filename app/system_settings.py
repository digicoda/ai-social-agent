from __future__ import annotations

import os
from pathlib import Path

import httpx

from .config import get_settings

EDITABLE_SETTINGS = {
    "ai_provider": ("AI_PROVIDER", "text"),
    "gemini_api_key": ("GEMINI_API_KEY", "secret"),
    "gemini_model": ("GEMINI_MODEL", "text"),
    "gemini_timeout_seconds": ("GEMINI_TIMEOUT_SECONDS", "number"),
    "openai_api_key": ("OPENAI_API_KEY", "secret"),
    "openai_model": ("OPENAI_MODEL", "text"),
    "openai_base_url": ("OPENAI_BASE_URL", "text"),
    "huggingface_api_key": ("HUGGINGFACE_API_KEY", "secret"),
    "huggingface_model": ("HUGGINGFACE_MODEL", "text"),
    "huggingface_base_url": ("HUGGINGFACE_BASE_URL", "text"),
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
    path.write_text("\n".join(f"{key}={values[key]}" for key in sorted(values)) + "\n", encoding="utf-8")


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
    if key == "ai_provider" and value.lower() not in {"gemini", "openai", "huggingface", "hf"}:
        raise ValueError("ai_provider must be gemini, openai, or huggingface")
    return value


def read_settings() -> dict:
    settings = get_settings()
    raw = _read_file()
    result = {}
    for key, (env_name, _) in EDITABLE_SETTINGS.items():
        value = raw.get(env_name, getattr(settings, key))
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
        {"id": "gemini", "name": "Google Gemini", "status": "configured" if settings.gemini_api_key else "not_configured", "supported": True},
        {"id": "openai", "name": "OpenAI", "status": "configured" if settings.openai_api_key else "not_configured", "supported": True},
        {"id": "huggingface", "name": "Hugging Face", "status": "configured" if settings.huggingface_api_key else "not_configured", "supported": True},
        {"id": "linkedin", "name": "LinkedIn", "status": "configured" if settings.linkedin_access_token and settings.linkedin_author_urn else "not_configured", "supported": True},
        {"id": "facebook", "name": "Facebook Pages", "status": "available_next", "supported": False},
        {"id": "instagram", "name": "Instagram", "status": "available_next", "supported": False},
        {"id": "x", "name": "X", "status": "available_next", "supported": False},
        {"id": "youtube", "name": "YouTube", "status": "available_next", "supported": False},
    ]


def test_provider(provider: str) -> dict[str, object]:
    settings = get_settings()
    timeout = settings.gemini_timeout_seconds
    if provider == "gemini":
        if not settings.gemini_api_key:
            return {"ok": False, "message": "Gemini API key is not configured."}
        try:
            response = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": settings.gemini_api_key}, timeout=timeout)
            response.raise_for_status()
            return {"ok": True, "message": "Gemini API connection is working."}
        except httpx.HTTPStatusError as exc:
            return {"ok": False, "message": f"Gemini API returned HTTP {exc.response.status_code}."}
        except httpx.RequestError as exc:
            return {"ok": False, "message": f"Gemini connection failed: {exc}"}
    if provider in {"openai", "huggingface", "hf"}:
        key = settings.openai_api_key if provider == "openai" else settings.huggingface_api_key
        base = settings.openai_base_url if provider == "openai" else settings.huggingface_base_url
        name = "OpenAI" if provider == "openai" else "Hugging Face"
        if not key:
            return {"ok": False, "message": f"{name} API key is not configured."}
        try:
            response = httpx.get(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
            if response.status_code >= 400:
                return {"ok": False, "message": f"{name} returned HTTP {response.status_code}."}
            return {"ok": True, "message": f"{name} API connection is working."}
        except httpx.RequestError as exc:
            return {"ok": False, "message": f"{name} connection failed: {exc}"}
    if provider == "linkedin":
        if not settings.linkedin_access_token or not settings.linkedin_author_urn:
            return {"ok": False, "message": "LinkedIn access token and author URN are required."}
        try:
            response = httpx.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {settings.linkedin_access_token}"}, timeout=settings.publishing_timeout_seconds)
            if response.status_code >= 400:
                return {"ok": False, "message": f"LinkedIn returned HTTP {response.status_code}. Check the token and scopes."}
            return {"ok": True, "message": "LinkedIn token is accepted."}
        except httpx.RequestError as exc:
            return {"ok": False, "message": f"LinkedIn connection failed: {exc}"}
    return {"ok": False, "message": "This provider is not implemented."}
