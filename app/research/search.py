from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Callable

from ..config import Settings
from ..database import connect, save_problem
from ..schemas import Problem
from .github import DEFAULT_QUERY, fetch_github_issues
from .reddit import fetch_reddit
from .rss import fetch_rss
from .stackoverflow import fetch_stackoverflow
from ..websearch import fetch_web

SUPPORTED_SOURCES = ("github", "reddit", "stackoverflow", "rss", "web")
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
    sentiment: str
    severity: int
    problem_id: int | None = None


def _text(problem: Problem) -> str:
    return f"{problem.title} {problem.body} {' '.join(problem.tags)}".lower()


def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _classify(text: str) -> tuple[str, str]:
    text = _normalize(text)
    category_rules = {"wordpress": ("wordpress", "elementor", "woocommerce"), "ai": (" ai ", "artificial intelligence", "llm", "gemini", "chatgpt", "machine learning"), "development": ("python", "php", "javascript", "api", "code", "developer", "programming"), "security": ("security", "vulnerability", "cve", "hack", "breach"), "seo": ("seo", "search engine", "ranking", "backlink"), "marketing": ("marketing", "campaign", "conversion", "ads", "social media"), "ecommerce": ("ecommerce", "e commerce", "shopify", "store", "checkout", "cart"), "business": ("business", "startup", "revenue", "customer", "sales"), "design": ("design", "ui", "ux", "frontend"), "productivity": ("productivity", "workflow", "automation", "task", "time saving"), "education": ("course", "learning", "tutorial", "student", "education"), "finance": ("finance", "fintech", "payment", "bank", "investment"), "news": ("breaking", "announcement", "released", "release", "news")}
    category = "other"
    for name, terms in category_rules.items():
        if any(term.strip() in text for term in terms):
            category = name
            break
    if re.search(r"\bhow (do|can|could|would) i\b|\bhow to\b|\bwhy (does|is|are|do|did|can)\b|\bwhat (is|are|does)\b|\banyone know\b|\bhelp me\b", text): return category, "question"
    intent_rules = (("bug", ("bug", "error", "exception", "crash", "fails", "failed", "broken", "fatal")), ("complaint", ("hate", "frustrated", "annoying", "terrible", "disappointed", "complaint")), ("feature_request", ("feature request", "would be nice", "please add", "support for", "request")), ("tutorial", ("tutorial", "guide", "step by step")), ("review", ("review", "rating", "experience with", "worth it")), ("opinion", ("i think", "opinion", "thoughts on", "what do you think")), ("trend", ("trending", "trend", "growing", "rising", "new in")))
    for intent, terms in intent_rules:
        if any(term in text for term in terms): return category, intent
    if any(term in text for term in ("problem", "pain point", "pain", "issue")): return category, "problem"
    return category, "opportunity"


def _sentiment(text: str) -> str:
    negative = ("broken", "error", "bug", "bad", "hate", "frustrated", "annoying", "terrible", "failed", "problem", "issue", "pain", "fatal", "security", "breach", "data loss", "blocked")
    positive = ("great", "good", "love", "helpful", "success", "working", "excellent", "easy")
    neg = sum(text.count(word) for word in negative); pos = sum(text.count(word) for word in positive)
    return "negative" if neg > pos else "positive" if pos > neg else "neutral"


def _severity(text: str, intent: str) -> int:
    score = 20
    if intent == "bug": score += 30
    if intent == "complaint": score += 20
    for term, points in (("fatal", 25), ("crash", 20), ("security", 25), ("breach", 30), ("data loss", 30), ("broken", 15), ("error", 10), ("blocked", 15)):
        if term in text: score += points
    return min(100, score)


def _relevance(problem: Problem, query: str) -> int:
    if not query.strip(): return 70
    terms = {x for x in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())}
    if not terms: return 70
    text = _text(problem); hits = sum(1 for term in terms if term in text)
    return min(100, 35 + round(65 * hits / len(terms)))


def _score(problem: Problem, relevance: int, intent: str, severity: int) -> tuple[int, int, int]:
    engagement = min(100, int(max(0, problem.score) * 4 + max(0, problem.comments) * 2))
    opportunity = min(100, round(relevance * 0.45 + min(100, engagement + 20) * 0.35 + severity * 0.20))
    trend = min(100, round(relevance * 0.45 + min(100, engagement + 10) * 0.35 + severity * 0.20))
    if intent in {"bug", "complaint", "feature_request", "problem"}: opportunity = min(100, opportunity + 5)
    return relevance, opportunity, trend


def _within_date(problem: Problem, days: int | None) -> bool:
    if not days or not problem.published_at: return True
    return problem.published_at >= datetime.now(timezone.utc) - timedelta(days=days)


def _dedup_key(problem: Problem) -> str:
    normalized = _normalize(problem.title)
    normalized = re.sub(r"\b(how|why|what|help|issue|problem|question|error|i|do|can|could|would)\b", " ", normalized)
    return " ".join(sorted(set(normalized.split())))


def _cluster(items: list[SearchItem]) -> list[dict[str, Any]]:
    groups: dict[str, list[SearchItem]] = {}
    for item in items:
        key = _normalize(item.title)
        if len(key) < 12: key = item.external_id
        groups.setdefault(key, []).append(item)
    clusters = []
    for key, group in groups.items():
        if len(group) < 2: continue
        clusters.append({"id": key[:80], "title": max(group, key=lambda x: (x.opportunity, x.relevance)).title, "count": len(group), "sources": sorted({x.source for x in group}), "opportunity": max(x.opportunity for x in group), "trend": max(x.trend for x in group), "sentiment": max((x.sentiment for x in group), key=lambda s: {"negative": 3, "neutral": 2, "positive": 1}[s]), "items": [x.external_id for x in group]})
    clusters.sort(key=lambda x: (x.opportunity, x.count, x.trend), reverse=True)
    return clusters[:25]


def search_research(settings: Settings, *, query: str = "", sources: list[str] | None = None, category: str = "all", intent: str = "all", time_range: str = "30d", limit: int = 50, website_url: str = "") -> dict[str, Any]:
    selected = [s for s in (sources or list(SUPPORTED_SOURCES)) if s in SUPPORTED_SOURCES]
    days = TIME_RANGES.get(time_range)
    fetchers: dict[str, Callable[[], list[Problem]]] = {
        "github": lambda: fetch_github_issues(query=(f"{query} is:issue is:open" if query.strip() else DEFAULT_QUERY), limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds),
        "reddit": lambda: fetch_reddit(limit=settings.research_limit_per_source, user_agent=settings.reddit_user_agent, timeout=settings.research_timeout_seconds, query=query),
        "stackoverflow": lambda: fetch_stackoverflow(limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds, query=query),
        "rss": lambda: fetch_rss(settings.rss_feed_list, limit=settings.research_limit_per_source, query=query),
        "web": lambda: fetch_web(query=query, limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds, website_url=website_url),
    }
    items: list[SearchItem] = []; failed: list[str] = []; seen: set[str] = set(); query_terms = [term for term in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", query.lower())]
    source_counts: dict[str, int] = {source: 0 for source in selected}
    db = connect(settings.database_url)
    try:
        for source in selected:
            try:
                for problem in fetchers[source]():
                    if not _within_date(problem, days): continue
                    text = _text(problem)
                    if query.strip() and query_terms and not any(term in text for term in query_terms): continue
                    classified_category, classified_intent = _classify(text)
                    if category != "all" and classified_category != category: continue
                    if intent != "all" and classified_intent != intent: continue
                    dedup_key = f"{source}:{_dedup_key(problem)}"
                    if dedup_key in seen: continue
                    seen.add(dedup_key)
                    save_problem(db, problem)
                    row = db.execute("SELECT id FROM problems WHERE source=? AND external_id=?", (problem.source, problem.external_id)).fetchone()
                    problem_id = int(row["id"]) if row else None
                    sentiment = _sentiment(text); severity = _severity(text, classified_intent); relevance, opportunity, trend = _score(problem, _relevance(problem, query), classified_intent, severity)
                    items.append(SearchItem(source, problem.external_id, problem.title, problem.url, problem.body, problem.tags, problem.score, problem.comments, problem.published_at.isoformat() if problem.published_at else None, classified_category, classified_intent, relevance, opportunity, trend, sentiment, severity, problem_id))
                    source_counts[source] += 1
            except Exception:
                failed.append(source)
    finally:
        db.close()
    items.sort(key=lambda x: (x.opportunity, x.relevance, x.trend, x.severity), reverse=True)
    return {"items": [asdict(item) for item in items[:limit]], "total": len(items), "failed_sources": failed, "sources": selected, "source_counts": source_counts, "clusters": _cluster(items), "filters": {"query": query, "category": category, "intent": intent, "time_range": time_range, "website_url": website_url}}


def search_options() -> dict[str, Any]:
    return {"sources": [{"id": "github", "name": "GitHub Issues", "enabled": True}, {"id": "reddit", "name": "Reddit", "enabled": True}, {"id": "stackoverflow", "name": "Stack Overflow", "enabled": True}, {"id": "rss", "name": "RSS / News", "enabled": True}, {"id": "web", "name": "Web Search", "enabled": True}], "categories": list(CATEGORIES), "intents": list(INTENTS), "time_ranges": list(TIME_RANGES), "modes": ["quick", "standard", "deep"]}
