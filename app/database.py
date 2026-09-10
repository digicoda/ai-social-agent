import json
import sqlite3
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

CREATE TABLE IF NOT EXISTS content_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL,
    platform TEXT NOT NULL DEFAULT 'generic',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    hashtags TEXT NOT NULL DEFAULT '[]',
    call_to_action TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_approval',
    generation_confidence INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    approved_at TEXT,
    rejected_at TEXT,
    rejection_reason TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON content_drafts(status);
CREATE INDEX IF NOT EXISTS idx_content_drafts_problem ON content_drafts(problem_id);
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


def list_problems(connection: sqlite3.Connection, limit: int = 25) -> list[tuple[int, Problem]]:
    rows = connection.execute(
        "SELECT * FROM problems ORDER BY score DESC, discovered_at DESC LIMIT ?", (limit,)
    ).fetchall()
    problems: list[tuple[int, Problem]] = []
    from datetime import datetime

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
    from datetime import datetime, timezone

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


def get_analysis(connection: sqlite3.Connection, problem_id: int) -> tuple[ProblemAnalysis, str] | None:
    row = connection.execute(
        "SELECT pain_point, audience, root_cause, solution_angle, hooks, risks, confidence, decision "
        "FROM problem_analyses WHERE problem_id = ?",
        (problem_id,),
    ).fetchone()
    if row is None:
        return None
    return (
        ProblemAnalysis(
            pain_point=row["pain_point"],
            audience=row["audience"],
            root_cause=row["root_cause"],
            solution_angle=row["solution_angle"],
            hooks=json.loads(row["hooks"]),
            risks=json.loads(row["risks"]),
            confidence=int(row["confidence"]),
        ),
        row["decision"],
    )


def save_draft(
    connection: sqlite3.Connection,
    problem_id: int,
    platform: str,
    title: str,
    body: str,
    hashtags: list[str],
    call_to_action: str,
    generation_confidence: int,
) -> int:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        """INSERT INTO content_drafts
        (problem_id, platform, title, body, hashtags, call_to_action, status,
         generation_confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending_approval', ?, ?, ?)""",
        (problem_id, platform, title, body, json.dumps(hashtags, ensure_ascii=False),
         call_to_action, max(0, min(100, generation_confidence)), now, now),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_drafts(connection: sqlite3.Connection, status: str | None = None, limit: int = 25) -> list[sqlite3.Row]:
    if status:
        return connection.execute(
            "SELECT * FROM content_drafts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    return connection.execute(
        "SELECT * FROM content_drafts ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()


def update_draft_status(
    connection: sqlite3.Connection,
    draft_id: int,
    status: str,
    rejection_reason: str = "",
) -> bool:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    timestamp_column = {
        "approved": "approved_at",
        "rejected": "rejected_at",
    }.get(status)
    if timestamp_column:
        cursor = connection.execute(
            f"UPDATE content_drafts SET status = ?, updated_at = ?, {timestamp_column} = ?, rejection_reason = ? "
            "WHERE id = ?",
            (status, now, now, rejection_reason, draft_id),
        )
    else:
        cursor = connection.execute(
            "UPDATE content_drafts SET status = ?, updated_at = ?, rejection_reason = ? WHERE id = ?",
            (status, now, rejection_reason, draft_id),
        )
    connection.commit()
    return cursor.rowcount == 1
