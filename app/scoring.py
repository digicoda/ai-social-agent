from datetime import datetime, timezone

from .schemas import Problem

KEYWORDS = {
    "wordpress", "woocommerce", "elementor", "php", "javascript", "api",
    "performance", "seo", "security", "plugin", "theme", "hosting",
    "database", "mysql", "css", "react", "automation", "integration",
}


def _recency_score(problem: Problem) -> int:
    if not problem.published_at:
        return 8
    published = problem.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max(0, (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).days)
    if age_days <= 1:
        return 20
    if age_days <= 7:
        return 16
    if age_days <= 30:
        return 12
    if age_days <= 90:
        return 8
    return 4


def score_problem(problem: Problem) -> int:
    text = f"{problem.title} {problem.body} {' '.join(problem.tags)}".lower()
    relevance = min(25, sum(3 for word in KEYWORDS if word in text))
    recency = _recency_score(problem)
    engagement = min(15, max(0, problem.score) // 2 + max(0, problem.comments) // 3)
    technical = min(
        20,
        8
        + (4 if problem.body else 0)
        + (4 if problem.tags else 0)
        + (4 if problem.source in {"github", "stackoverflow"} else 0),
    )
    service_match = min(15, sum(2 for word in ("bug", "error", "broken", "issue", "fails", "problem") if word in text))
    originality = 5
    return min(100, relevance + recency + engagement + technical + service_match + originality)
