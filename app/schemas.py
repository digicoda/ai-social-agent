from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Problem:
    source: str
    external_id: str
    title: str
    url: str
    summary: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    score: int = 0
    comments: int = 0
    published_at: datetime | None = None
    discovered_at: datetime = field(default_factory=utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        import hashlib
        normalized = " ".join(self.title.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
