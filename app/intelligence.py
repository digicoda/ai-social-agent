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


def _problem_rows(connection: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return connection.execute("SELECT * FROM problems ORDER BY score DESC, discovered_at DESC LIMIT ?", (limit,)).fetchall()


def _problem(row: sqlite3.Row) -> Problem:
    return Problem(
        source=row["source"], external_id=row["external_id"], title=row["title"], url=row["url"],
        summary=row["summary"], body=row["body"], tags=json.loads(row["tags"]), score=int(row["score"]),
        comments=int(row["comments"]), published_at=datetime.fromisoformat(row["published_at"]) if row["published_at"] else None,
        discovered_at=datetime.fromisoformat(row["discovered_at"]), metadata=json.loads(row["metadata"]),
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


def run_intelligence(settings: Settings, limit: int = 100, client_factory: Callable[[Settings], AIAnalysisClient] | None = None) -> IntelligenceResult:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    result = IntelligenceResult()
    client = (client_factory or create_ai_client)(settings)
    connection = connect(settings.database_url)
    try:
        _ensure_schema(connection)
        rows = _problem_rows(connection, limit)
        canonical: list[tuple[int, Problem]] = []
        duplicate_map: dict[int, int] = {}
        problems_by_id = {int(row["id"]): _problem(row) for row in rows}
        for row in rows:
            pid = int(row["id"]); problem = problems_by_id[pid]; result.processed += 1
            duplicate_of = next((cid for cid, cp in canonical if semantic_similarity(problem.title, cp.title) >= 0.72), None)
            if duplicate_of is None: canonical.append((pid, problem))
            else: duplicate_map[pid] = duplicate_of; result.duplicates += 1

        analyses: dict[int, ProblemAnalysis] = {}
        for pid, problem in canonical:
            try:
                analyses[pid] = client.analyze(problem); result.analyzed += 1
            except Exception:
                result.failed += 1

        groups: list[dict] = []
        for pid, analysis in analyses.items():
            problem = problems_by_id[pid]; signature = " ".join([problem.title, analysis.pain_point, *analysis.related_topics])
            chosen = None; best = 0.0
            for group in groups:
                sim = semantic_similarity(signature, group["signature"])
                if sim >= 0.34 and sim > best: chosen, best = group, sim
            if chosen is None:
                chosen = {"signature": signature, "members": [], "analyses": []}; groups.append(chosen)
            chosen["members"].append(pid); chosen["analyses"].append(analysis)

        connection.execute("DELETE FROM ai_clusters")
        now = datetime.now(timezone.utc).isoformat(); cluster_for: dict[int, int] = {}
        for group in groups:
            members = group["members"]; analyses_in_group = group["analyses"]
            label = analyses_in_group[0].pain_point[:160] or problems_by_id[members[0]].title[:160]
            avg_score = round(sum(opportunity_score(problems_by_id[pid], analyses[pid], len(members)) for pid in members) / len(members))
            trend = Counter(a.trend_label for a in analyses_in_group).most_common(1)[0][0]
            intent = Counter(a.intent for a in analyses_in_group).most_common(1)[0][0]
            cursor = connection.execute("INSERT INTO ai_clusters (label, summary, member_count, opportunity_score, trend_label, content_angle, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (label, f"{len(members)} related research items; dominant intent: {intent}", len(members), avg_score, trend, analyses_in_group[0].solution_angle, now, now))
            cluster_id = int(cursor.lastrowid); result.clusters += 1; result.assignments += len(members)
            if avg_score >= 70: result.opportunities += 1
            for pid in members: cluster_for[pid] = cluster_id

        for pid, analysis in analyses.items():
            cluster_size = sum(1 for member in cluster_for if cluster_for[member] == cluster_for[pid])
            _save_analysis(connection, pid, analysis, opportunity_score(problems_by_id[pid], analysis, cluster_size), None, cluster_for.get(pid))
        for pid, canonical_id in duplicate_map.items():
            if canonical_id in analyses:
                analysis = analyses[canonical_id]
                _save_analysis(connection, pid, analysis, opportunity_score(problems_by_id[canonical_id], analysis), canonical_id, cluster_for.get(canonical_id))
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
