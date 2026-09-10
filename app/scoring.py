from .schemas import Problem

KEYWORDS = {
    "wordpress", "woocommerce", "elementor", "php", "javascript", "api",
    "performance", "seo", "security", "plugin", "theme", "hosting",
    "database", "mysql", "css", "react", "automation", "integration",
}


def score_problem(problem: Problem) -> int:
    text = f"{problem.title} {problem.body} {' '.join(problem.tags)}".lower()
    relevance = min(25, sum(3 for word in KEYWORDS if word in text))
    recency = 20 if problem.published_at else 10
    engagement = min(15, problem.score // 2 + problem.comments // 3)
    technical = min(20, 8 + (4 if problem.body else 0) + (4 if problem.tags else 0) + (4 if problem.source in {"github", "stackoverflow"} else 0))
    service_match = min(15, sum(2 for word in ("bug", "error", "broken", "issue", "fails", "problem") if word in text))
    originality = 5
    return min(100, relevance + recency + engagement + technical + service_match + originality)
