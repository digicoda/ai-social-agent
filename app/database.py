import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from .ai import ProblemAnalysis
from .schemas import Problem

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, external_id TEXT NOT NULL,
    title TEXT NOT NULL, url TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]', score INTEGER NOT NULL DEFAULT 0, comments INTEGER NOT NULL DEFAULT 0,
    published_at TEXT, discovered_at TEXT NOT NULL, fingerprint TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source, external_id), UNIQUE(fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_problems_source ON problems(source);
CREATE INDEX IF NOT EXISTS idx_problems_discovered ON problems(discovered_at);
CREATE TABLE IF NOT EXISTS problem_analyses (
    problem_id INTEGER PRIMARY KEY, pain_point TEXT NOT NULL, audience TEXT NOT NULL, root_cause TEXT NOT NULL,
    solution_angle TEXT NOT NULL, hooks TEXT NOT NULL DEFAULT '[]', risks TEXT NOT NULL DEFAULT '[]',
    confidence INTEGER NOT NULL, decision TEXT NOT NULL, analyzed_at TEXT NOT NULL,
    FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS problem_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT, representative_problem_id INTEGER NOT NULL, label TEXT NOT NULL,
    FOREIGN KEY(representative_problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_problem_clusters_representative ON problem_clusters(representative_problem_id);
CREATE TABLE IF NOT EXISTS problem_cluster_members (
    cluster_id INTEGER NOT NULL, problem_id INTEGER NOT NULL, similarity REAL NOT NULL DEFAULT 0,
    PRIMARY KEY(cluster_id, problem_id),
    FOREIGN KEY(cluster_id) REFERENCES problem_clusters(id) ON DELETE CASCADE,
    FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cluster_members_problem ON problem_cluster_members(problem_id);
CREATE TABLE IF NOT EXISTS content_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id INTEGER NOT NULL, platform TEXT NOT NULL DEFAULT 'generic',
    title TEXT NOT NULL, body TEXT NOT NULL, hashtags TEXT NOT NULL DEFAULT '[]', call_to_action TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_approval', generation_confidence INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, approved_at TEXT, rejected_at TEXT,
    rejection_reason TEXT NOT NULL DEFAULT '', FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_content_drafts_status ON content_drafts(status);
CREATE INDEX IF NOT EXISTS idx_content_drafts_problem ON content_drafts(problem_id);
CREATE TABLE IF NOT EXISTS publishing_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    remote_id TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT '',
    attempted_at TEXT NOT NULL,
    FOREIGN KEY(draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_publishing_attempts_draft ON publishing_attempts(draft_id);
CREATE INDEX IF NOT EXISTS idx_publishing_attempts_remote ON publishing_attempts(provider, remote_id);
CREATE TABLE IF NOT EXISTS publish_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(draft_id) REFERENCES content_drafts(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_publish_schedules_due ON publish_schedules(status, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_publish_schedules_draft ON publish_schedules(draft_id);
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
        "INSERT OR IGNORE INTO problems (source, external_id, title, url, summary, body, tags, score, comments, published_at, discovered_at, fingerprint, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (problem.source, problem.external_id, problem.title, problem.url, problem.summary, problem.body,
         json.dumps(problem.tags, ensure_ascii=False), problem.score, problem.comments,
         problem.published_at.isoformat() if problem.published_at else None, problem.discovered_at.isoformat(),
         problem.fingerprint, json.dumps(problem.metadata, ensure_ascii=False)),
    )
    connection.commit()
    return cursor.rowcount == 1


def list_problems(connection: sqlite3.Connection, limit: int = 25) -> list[tuple[int, Problem]]:
    from datetime import datetime
    rows = connection.execute("SELECT * FROM problems ORDER BY score DESC, discovered_at DESC LIMIT ?", (limit,)).fetchall()
    return [(int(row["id"]), Problem(source=row["source"], external_id=row["external_id"], title=row["title"],
        url=row["url"], summary=row["summary"], body=row["body"], tags=json.loads(row["tags"]), score=int(row["score"]),
        comments=int(row["comments"]), published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        discovered_at=datetime.fromisoformat(row["discovered_at"]), metadata=json.loads(row["metadata"]))) for row in rows]


def save_analysis(connection: sqlite3.Connection, problem_id: int, analysis: ProblemAnalysis, decision: str) -> None:
    from datetime import datetime, timezone
    connection.execute("""INSERT INTO problem_analyses (problem_id, pain_point, audience, root_cause, solution_angle, hooks, risks, confidence, decision, analyzed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(problem_id) DO UPDATE SET pain_point=excluded.pain_point, audience=excluded.audience,
    root_cause=excluded.root_cause, solution_angle=excluded.solution_angle, hooks=excluded.hooks, risks=excluded.risks,
    confidence=excluded.confidence, decision=excluded.decision, analyzed_at=excluded.analyzed_at""",
    (problem_id, analysis.pain_point, analysis.audience, analysis.root_cause, analysis.solution_angle,
     json.dumps(analysis.hooks, ensure_ascii=False), json.dumps(analysis.risks, ensure_ascii=False), analysis.confidence,
     decision, datetime.now(timezone.utc).isoformat()))
    connection.commit()


def get_analysis(connection: sqlite3.Connection, problem_id: int) -> tuple[ProblemAnalysis, str] | None:
    row = connection.execute("SELECT pain_point, audience, root_cause, solution_angle, hooks, risks, confidence, decision FROM problem_analyses WHERE problem_id = ?", (problem_id,)).fetchone()
    if row is None: return None
    return (ProblemAnalysis(row["pain_point"], row["audience"], row["root_cause"], row["solution_angle"], json.loads(row["hooks"]), json.loads(row["risks"]), int(row["confidence"])), row["decision"])


def save_draft(connection: sqlite3.Connection, problem_id: int, platform: str, title: str, body: str, hashtags: list[str], call_to_action: str, generation_confidence: int) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute("INSERT INTO content_drafts (problem_id, platform, title, body, hashtags, call_to_action, status, generation_confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending_approval', ?, ?, ?)",
        (problem_id, platform, title, body, json.dumps(hashtags, ensure_ascii=False), call_to_action, max(0, min(100, generation_confidence)), now, now))
    connection.commit(); return int(cursor.lastrowid)


def list_drafts(connection: sqlite3.Connection, status: str | None = None, limit: int = 25) -> list[sqlite3.Row]:
    if status: return connection.execute("SELECT * FROM content_drafts WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit)).fetchall()
    return connection.execute("SELECT * FROM content_drafts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()


def update_draft_status(connection: sqlite3.Connection, draft_id: int, status: str, rejection_reason: str = "") -> bool:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    timestamp_column = {"approved": "approved_at", "rejected": "rejected_at"}.get(status)
    if timestamp_column:
        cursor = connection.execute(f"UPDATE content_drafts SET status = ?, updated_at = ?, {timestamp_column} = ?, rejection_reason = ? WHERE id = ?", (status, now, now, rejection_reason, draft_id))
    else:
        cursor = connection.execute("UPDATE content_drafts SET status = ?, updated_at = ?, rejection_reason = ? WHERE id = ?", (status, now, rejection_reason, draft_id))
    connection.commit(); return cursor.rowcount == 1


def save_publishing_attempt(connection: sqlite3.Connection, draft_id: int, provider: str, status: str, remote_id: str = "", error: str = "") -> int:
    from datetime import datetime, timezone
    cursor = connection.execute("INSERT INTO publishing_attempts (draft_id, provider, status, remote_id, error, attempted_at) VALUES (?, ?, ?, ?, ?, ?)",
        (draft_id, provider, status, remote_id, error, datetime.now(timezone.utc).isoformat()))
    connection.commit(); return int(cursor.lastrowid)


def existing_published_attempt(connection: sqlite3.Connection, draft_id: int, provider: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM publishing_attempts WHERE draft_id = ? AND provider = ? AND status = 'published' AND remote_id != '' ORDER BY attempted_at DESC LIMIT 1",
        (draft_id, provider),
    ).fetchone()


def mark_draft_published(connection: sqlite3.Connection, draft_id: int) -> bool:
    from datetime import datetime, timezone
    cursor = connection.execute("UPDATE content_drafts SET status = 'published', updated_at = ? WHERE id = ? AND status = 'approved'", (datetime.now(timezone.utc).isoformat(), draft_id))
    connection.commit(); return cursor.rowcount == 1


def create_schedule(connection: sqlite3.Connection, draft_id: int, provider: str, scheduled_for: str, max_attempts: int = 3) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        "INSERT INTO publish_schedules (draft_id, provider, scheduled_for, status, attempts, max_attempts, created_at, updated_at) VALUES (?, ?, ?, 'scheduled', 0, ?, ?, ?)",
        (draft_id, provider, scheduled_for, max(1, max_attempts), now, now),
    )
    connection.commit()
    return int(cursor.lastrowid)


def get_schedule(connection: sqlite3.Connection, schedule_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM publish_schedules WHERE id = ?", (schedule_id,)).fetchone()


def list_schedules(database_url: str, status: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
    connection = connect(database_url)
    try:
        if status:
            return connection.execute("SELECT * FROM publish_schedules WHERE status = ? ORDER BY scheduled_for ASC LIMIT ?", (status, limit)).fetchall()
        return connection.execute("SELECT * FROM publish_schedules ORDER BY scheduled_for ASC LIMIT ?", (limit,)).fetchall()
    finally:
        connection.close()


def list_due_schedules(database_url: str, limit: int = 10) -> list[sqlite3.Row]:
    from datetime import datetime, timezone
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        return connection.execute(
            "SELECT * FROM publish_schedules WHERE status IN ('scheduled', 'retrying') AND scheduled_for <= ? ORDER BY scheduled_for ASC LIMIT ?",
            (now, limit),
        ).fetchall()
    finally:
        connection.close()


def claim_due_schedule(database_url: str, schedule_id: int) -> bool:
    from datetime import datetime, timezone
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE publish_schedules SET status = 'running', updated_at = ? WHERE id = ? AND status IN ('scheduled', 'retrying')",
            (now, schedule_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def complete_schedule(database_url: str, schedule_id: int) -> bool:
    from datetime import datetime, timezone
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute("UPDATE publish_schedules SET status = 'published', updated_at = ? WHERE id = ? AND status = 'running'", (now, schedule_id))
        connection.commit(); return cursor.rowcount == 1
    finally:
        connection.close()


def fail_schedule(database_url: str, schedule_id: int, error: str, next_run: str | None, attempts: int, status: str) -> bool:
    from datetime import datetime, timezone
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute(
            "UPDATE publish_schedules SET status = ?, scheduled_for = COALESCE(?, scheduled_for), attempts = ?, last_error = ?, updated_at = ? WHERE id = ? AND status = 'running'",
            (status, next_run, attempts, error, now, schedule_id),
        )
        connection.commit(); return cursor.rowcount == 1
    finally:
        connection.close()


def cancel_schedule(database_url: str, schedule_id: int) -> bool:
    from datetime import datetime, timezone
    connection = connect(database_url)
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = connection.execute("UPDATE publish_schedules SET status = 'cancelled', updated_at = ? WHERE id = ? AND status IN ('scheduled', 'retrying')", (now, schedule_id))
        connection.commit(); return cursor.rowcount == 1
    finally:
        connection.close()
