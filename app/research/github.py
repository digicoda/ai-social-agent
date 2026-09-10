from datetime import datetime, timezone

import httpx

from ..schemas import Problem

GITHUB_API = "https://api.github.com/search/issues"
DEFAULT_QUERY = "is:issue is:open (bug OR error OR broken OR fails OR problem)"


def fetch_github_issues(query: str = DEFAULT_QUERY, limit: int = 25, timeout: float = 15.0) -> list[Problem]:
    response = httpx.get(
        GITHUB_API,
        params={"q": query, "sort": "updated", "order": "desc", "per_page": min(limit, 100)},
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    problems: list[Problem] = []
    for item in items[:limit]:
        problems.append(
            Problem(
                source="github",
                external_id=str(item["id"]),
                title=item.get("title", "Untitled issue"),
                url=item.get("html_url", ""),
                body=item.get("body") or "",
                tags=[label["name"] for label in item.get("labels", []) if label.get("name")],
                score=int(item.get("reactions", {}).get("total_count", 0)),
                comments=int(item.get("comments", 0)),
                published_at=_parse_datetime(item.get("created_at")),
                metadata={"repository": item.get("repository_url", "").rsplit("/", 1)[-1]},
            )
        )
    return problems


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
