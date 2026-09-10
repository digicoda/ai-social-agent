import httpx

from ..schemas import Problem


def fetch_reddit(subreddits: list[str] | None = None, limit: int = 25, user_agent: str = "ai-social-agent/0.1", timeout: float = 15.0) -> list[Problem]:
    subreddits = subreddits or ["webdev", "wordpress", "woocommerce", "php", "javascript"]
    problems: list[Problem] = []
    for subreddit in subreddits:
        response = httpx.get(
            f"https://www.reddit.com/r/{subreddit}/new.json",
            params={"limit": min(limit, 100), "raw_json": 1},
            headers={"User-Agent": user_agent},
            timeout=timeout,
        )
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        for child in children:
            data = child.get("data", {})
            if data.get("stickied") or data.get("is_self") is False:
                continue
            problems.append(
                Problem(
                    source="reddit",
                    external_id=str(data.get("id", "")),
                    title=data.get("title", "Untitled post"),
                    url=f"https://www.reddit.com{data.get('permalink', '')}",
                    body=data.get("selftext", "") or "",
                    score=int(data.get("score", 0)),
                    comments=int(data.get("num_comments", 0)),
                    tags=[subreddit],
                    metadata={"subreddit": subreddit},
                )
            )
    return problems[:limit]
