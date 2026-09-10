"""Research source adapters."""

from .github import fetch_github_issues
from .reddit import fetch_reddit
from .rss import fetch_rss
from .stackoverflow import fetch_stackoverflow

__all__ = ["fetch_github_issues", "fetch_reddit", "fetch_rss", "fetch_stackoverflow"]
