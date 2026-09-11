import json
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .ai import ProblemAnalysis
from .schemas import Problem


SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    score INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source, external_id),
    UNIQUE(fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_problems_source ON problems(source);
CREATE INDEX IF NOT EXISTS idx_problems_discovered ON problems(discovered_at);

CREATE TABLE IF NOT EXISTS problem_analyses (
    problem_id INTEGER PRIMARY KEY,
    pain_point TEXT NOT NULL,
    audience TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    solution_angle TEXT NOT NULL,
    hooks TEXT NOT NULL DEFAULT '[]',
    risks TEXT NOT NULL DEFAULT '[]',
    confidence INTEGER NOT NULL,
    decision TEXT NOT NULL,
    analyzed_at TEXT NOT NULL,
    FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS problem_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    representative_problem_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    FOREIGN KEY(representative_problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_problem_clusters_representative
    ON problem_clusters(representative_problem_id);

CREATE TABLE IF NOT EXISTS problem_cluster_members (
    cluster_id INTEGER NOT NULL,
    problem_id INTEGER NOT NULL,
    similarity REAL NOT NULL DEFAULT 0,
    PRIMARY KEY(cluster_id, problem_id),
    FOREIGN KEY(cluster_id) REFERENCES problem_clusters(id) ON DELETE CASCADE,
    FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cluster_members_problem
    ON problem_cluster_members(problem_id);
"""


def _path_from_url(url: str) -> Path:
    parsed = urlparse(url)
    raw = parsed.path[len("sqlite://"):] if parsed.scheme == "sqlite" else url
    return Path(raw or "data/ai_social_agent.db")


def connect(database_url: str) -> sqlite3.Connection:
    path = _path_from_url(database_url)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(SCHEMA)
    return connection


def save_problem(connection: sqlite3.Connection, problem: Problem) -> bool:
    cursor = connection.execute(
        """INSERT OR IGNORE INTO problems
        (source, external_id, title, url, summary, body, tags, score, comments,
         published_at, discovered_at, fingerprint, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            problem.source,
            problem.external_id,
            problem.title,
            problem.url,
            problem.summary,
            problem.body,
            json.dumps(problem.tags, ensure_ascii=False),
            problem.score,
            problem.comments,
            problem.published_at.isoformat() if problem.published_at else None,
            problem.discovered_at.isoformat(),
            problem.fingerprint,
            json.dumps(problem.metadata, ensure_ascii=False),
        ),
    )
    connection.commit()
    return cursor.rowcount == 1


def list_problems(
    connection: sqlite3.Connection,
    limit: int = 25,
    *,
    unanalyzed_only: bool = False,
) -> list[tuple[int, Problem]]:
    query = """SELECT p.* FROM problems p"""
    params: list[int] = []
    if unanalyzed_only:
        query += " LEFT JOIN problem_analyses a ON a.problem_id = p.id WHERE a.problem_id IS NULL"
    query += " ORDER BY p.score DESC, p.discovered_at DESC LIMIT ?"
    params.append(limit)
    rows = connection.execute(query, params).fetchall()

    problems: list[tuple[int, Problem]] = []
    for row in rows:
        published_at = datetime.fromisoformat(row["published_at"]) if row["published_at"] else None
        discovered_at = datetime.fromisoformat(row["discovered_at"])
        problems.append((
            int(row["id"]),
            Problem(
                source=row["source"],
                external_id=row["external_id"],
                title=row["title"],
                url=row["url"],
                summary=row["summary"],
                body=row["body"],
                tags=json.loads(row["tags"]),
                score=int(row["score"]),
                comments=int(row["comments"]),
                published_at=published_at,
                discovered_at=discovered_at,
                metadata=json.loads(row["metadata"]),
            ),
        ))
    return problems


def save_analysis(connection: sqlite3.Connection, problem_id: int, analysis: ProblemAnalysis, decision: str) -> None:
    from datetime import timezone

    connection.execute(
        """INSERT INTO problem_analyses
        (problem_id, pain_point, audience, root_cause, solution_angle, hooks, risks, confidence, decision, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(problem_id) DO UPDATE SET
            pain_point=excluded.pain_point, audience=excluded.audience, root_cause=excluded.root_cause,
            solution_angle=excluded.solution_angle, hooks=excluded.hooks, risks=excluded.risks,
            confidence=excluded.confidence, decision=excluded.decision, analyzed_at=excluded.analyzed_at""",
        (
            problem_id,
            analysis.pain_point,
            analysis.audience,
            analysis.root_cause,
            analysis.solution_angle,
            json.dumps(analysis.hooks, ensure_ascii=False),
            json.dumps(analysis.risks, ensure_ascii=False),
            analysis.confidence,
            decision,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    connection.commit()
