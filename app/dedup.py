import re
import sqlite3
from collections import Counter

from .schemas import Problem

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "has", "have", "how", "i", "in", "is", "it", "my", "of", "on",
    "or", "that", "the", "this", "to", "was", "what", "when", "with", "why",
    "you", "your", "can", "do", "does", "doesn", "not", "using", "use",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9_+#.-]{1,}", text.lower())
    return {word.strip("._-") for word in words if word not in _STOPWORDS and len(word) > 2}


def similarity(left: Problem, right: Problem) -> float:
    """Return a lightweight title/body similarity score in the range 0..1."""
    left_title = _tokens(left.title)
    right_title = _tokens(right.title)
    if not left_title or not right_title:
        return 0.0

    title_jaccard = len(left_title & right_title) / len(left_title | right_title)
    left_body = _tokens(f"{left.summary} {left.body}")
    right_body = _tokens(f"{right.summary} {right.body}")
    if left_body and right_body:
        body_jaccard = len(left_body & right_body) / len(left_body | right_body)
    else:
        body_jaccard = 0.0

    # Titles are the strongest signal for short technical questions.
    return round((title_jaccard * 0.75) + (body_jaccard * 0.25), 4)


def find_cross_source_duplicate(
    connection: sqlite3.Connection,
    problem: Problem,
    *,
    threshold: float = 0.82,
    candidate_limit: int = 250,
) -> tuple[int, float] | None:
    """Find a highly similar problem from another source.

    This is intentionally local and deterministic so it remains suitable for
    SQLite/shared-hosting deployments and does not require another AI call.
    """
    rows = connection.execute(
        """SELECT id, source, title, summary, body, tags, score, comments,
                  published_at, discovered_at, external_id, url, metadata
           FROM problems
           WHERE source <> ?
           ORDER BY discovered_at DESC
           LIMIT ?""",
        (problem.source, candidate_limit),
    ).fetchall()

    best: tuple[int, float] | None = None
    for row in rows:
        candidate = Problem(
            source=row["source"],
            external_id=row["external_id"],
            title=row["title"],
            url=row["url"],
            summary=row["summary"],
            body=row["body"],
            tags=[],
            score=int(row["score"]),
            comments=int(row["comments"]),
        )
        score = similarity(problem, candidate)
        if score >= threshold and (best is None or score > best[1]):
            best = (int(row["id"]), score)
    return best
