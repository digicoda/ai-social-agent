from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .ai import AIAnalysisClient, ProblemAnalysis, create_ai_client
from .config import Settings
from .database import connect
from .schemas import Problem

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "have", "has", "how", "why", "what",
    "when", "where", "your", "you", "are", "was", "were", "not", "but", "can", "could", "would",
    "into", "about", "problem", "issue", "help", "using", "use", "get", "got", "just", "very",
}


def _normalize_token(token: str) -> str:
    replacements = {
        "broke": "break", "breaks": "break", "broken": "break",
        "websites": "site", "website": "site", "sites": "site",
        "queries": "query", "errors": "error", "updates": "update",
    }
    token = replacements.get(token, token)
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("s"):
        token = token[:-1]
    return token


def _tokens(text: str) -> set[str]:
    return {_normalize_token(token) for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in STOPWORDS}


def semantic_similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass(slots=True)
class IntelligenceResult:
    processed: int = 0
    analyzed: int = 0
    duplicates: int = 0
    clusters: int = 0
    assignments: int = 0
    opportunities: int = 0
    failed: int = 0
    skipped: int = 0


def opportunity_score(problem: Problem, analysis: ProblemAnalysis, cluster_size: int = 1) -> int:
    engagement = min(100, problem.score * 2 + problem.comments)
    recurrence = min(100, 35 + cluster_size * 12)
    raw = (
        analysis.severity * 0.20 + analysis.frequency_signal * 0.15 + analysis.trend_signal * 0.15
        + analysis.content_gap * 0.15 + engagement * 0.10 + analysis.confidence * 0.10 + recurrence * 0.15
    )
    return max(0, min(100, round(raw)))


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS ai_intelligence (
            problem_id INTEGER PRIMARY KEY, category TEXT NOT NULL, intent TEXT NOT NULL,
            sentiment TEXT NOT NULL, severity INTEGER NOT NULL, frequency_signal INTEGER NOT NULL,
            trend_signal INTEGER NOT NULL, content_gap INTEGER NOT NULL, opportunity_score INTEGER NOT NULL,
            trend_label TEXT NOT NULL, pain_point TEXT NOT NULL, audience TEXT NOT NULL,
            root_cause TEXT NOT NULL, solution_angle TEXT NOT NULL, hooks TEXT NOT NULL DEFAULT '[]',
            risks TEXT NOT NULL DEFAULT '[]', related_topics TEXT NOT NULL DEFAULT '[]',
            recommended_formats TEXT NOT NULL DEFAULT '[]', evidence TEXT NOT NULL DEFAULT '[]',
            confidence INTEGER NOT NULL, duplicate_of INTEGER, cluster_id INTEGER, analyzed_at TEXT NOT NULL,
            FOREIGN KEY(problem_id) REFERENCES problems(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_ai_intelligence_opportunity ON ai_intelligence(opportunity_score DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_intelligence_cluster ON ai_intelligence(cluster_id);
        CREATE TABLE IF NOT EXISTS ai_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
            member_count INTEGER NOT NULL DEFAULT 0, opportunity_score INTEGER NOT NULL DEFAULT 0,
            trend_label TEXT NOT NULL DEFAULT 'stable', content_angle TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
    """)
    connection.commit()


def _problem(row: sqlite3.Row) -> Problem:
    return Problem(
        source=row["source"], external_id=row["external_id"], title=row["title"], url=row["url"],
        summary=row["summary"], body=row["body"], tags=json.loads(row["tags"]), score=int(row["score"]),
        comments=int(row["comments"]), published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        discovered_at=datetime.fromisoformat(row["discovered_at"]), metadata=json.loads(row["metadata"]),
    )


def _analysis_from_row(row: sqlite3.Row) -> ProblemAnalysis:
    return ProblemAnalysis(
        pain_point=row["pain_point"], audience=row["audience"], root_cause=row["root_cause"],
        solution_angle=row["solution_angle"], hooks=json.loads(row["hooks"]), risks=json.loads(row["risks"]),
        confidence=int(row["confidence"]), category=row["category"], intent=row["intent"],
        sentiment=row["sentiment"], severity=int(row["severity"]), frequency_signal=int(row["frequency_signal"]),
        trend_signal=int(row["trend_signal"]), content_gap=int(row["content_gap"]),
        opportunity_score=int(row["opportunity_score"]), trend_label=row["trend_label"],
        related_topics=json.loads(row["related_topics"]), recommended_formats=json.loads(row["recommended_formats"]),
        evidence=json.loads(row["evidence"]),
    )


def _save_analysis(connection: sqlite3.Connection, problem_id: int, analysis: ProblemAnalysis, score: int, duplicate_of: int | None, cluster_id: int | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute("""INSERT INTO ai_intelligence
        (problem_id, category, intent, sentiment, severity, frequency_signal, trend_signal, content_gap,
         opportunity_score, trend_label, pain_point, audience, root_cause, solution_angle, hooks, risks,
         related_topics, recommended_formats, evidence, confidence, duplicate_of, cluster_id, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(problem_id) DO UPDATE SET category=excluded.category, intent=excluded.intent,
        sentiment=excluded.sentiment, severity=excluded.severity, frequency_signal=excluded.frequency_signal,
        trend_signal=excluded.trend_signal, content_gap=excluded.content_gap, opportunity_score=excluded.opportunity_score,
        trend_label=excluded.trend_label, pain_point=excluded.pain_point, audience=excluded.audience,
        root_cause=excluded.root_cause, solution_angle=excluded.solution_angle, hooks=excluded.hooks,
        risks=excluded.risks, related_topics=excluded.related_topics, recommended_formats=excluded.recommended_formats,
        evidence=excluded.evidence, confidence=excluded.confidence, duplicate_of=excluded.duplicate_of,
        cluster_id=excluded.cluster_id, analyzed_at=excluded.analyzed_at""",
        (problem_id, analysis.category, analysis.intent, analysis.sentiment, analysis.severity,
         analysis.frequency_signal, analysis.trend_signal, analysis.content_gap, score, analysis.trend_label,
         analysis.pain_point, analysis.audience, analysis.root_cause, analysis.solution_angle,
         json.dumps(analysis.hooks, ensure_ascii=False), json.dumps(analysis.risks, ensure_ascii=False),
         json.dumps(analysis.related_topics, ensure_ascii=False), json.dumps(analysis.recommended_formats, ensure_ascii=False),
         json.dumps(analysis.evidence, ensure_ascii=False), analysis.confidence, duplicate_of, cluster_id, now),
    )


def _cluster_signature(problem: Problem, analysis: ProblemAnalysis) -> str:
    return " ".join([problem.title, analysis.pain_point, *analysis.related_topics])


def _existing_canonical(connection: sqlite3.Connection) -> list[tuple[int, Problem, ProblemAnalysis]]:
    rows = connection.execute("""
        SELECT i.*, p.source, p.external_id, p.title, p.url, p.summary, p.body, p.tags, p.score,
               p.comments, p.published_at, p.discovered_at, p.metadata
        FROM ai_intelligence i JOIN problems p ON p.id=i.problem_id
        WHERE i.duplicate_of IS NULL
        ORDER BY p.discovered_at DESC
    """).fetchall()
    return [(int(row["problem_id"]), _problem(row), _analysis_from_row(row)) for row in rows]


def _assign_cluster(connection: sqlite3.Connection, problem: Problem, analysis: ProblemAnalysis) -> int:
    signature = _cluster_signature(problem, analysis)
    existing = connection.execute("""
        SELECT i.cluster_id, p.title, i.pain_point, i.related_topics
        FROM ai_intelligence i JOIN problems p ON p.id=i.problem_id
        WHERE i.cluster_id IS NOT NULL
        ORDER BY i.analyzed_at DESC
    """).fetchall()
    best_cluster = None
    best_similarity = 0.0
    for row in existing:
        related = json.loads(row["related_topics"] or "[]")
        similarity = semantic_similarity(signature, " ".join([row["title"], row["pain_point"], *related]))
        if similarity >= 0.34 and similarity > best_similarity:
            best_cluster, best_similarity = int(row["cluster_id"]), similarity
    if best_cluster is not None:
        return best_cluster

    now = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        "INSERT INTO ai_clusters (label, summary, member_count, opportunity_score, trend_label, content_angle, created_at, updated_at) VALUES (?, ?, 0, 0, ?, ?, ?, ?)",
        (analysis.pain_point[:160] or problem.title[:160], "Incremental research cluster", analysis.trend_label, analysis.solution_angle, now, now),
    )
    return int(cursor.lastrowid)


def _refresh_cluster(connection: sqlite3.Connection, cluster_id: int) -> None:
    rows = connection.execute("""
        SELECT i.*, p.source, p.external_id, p.title, p.url, p.summary, p.body, p.tags, p.score,
               p.comments, p.published_at, p.discovered_at, p.metadata
        FROM ai_intelligence i JOIN problems p ON p.id=i.problem_id
        WHERE i.cluster_id=?
    """, (cluster_id,)).fetchall()
    if not rows:
        return
    analyses = [_analysis_from_row(row) for row in rows]
    opportunities = [int(row["opportunity_score"]) for row in rows]
    trend = Counter(a.trend_label for a in analyses).most_common(1)[0][0]
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "UPDATE ai_clusters SET member_count=?, opportunity_score=?, trend_label=?, content_angle=?, updated_at=? WHERE id=?",
        (len(rows), round(sum(opportunities) / len(opportunities)), trend, analyses[0].solution_angle, now, cluster_id),
    )


def run_intelligence(settings: Settings, limit: int = 100, client_factory: Callable[[Settings], AIAnalysisClient] | None = None) -> IntelligenceResult:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    result = IntelligenceResult()
    client = (client_factory or create_ai_client)(settings)
    connection = connect(settings.database_url)
    try:
        _ensure_schema(connection)
        rows = connection.execute("""
            SELECT p.* FROM problems p
            LEFT JOIN ai_intelligence i ON i.problem_id=p.id
            WHERE i.problem_id IS NULL
            ORDER BY p.score DESC, p.discovered_at DESC LIMIT ?
        """, (limit,)).fetchall()
        result.processed = len(rows)
        result.skipped = connection.execute("SELECT COUNT(*) FROM problems p JOIN ai_intelligence i ON i.problem_id=p.id").fetchone()[0]
        if not rows:
            return result

        existing = _existing_canonical(connection)
        problems_by_id = {int(row["id"]): _problem(row) for row in rows}
        canonical_new: list[tuple[int, Problem]] = []
        duplicate_map: dict[int, int] = {}
        for row in rows:
            pid = int(row["id"])
            problem = problems_by_id[pid]
            duplicate_of = next((cid for cid, cp, _ in existing + [(nid, np, None) for nid, np in canonical_new] if semantic_similarity(problem.title, cp.title) >= 0.72), None)
            if duplicate_of is None:
                canonical_new.append((pid, problem))
            else:
                duplicate_map[pid] = duplicate_of
                result.duplicates += 1

        analyses: dict[int, ProblemAnalysis] = {}
        for pid, problem in canonical_new:
            try:
                analyses[pid] = client.analyze(problem)
                result.analyzed += 1
            except Exception:
                result.failed += 1

        cluster_for: dict[int, int] = {}
        for pid, analysis in analyses.items():
            cluster_id = _assign_cluster(connection, problems_by_id[pid], analysis)
            cluster_for[pid] = cluster_id
            _save_analysis(connection, pid, analysis, opportunity_score(problems_by_id[pid], analysis, 1), None, cluster_id)

        for pid, canonical_id in duplicate_map.items():
            analysis = analyses.get(canonical_id)
            if analysis is None and canonical_id in {cid for cid, _, _ in existing}:
                analysis = next(a for cid, _, a in existing if cid == canonical_id)
            if analysis is not None:
                cluster_id = cluster_for.get(canonical_id)
                if cluster_id is None:
                    cluster_id = next((cluster for cid, cluster in [(cid, row["cluster_id"]) for row in connection.execute("SELECT problem_id, cluster_id FROM ai_intelligence WHERE problem_id=?", (canonical_id,)).fetchall()] if cid == canonical_id), None)
                _save_analysis(connection, pid, analysis, opportunity_score(problems_by_id[pid], analysis, 1), canonical_id, int(cluster_id) if cluster_id else None)

        for cluster_id in set(cluster_for.values()) | {int(row["cluster_id"]) for row in connection.execute("SELECT cluster_id FROM ai_intelligence WHERE cluster_id IS NOT NULL AND problem_id IN (SELECT problem_id FROM ai_intelligence WHERE analyzed_at >= datetime('now','-1 day'))").fetchall()}:
            _refresh_cluster(connection, cluster_id)
        result.clusters = connection.execute("SELECT COUNT(*) FROM ai_clusters").fetchone()[0]
        result.assignments = sum(1 for pid in analyses if cluster_for.get(pid) is not None)
        result.opportunities = sum(1 for pid, analysis in analyses.items() if opportunity_score(problems_by_id[pid], analysis, 1) >= 70)
        connection.commit()
    finally:
        connection.close()
    return result


def list_intelligence(settings: Settings, limit: int = 100) -> list[dict]:
    connection = connect(settings.database_url)
    try:
        rows = connection.execute("SELECT i.*, p.source, p.title, p.url, p.comments, p.score FROM ai_intelligence i JOIN problems p ON p.id=i.problem_id ORDER BY i.opportunity_score DESC, p.discovered_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()


def list_clusters(settings: Settings, limit: int = 50) -> list[dict]:
    connection = connect(settings.database_url)
    try:
        rows = connection.execute("SELECT * FROM ai_clusters ORDER BY opportunity_score DESC, member_count DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally: connection.close()
