from datetime import datetime, timezone

import httpx

from ..schemas import Problem

API = "https://api.stackexchange.com/2.3/questions"
TAGS = ["wordpress", "woocommerce", "php", "javascript", "elementor", "api"]


def fetch_stackoverflow(tags: list[str] | None = None, limit: int = 25, timeout: float = 15.0) -> list[Problem]:
    tags = tags or TAGS
    response = httpx.get(
        API,
        params={
            "site": "stackoverflow",
            "tagged": ";".join(tags),
            "sort": "activity",
            "order": "desc",
            "pagesize": min(limit, 100),
            "filter": "default",
        },
        timeout=timeout,
    )
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
