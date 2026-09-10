from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .config import Settings
from .database import connect


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    name: str
    status: str
    detail: str


def _check_database(settings: Settings) -> ReadinessCheck:
    try:
        connection = connect(settings.database_url)
        connection.execute("SELECT 1").fetchone()
        connection.close()
        return ReadinessCheck("database", "ok", "SQLite connection and schema are available")
    except Exception as exc:
        return ReadinessCheck("database", "error", f"database check failed: {exc}")


def _check_configuration(settings: Settings) -> ReadinessCheck:
    problems: list[str] = []
    if settings.app_env.lower() == "production" and not settings.internal_api_key:
        problems.append("INTERNAL_API_KEY is required in production")
    if not re.fullmatch(r"\d{6}", settings.linkedin_api_version):
        problems.append("LINKEDIN_API_VERSION must use YYYYMM format")
    if settings.linkedin_media_poll_attempts < 1:
        problems.append("LINKEDIN_MEDIA_POLL_ATTEMPTS must be >= 1")
    if settings.linkedin_media_poll_seconds <= 0:
        problems.append("LINKEDIN_MEDIA_POLL_SECONDS must be > 0")
    if settings.retry_base_seconds <= 0 or settings.retry_max_seconds < settings.retry_base_seconds:
        problems.append("retry settings must satisfy 0 < RETRY_BASE_SECONDS <= RETRY_MAX_SECONDS")
    if problems:
        return ReadinessCheck("configuration", "error", "; ".join(problems))
    return ReadinessCheck("configuration", "ok", "runtime configuration is structurally valid")


def check_readiness(settings: Settings) -> dict:
    checks = [_check_database(settings), _check_configuration(settings)]
    healthy = all(check.status == "ok" for check in checks)
    return {
        "status": "ready" if healthy else "not_ready",
        "checks": [
            {"name": check.name, "status": check.status, "detail": check.detail}
            for check in checks
        ],
    }
