from __future__ import annotations

import os
from pathlib import Path

import httpx

from .config import get_settings

EDITABLE_SETTINGS = {
    "ai_provider": ("AI_PROVIDER", "text"), "gemini_api_key": ("GEMINI_API_KEY", "secret"), "gemini_model": ("GEMINI_MODEL", "text"), "gemini_timeout_seconds": ("GEMINI_TIMEOUT_SECONDS", "number"),
    "openai_api_key": ("OPENAI_API_KEY", "secret"), "openai_model": ("OPENAI_MODEL", "text"), "openai_base_url": ("OPENAI_BASE_URL", "text"),
    "huggingface_api_key": ("HUGGINGFACE_API_KEY", "secret"), "huggingface_model": ("HUGGINGFACE_MODEL", "text"), "huggingface_base_url": ("HUGGINGFACE_BASE_URL", "text"),
    "rss_feeds": ("RSS_FEEDS", "text"), "research_timeout_seconds": ("RESEARCH_TIMEOUT_SECONDS", "number"), "research_limit_per_source": ("RESEARCH_LIMIT_PER_SOURCE", "integer"),
    "linkedin_access_token": ("LINKEDIN_ACCESS_TOKEN", "secret"), "linkedin_author_urn": ("LINKEDIN_AUTHOR_URN", "text"), "linkedin_api_version": ("LINKEDIN_API_VERSION", "text"),
    "publishing_timeout_seconds": ("PUBLISHING_TIMEOUT_SECONDS", "number"), "retry_base_seconds": ("RETRY_BASE_SECONDS", "integer"), "retry_max_seconds": ("RETRY_MAX_SECONDS", "integer"), "worker_batch_size": ("WORKER_BATCH_SIZE", "integer"), "worker_poll_seconds": ("WORKER_POLL_SECONDS", "number"),
}
SECRET_KEYS = {key for key, (_, kind) in EDITABLE_SETTINGS.items() if kind == "secret"}

def config_path() -> Path:
    configured = os.environ.get("AI_SOCIAL_AGENT_CONFIG", "")
    return Path(configured) if configured else Path(__file__).resolve().parents[1] / ".env"

def _read_file() -> dict[str, str]:
    path, values = config_path(), {}
    if not path.exists(): return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1); values[key.strip()] = value
    return values

def _write_file(values: dict[str, str]) -> None:
    path = config_path(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"{key}={values[key]}" for key in sorted(values)) + "\n", encoding="utf-8")

def _validate(key: str, value: str) -> str:
    _, kind = EDITABLE_SETTINGS[key]; value = str(value).strip()
    if kind == "integer":
        number = int(value)
        if number < 1: raise ValueError(f"{key} must be at least 1")
        return str(number)
    if kind == "number":
        number = float(value)
        if number <= 0: raise ValueError(f"{key} must be greater than 0")
        return str(number)
    if key == "ai_provider" and value.lower() not in {"gemini", "openai", "huggingface", "hf"}: raise ValueError("ai_provider must be gemini, openai, or huggingface")
    return value

def read_settings() -> dict:
    settings, raw, result = get_settings(), _read_file(), {}
    for key, (env_name, _) in EDITABLE_SETTINGS.items():
        value = raw.get(env_name, getattr(settings, key))
        result[key] = {"configured": bool(value), "masked": "••••••••" if value else ""} if key in SECRET_KEYS else value
    return result

def save_settings(payload: dict) -> dict:
    raw = _read_file()
    for key, value in payload.items():
        if key not in EDITABLE_SETTINGS or (key in SECRET_KEYS and (value is None or str(value) == "••••••••")): continue
        validated = _validate(key, str(value)); env_name, _ = EDITABLE_SETTINGS[key]; raw[env_name] = validated; os.environ[env_name] = validated
    _write_file(raw); return read_settings()

def provider_status() -> list[dict[str, object]]:
    s = get_settings()
    return [
        {"id":"gemini","name":"Google Gemini","status":"configured" if s.gemini_api_key else "not_configured","supported":True}, {"id":"openai","name":"OpenAI","status":"configured" if s.openai_api_key else "not_configured","supported":True}, {"id":"huggingface","name":"Hugging Face","status":"configured" if s.huggingface_api_key else "not_configured","supported":True},
        {"id":"linkedin","name":"LinkedIn","status":"configured" if s.linkedin_access_token and s.linkedin_author_urn else "not_configured","supported":True}, {"id":"facebook","name":"Facebook Pages","status":"available_next","supported":False}, {"id":"instagram","name":"Instagram","status":"available_next","supported":False}, {"id":"x","name":"X","status":"available_next","supported":False}, {"id":"youtube","name":"YouTube","status":"available_next","supported":False},
    ]

def _model_items(provider: str, data: object) -> list[dict[str, str]]:
    if provider == "gemini":
        raw = data.get("models", []) if isinstance(data, dict) else []
        return [{"id": str(x.get("name", "")).removeprefix("models/"), "name": str(x.get("displayName") or x.get("name", "")).removeprefix("models/")} for x in raw if isinstance(x, dict) and "generateContent" in x.get("supportedGenerationMethods", [])]
    raw = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    return [{"id": str(x.get("id", "")), "name": str(x.get("id", ""))} for x in raw if isinstance(x, dict) and x.get("id")]

def provider_models(provider: str, api_key: str = "") -> dict[str, object]:
    s = get_settings(); provider = provider.lower(); key = api_key.strip() or (s.gemini_api_key if provider == "gemini" else s.openai_api_key if provider == "openai" else s.huggingface_api_key)
    if provider not in {"gemini", "openai", "huggingface"}: raise ValueError("Unsupported AI provider")
    if not key: raise ValueError(f"{provider} API key is not configured")
    timeout = s.gemini_timeout_seconds
    try:
        if provider == "gemini":
            r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": key}, timeout=timeout); r.raise_for_status(); models = _model_items(provider, r.json()); selected = s.gemini_model
        else:
            base = s.openai_base_url if provider == "openai" else s.huggingface_base_url
            r = httpx.get(f"{base.rstrip('/')}/models", headers={"Authorization": f"Bearer {key}"}, timeout=timeout); r.raise_for_status(); models = _model_items(provider, r.json()); selected = s.openai_model if provider == "openai" else s.huggingface_model
        return {"provider": provider, "models": models[:200], "selected": selected}
    except httpx.HTTPStatusError as exc: raise ValueError(f"{provider} returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc: raise ValueError(f"Could not reach {provider}: {exc}") from exc

def test_provider(provider: str) -> dict[str, object]:
    provider = provider.lower()
    if provider in {"gemini", "openai", "huggingface", "hf"}:
        try:
            data = provider_models("huggingface" if provider == "hf" else provider)
            return {"ok": True, "message": f"{data['provider'].title()} API connection is working.", "models": data["models"], "selected": data["selected"]}
        except ValueError as exc: return {"ok": False, "message": str(exc), "models": []}
    s = get_settings()
    if provider == "linkedin":
        if not s.linkedin_access_token or not s.linkedin_author_urn: return {"ok": False, "message": "LinkedIn access token and author URN are required."}
        try:
            r = httpx.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {s.linkedin_access_token}"}, timeout=s.publishing_timeout_seconds)
            if r.status_code >= 400: return {"ok": False, "message": f"LinkedIn returned HTTP {r.status_code}. Check the token and scopes."}
            return {"ok": True, "message": "LinkedIn token is accepted."}
        except httpx.RequestError as exc: return {"ok": False, "message": f"LinkedIn connection failed: {exc}"}
    return {"ok": False, "message": "This provider is not implemented."}
