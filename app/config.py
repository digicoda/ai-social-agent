import os
from contextvars import ContextVar
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_active_profile: ContextVar[dict | None] = ContextVar("active_profile", default=None)


def set_active_profile(profile: dict | None):
    return _active_profile.set(profile)


def reset_active_profile(token):
    _active_profile.reset(token)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.environ.get("AI_SOCIAL_AGENT_CONFIG", ".env"), extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./data/ai_social_agent.db"
    internal_api_key: str = ""
    admin_username: str = "admin"
    admin_password: str = ""
    session_secret: str = ""
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 30.0
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    huggingface_api_key: str = ""
    huggingface_model: str = "deepseek-ai/DeepSeek-V3-0324"
    huggingface_base_url: str = "https://router.huggingface.co/v1"
    reddit_user_agent: str = "ai-social-agent/0.1"
    rss_feeds: str = "https://hnrss.org/frontpage"
    research_timeout_seconds: float = 15.0
    research_limit_per_source: int = 25
    publishing_timeout_seconds: float = 20.0
    linkedin_access_token: str = ""
    linkedin_author_urn: str = ""
    linkedin_api_version: str = "202608"
    linkedin_media_poll_attempts: int = 10
    linkedin_media_poll_seconds: float = 1.0
    retry_base_seconds: int = 60
    retry_max_seconds: int = 3600
    worker_batch_size: int = 10
    worker_poll_seconds: float = 60.0

    @property
    def rss_feed_list(self) -> list[str]:
        return [item.strip() for item in self.rss_feeds.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    base = Settings()
    profile = _active_profile.get()
    if not profile: return base
    cfg = profile.get("config") or {}
    values = {"ai_provider": cfg.get("ai_provider", base.ai_provider), "gemini_model": base.gemini_model, "openai_model": base.openai_model, "huggingface_model": base.huggingface_model}
    provider = str(cfg.get("ai_provider") or base.ai_provider)
    model = str(cfg.get("ai_model") or "")
    if provider == "gemini" and model: values["gemini_model"] = model
    elif provider == "openai" and model: values["openai_model"] = model
    elif provider == "huggingface" and model: values["huggingface_model"] = model
    values["database_url"] = profile.get("database_url") or base.database_url
    return base.model_copy(update=values)
