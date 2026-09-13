from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

import httpx

from .schemas import Problem


def _domain(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else "https://" + raw)
    host = (parsed.hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if re.fullmatch(r"[a-z0-9.-]+", host or "") else ""


def fetch_web(query: str, limit: int = 10, timeout: float = 15.0, website_url: str = "") -> list[Problem]:
    q = query.strip() or "technology problems"
    domain = _domain(website_url)
    # A profile website is context, not a restriction. Keep external Reddit,
    # GitHub, Stack Overflow and news research available alongside the brand.
    if domain:
        q = f"{q} {domain}"
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
        external_id = "web:" + hashlib.sha1(href.encode("utf-8")).hexdigest()[:20]
        results.append(Problem(source="web", external_id=external_id, title=title, url=href, summary=body[:500], body=body, tags=[], score=0, comments=0, published_at=now, discovered_at=now, metadata={"provider": "DuckDuckGo HTML", "website_domain": domain}))
    return results
