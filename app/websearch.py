from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx

from .schemas import Problem


def fetch_web(query: str, limit: int = 10, timeout: float = 15.0) -> list[Problem]:
    q = query.strip() or "technology problems"
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(q)
    headers = {"User-Agent": "AI-Social-Agent/1.0 (+research)"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
    text = response.text
    results: list[Problem] = []
    pattern = re.compile(r'<a[^>]+class=["\']result__a["\'][^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for index, match in enumerate(pattern.finditer(text)):
        if index >= limit:
            break
        href = html.unescape(match.group(1))
        title = re.sub(r"<[^>]+>", " ", html.unescape(match.group(2))).strip()
        title = re.sub(r"\s+", " ", title)
        end = text.find("</div>", match.end())
        fragment = text[match.end():end if end > match.end() else match.end() + 2500]
        snippet_match = re.search(r'class=["\']result__snippet["\'][^>]*>(.*?)</(?:a|div)>', fragment, re.I | re.S)
        body = re.sub(r"<[^>]+>", " ", html.unescape(snippet_match.group(1) if snippet_match else ""))
        body = re.sub(r"\s+", " ", body).strip()
        if not title or not href.startswith(("http://", "https://")):
            continue
        now = datetime.now(timezone.utc)
        results.append(Problem(source="web", external_id="web:" + str(abs(hash(href))), title=title, url=href, summary=body[:500], body=body, tags=[], score=0, comments=0, published_at=now, discovered_at=now, metadata={"provider": "DuckDuckGo HTML"}))
    return results
