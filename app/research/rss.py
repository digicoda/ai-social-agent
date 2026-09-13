from datetime import datetime, timezone

import feedparser
import httpx

from ..schemas import Problem


def fetch_rss(feeds: list[str], limit: int = 25, query: str = "", timeout: float = 15.0) -> list[Problem]:
    problems: list[Problem] = []
    terms = [term for term in query.lower().split() if len(term) > 2]
    for feed_url in feeds:
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "AI-Social-Agent/1.0"}) as client:
                response = client.get(feed_url)
                response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except Exception:
            continue
        for entry in parsed.entries:
            link = entry.get("link", "")
            if not link:
                continue
            title = entry.get("title", "Untitled article")
            summary = entry.get("summary", "") or ""
            if terms:
                haystack = f"{title} {summary}".lower()
                if not any(term in haystack for term in terms):
                    continue
            published = _entry_datetime(entry)
            problems.append(Problem(source="rss", external_id=entry.get("id") or link, title=title, url=link, summary=summary, body=summary, published_at=published, metadata={"feed": feed_url}))
            if len(problems) >= limit:
                break
        if len(problems) >= limit:
            break
    return problems[:limit]


def _entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)
