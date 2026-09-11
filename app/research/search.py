from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Callable

from ..config import Settings
from ..schemas import Problem
from .github import DEFAULT_QUERY, fetch_github_issues
from .reddit import fetch_reddit
from .rss import fetch_rss
from .stackoverflow import fetch_stackoverflow

SUPPORTED_SOURCES = ("github", "reddit", "stackoverflow", "rss")
CATEGORIES = ("business", "technology", "ai", "marketing", "seo", "ecommerce", "wordpress", "development", "design", "security", "productivity", "finance", "education", "news", "other")
INTENTS = ("problem", "question", "trend", "complaint", "feature_request", "tutorial", "review", "opinion", "bug", "opportunity")
TIME_RANGES = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365}


@dataclass(slots=True)
class SearchItem:
    source: str
    external_id: str
    title: str
    url: str
    body: str
    tags: list[str]
    score: int
    comments: int
    published_at: str | None
    category: str
    intent: str
    relevance: int
    opportunity: int
    trend: int


def _text(problem: Problem) -> str:
    return f"{problem.title} {problem.body} {' '.join(problem.tags)}".lower()


def _classify(text: str) -> tuple[str, str]:
    category_rules = {
        "ai": (" ai ", "artificial intelligence", "llm", "gemini", "chatgpt", "machine learning"),
        "wordpress": ("wordpress", "elementor", "woocommerce"),
        "development": ("python", "php", "javascript", "api", "code", "developer", "programming"),
        "security": ("security", "vulnerability", "cve", "hack", "breach"),
        "seo": ("seo", "search engine", "ranking", "backlink"),
        "marketing": ("marketing", "campaign", "conversion", "ads", "social media"),
        "ecommerce": ("ecommerce", "e-commerce", "shopify", "store", "checkout", "cart"),
        "business": ("business", "startup", "revenue", "customer", "sales"),
        "design": ("design", "ui", "ux", "frontend"),
        "productivity": ("productivity", "workflow", "automation", "task", "time saving"),
        "education": ("course", "learning", "tutorial", "student", "education"),
        "finance": ("finance", "fintech", "payment", "bank", "investment"),
        "news": ("breaking", "announcement", "released", "release", "news"),
    }
    category = "other"
    for name, terms in category_rules.items():
        if any(term in text for term in terms):
            category = name
            break
    intent_rules = (
        ("bug", ("bug", "error", "exception", "crash", "fails", "broken")),
        ("complaint", ("hate", "frustrated", "annoying", "terrible", "disappointed", "complaint")),
        ("feature_request", ("feature request", "would be nice", "please add", "support for", "request")),
        ("question", ("how do i", "how can i", "why does", "anyone know", "what is", "help")),
        ("tutorial", ("tutorial", "guide", "how to", "step by step")),
        ("review", ("review", "rating", "experience with", "worth it")),
        ("opinion", ("i think", "opinion", "thoughts on", "what do you think")),
        ("trend", ("trending", "trend", "growing", "rising", "new in")),
    )
    for intent, terms in intent_rules:
        if any(term in text for term in terms):
            return category, intent
    return category, "opportunity" if "problem" in text or "pain" in text else "trend"


def _relevance(problem: Problem, query: str) -> int:
    if not query.strip():
        return 70
    terms = {x for x in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())}
    if not terms:
        return 70
    text = _text(problem)
    hits = sum(1 for term in terms if term in text)
    return min(100, 35 + round(65 * hits / len(terms)))


def _score(problem: Problem, relevance: int) -> tuple[int, int, int]:
    engagement = min(100, int((problem.score * 4) + (problem.comments * 2)))
    opportunity = min(100, round(relevance * 0.55 + min(100, engagement + 20) * 0.45))
    trend = min(100, round(relevance * 0.5 + min(100, engagement + 10) * 0.5))
    return relevance, opportunity, trend


def _within_date(problem: Problem, days: int | None) -> bool:
    if not days or not problem.published_at:
        return True
    return problem.published_at >= datetime.now(timezone.utc) - timedelta(days=days)


def search_research(
    settings: Settings,
    *,
    query: str = "",
    sources: list[str] | None = None,
    category: str = "all",
    intent: str = "all",
    time_range: str = "30d",
    limit: int = 50,
) -> dict[str, Any]:
    selected = [s for s in (sources or list(SUPPORTED_SOURCES)) if s in SUPPORTED_SOURCES]
    days = TIME_RANGES.get(time_range)
    fetchers: dict[str, Callable[[], list[Problem]]] = {
        "github": lambda: fetch_github_issues(
            query=(f"{query} is:issue is:open" if query.strip() else DEFAULT_QUERY),
            limit=settings.research_limit_per_source,
            timeout=settings.research_timeout_seconds,
        ),
        "reddit": lambda: fetch_reddit(limit=settings.research_limit_per_source, user_agent=settings.reddit_user_agent, timeout=settings.research_timeout_seconds),
        "stackoverflow": lambda: fetch_stackoverflow(limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds),
        "rss": lambda: fetch_rss(settings.rss_feed_list, limit=settings.research_limit_per_source),
    }
    items: list[SearchItem] = []
    failed: list[str] = []
    seen: set[str] = set()
    for source in selected:
        try:
            for problem in fetchers[source]():
                if not _within_date(problem, days):
                    continue
                text = _text(problem)
                if query.strip() and not any(term in text for term in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())):
                    continue
                classified_category, classified_intent = _classify(text)
                if category != "all" and classified_category != category:
                    continue
                if intent != "all" and classified_intent != intent:
                    continue
                if problem.fingerprint in seen:
                    continue
                seen.add(problem.fingerprint)
                relevance, opportunity, trend = _score(problem, _relevance(problem, query))
                items.append(SearchItem(source, problem.external_id, problem.title, problem.url, problem.body, problem.tags, problem.score, problem.comments, problem.published_at.isoformat() if problem.published_at else None, classified_category, classified_intent, relevance, opportunity, trend))
        except Exception:
            failed.append(source)
    items.sort(key=lambda x: (x.opportunity, x.relevance, x.trend), reverse=True)
    return {
        "items": [asdict(item) for item in items[:limit]],
        "total": len(items),
        "failed_sources": failed,
        "sources": selected,
        "filters": {"query": query, "category": category, "intent": intent, "time_range": time_range},
    }


def search_options() -> dict[str, Any]:
    return {
        "sources": [{"id": "github", "name": "GitHub Issues", "enabled": True}, {"id": "reddit", "name": "Reddit", "enabled": True}, {"id": "stackoverflow", "name": "Stack Overflow", "enabled": True}, {"id": "rss", "name": "RSS / News", "enabled": True}, {"id": "web", "name": "Web Search", "enabled": False, "note": "Web adapter reserved for the next integration phase."}],
        "categories": list(CATEGORIES),
        "intents": list(INTENTS),
        "time_ranges": list(TIME_RANGES),
        "modes": ["quick", "standard", "deep"],
    }
