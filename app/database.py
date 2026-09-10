import sqlite3
from pathlib import Path
from urllib.parse import urlparse

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
    connection.executescript(SCHEMA)
    return connection


def save_problem(connection: sqlite3.Connection, problem: Problem) -> bool:
    import json

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
