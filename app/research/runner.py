from dataclasses import dataclass
from typing import Callable

from ..config import Settings
from ..database import connect, save_problem
from ..dedup import find_cross_source_duplicate
from ..schemas import Problem
from ..scoring import score_problem
from .github import fetch_github_issues
from .reddit import fetch_reddit
from .rss import fetch_rss
from .stackoverflow import fetch_stackoverflow
from ..websearch import fetch_web


@dataclass(slots=True)
class ResearchResult:
    discovered: int = 0
    saved: int = 0
    duplicates: int = 0
    failed_sources: list[str] | None = None

    def __post_init__(self) -> None:
        if self.failed_sources is None:
            self.failed_sources = []


def run_research(settings: Settings) -> ResearchResult:
    result = ResearchResult()
    sources: list[tuple[str, Callable[[], list[Problem]]]] = [
        ("github", lambda: fetch_github_issues(limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds)),
        ("reddit", lambda: fetch_reddit(limit=settings.research_limit_per_source, user_agent=settings.reddit_user_agent, timeout=settings.research_timeout_seconds)),
        ("stackoverflow", lambda: fetch_stackoverflow(limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds)),
        ("rss", lambda: fetch_rss(settings.rss_feed_list, limit=settings.research_limit_per_source)),
        ("web", lambda: fetch_web(query="technology problems", limit=settings.research_limit_per_source, timeout=settings.research_timeout_seconds)),
    ]
    connection = connect(settings.database_url)
    try:
        for name, fetcher in sources:
            try:
                problems: list[Problem] = fetcher()
                result.discovered += len(problems)
                for problem in problems:
                    problem.score = score_problem(problem)
                    if find_cross_source_duplicate(connection, problem) is not None:
                        result.duplicates += 1
                        continue
                    if save_problem(connection, problem):
                        result.saved += 1
                    else:
                        result.duplicates += 1
            except Exception:
                result.failed_sources.append(name)
    finally:
        connection.close()
    return result
