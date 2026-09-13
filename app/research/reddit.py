import httpx

from ..schemas import Problem


def _fetch(endpoint: str, params: dict, user_agent: str, timeout: float):
    response = httpx.get(endpoint, params=params, headers={"User-Agent": user_agent, "Accept": "application/json"}, timeout=timeout)
    response.raise_for_status()
    return response.json().get("data", {}).get("children", [])


def fetch_reddit(subreddits: list[str] | None = None, limit: int = 25, user_agent: str = "ai-social-agent/0.1", timeout: float = 15.0, query: str = "") -> list[Problem]:
    subreddits = subreddits or ["webdev", "wordpress", "woocommerce", "php", "javascript", "marketing"]
    problems: list[Problem] = []
    endpoints = []
    if query.strip():
        endpoints.append(("https://www.reddit.com/search.json", {"q": query.strip(), "limit": min(limit, 100), "raw_json": 1, "sort": "relevance", "t": "year"}, "global"))
        for subreddit in subreddits:
            endpoints.append((f"https://www.reddit.com/r/{subreddit}/search.json", {"q": query.strip(), "restrict_sr": "1", "limit": min(limit, 100), "raw_json": 1, "sort": "relevance", "t": "year"}, subreddit))
    else:
        endpoints = [(f"https://www.reddit.com/r/{subreddit}/new.json", {"limit": min(limit, 100), "raw_json": 1}, subreddit) for subreddit in subreddits]
    seen: set[str] = set()
    last_error: Exception | None = None
    for endpoint, params, subreddit in endpoints:
        try:
            children = _fetch(endpoint, params, user_agent, timeout)
            for child in children:
                data = child.get("data", {})
                if data.get("stickied") or data.get("is_self") is False:
                    continue
                external_id = str(data.get("id", ""))
                if not external_id or external_id in seen:
                    continue
                seen.add(external_id)
                problems.append(Problem(source="reddit", external_id=external_id, title=data.get("title", "Untitled post"), url=f"https://www.reddit.com{data.get('permalink', '')}", body=data.get("selftext", "") or "", score=int(data.get("score", 0)), comments=int(data.get("num_comments", 0)), tags=[] if subreddit == "global" else [subreddit], metadata={"subreddit": subreddit}))
                if len(problems) >= limit:
                    return problems[:limit]
        except Exception as exc:
            last_error = exc
            continue
    if not problems and last_error is not None:
        raise last_error
    return problems[:limit]
