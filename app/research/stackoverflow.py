from datetime import datetime, timezone

import httpx

from ..schemas import Problem

API = "https://api.stackexchange.com/2.3/questions"
TAGS = ["wordpress", "woocommerce", "php", "javascript", "elementor", "api"]


def fetch_stackoverflow(tags: list[str] | None = None, limit: int = 25, timeout: float = 15.0) -> list[Problem]:
    tags = tags or TAGS
    problems: list[Problem] = []
    seen_ids: set[str] = set()

    # Stack Exchange treats semicolon-separated tags as AND. Query each
    # target tag separately so one overly-specific combination does not empty
    # the entire source, then deduplicate question IDs locally.
    for tag in tags:
        response = httpx.get(
            API,
            params={
                "site": "stackoverflow",
                "tagged": tag,
                "sort": "activity",
                "order": "desc",
                "pagesize": min(limit, 100),
                "filter": "default",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        for item in response.json().get("items", []):
            question_id = str(item.get("question_id", ""))
            if not question_id or question_id in seen_ids:
                continue
            seen_ids.add(question_id)
            problems.append(
                Problem(
                    source="stackoverflow",
                    external_id=question_id,
                    title=item.get("title", "Untitled question"),
                    url=item.get("link", ""),
                    tags=item.get("tags", []),
                    score=int(item.get("score", 0)),
                    comments=int(item.get("answer_count", 0)),
                    published_at=datetime.fromtimestamp(item["creation_date"], tz=timezone.utc),
                    metadata={"is_answered": bool(item.get("is_answered"))},
                )
            )
            if len(problems) >= limit:
                return problems
    return problems
