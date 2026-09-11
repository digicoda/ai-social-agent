from datetime import datetime, timezone

import feedparser
import httpx

from ..schemas import Problem


def fetch_rss(feeds: list[str], limit: int = 25, timeout: float = 15.0) -> list[Problem]:
    problems: list[Problem] = []
    for feed_url in feeds:
        response = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            continue
        for entry in parsed.entries[:limit]:
            link = entry.get("link", "")
            if not link:
                continue
            published = _entry_datetime(entry)
            problems.append(
                Problem(
                    source="rss",
                    external_id=entry.get("id") or link,
                    title=entry.get("title", "Untitled article"),
                    url=link,
                    summary=entry.get("summary", "") or "",
                    body=entry.get("summary", "") or "",
                    published_at=published,
                    metadata={"feed": feed_url},
                )
            )
            if len(problems) >= limit:
                return problems
    return problems


def _entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)
