from datetime import datetime, timezone

import httpx

from ..schemas import Problem

API = "https://api.stackexchange.com/2.3/search/advanced"
TAGS = ["wordpress", "woocommerce", "php", "javascript", "elementor", "api"]


def fetch_stackoverflow(
    tags: list[str] | None = None,
    limit: int = 25,
    timeout: float = 15.0,
    query: str = "",
) -> list[Problem]:
    tags = tags or TAGS
    params = {
        "site": "stackoverflow",
        "tagged": ";".join(tags),
        "sort": "relevance" if query.strip() else "activity",
        "order": "desc",
        "pagesize": min(limit, 100),
        "filter": "default",
    }
    if query.strip():
        params["q"] = query.strip()
    response = httpx.get(API, params=params, timeout=timeout)
    response.raise_for_status()
    problems: list[Problem] = []
    for item in response.json().get("items", [])[:limit]:
        problems.append(
            Problem(
                source="stackoverflow",
                external_id=str(item["question_id"]),
                title=item.get("title", "Untitled question"),
                url=item.get("link", ""),
                tags=item.get("tags", []),
                score=int(item.get("score", 0)),
                comments=int(item.get("answer_count", 0)),
                published_at=datetime.fromtimestamp(item["creation_date"], tz=timezone.utc),
                metadata={"is_answered": bool(item.get("is_answered"))},
            )
        )
    return problems
