from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/ai_social_agent.db"

    # AI provider
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 30.0

    # Research sources
    reddit_user_agent: str = "ai-social-agent/0.1"
    rss_feeds: str = "https://hnrss.org/frontpage"
    research_timeout_seconds: float = 15.0
    research_limit_per_source: int = 25

    # Publishing
    publishing_timeout_seconds: float = 20.0
    linkedin_access_token: str = ""
    linkedin_author_urn: str = ""
    linkedin_api_version: str = "202603"
    retry_base_seconds: int = 60
    retry_max_seconds: int = 3600
    worker_batch_size: int = 10

    @property
    def rss_feed_list(self) -> list[str]:
        return [item.strip() for item in self.rss_feeds.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
