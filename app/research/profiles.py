"""Lightweight multi-profile research configuration.

A profile represents one research/content persona. Only name and main_category
are required; everything else is optional and stored as JSON in SQLite.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..database import connect

REQUIRED = {"name", "main_category"}
OPTIONAL = {
    "website_url", "description", "industry", "audience", "topics", "keywords",
    "competitors", "services", "sources", "intents", "language", "tone",
    "posting_times", "timezone", "research_mode", "research_interval_hours",
    "enabled", "auto_generate", "auto_publish", "platforms",
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def _decode(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ("topics", "keywords", "competitors", "services", "sources", "intents", "posting_times", "platforms"):
        try:
            item[key] = json.loads(item.get(key) or "[]")
        except (TypeError, json.JSONDecodeError):
            item[key] = []
    item["enabled"] = bool(item["enabled"])
    item["auto_generate"] = bool(item["auto_generate"])
    item["auto_publish"] = bool(item["auto_publish"])
    return item


def list_profiles(database_url: str, enabled_only: bool = False) -> list[dict[str, Any]]:
    db = connect(database_url)
    try:
        sql = "SELECT * FROM research_profiles"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY created_at ASC, id ASC"
        return [_decode(row) for row in db.execute(sql).fetchall()]
    finally:
        db.close()


def get_profile(database_url: str, profile_id: int) -> dict[str, Any] | None:
    db = connect(database_url)
    try:
        row = db.execute("SELECT * FROM research_profiles WHERE id = ?", (profile_id,)).fetchone()
        return _decode(row) if row else None
    finally:
        db.close()


def save_profile(database_url: str, values: dict[str, Any], profile_id: int | None = None) -> dict[str, Any]:
    missing = [key for key in REQUIRED if not str(values.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")
    unknown = set(values) - REQUIRED - OPTIONAL
    if unknown:
        raise ValueError(f"Unknown profile fields: {', '.join(sorted(unknown))}")
    db = connect(database_url)
    now = datetime.now(timezone.utc).isoformat()
    try:
        defaults = {
            "website_url": "", "description": "", "industry": "", "audience": "",
            "topics": [], "keywords": [], "competitors": [], "services": [],
            "sources": ["github", "reddit", "stackoverflow", "rss"],
            "intents": ["problems", "questions", "trends"], "language": "English",
            "tone": "professional", "posting_times": ["09:00", "18:00"],
            "timezone": "UTC", "research_mode": "monitoring",
            "research_interval_hours": 24, "enabled": True, "auto_generate": False,
            "auto_publish": False, "platforms": ["linkedin"],
        }
        merged = {**defaults, **values}
        if profile_id is None:
            cur = db.execute(
                """INSERT INTO research_profiles
                (name, main_category, website_url, description, industry, audience, topics, keywords,
                 competitors, services, sources, intents, language, tone, posting_times, timezone,
                 research_mode, research_interval_hours, enabled, auto_generate, auto_publish, platforms,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (merged["name"].strip(), merged["main_category"].strip(), merged["website_url"].strip(),
                 merged["description"], merged["industry"], merged["audience"], _json(merged["topics"]),
                 _json(merged["keywords"]), _json(merged["competitors"]), _json(merged["services"]),
                 _json(merged["sources"]), _json(merged["intents"]), merged["language"], merged["tone"],
                 _json(merged["posting_times"]), merged["timezone"], merged["research_mode"],
                 max(1, int(merged["research_interval_hours"])), int(bool(merged["enabled"])),
                 int(bool(merged["auto_generate"])), int(bool(merged["auto_publish"])), _json(merged["platforms"]), now, now),
            )
            profile_id = int(cur.lastrowid)
        else:
            if not db.execute("SELECT 1 FROM research_profiles WHERE id = ?", (profile_id,)).fetchone():
                raise ValueError("Profile not found")
            db.execute(
                """UPDATE research_profiles SET name=?, main_category=?, website_url=?, description=?, industry=?,
                audience=?, topics=?, keywords=?, competitors=?, services=?, sources=?, intents=?, language=?, tone=?,
                posting_times=?, timezone=?, research_mode=?, research_interval_hours=?, enabled=?, auto_generate=?,
                auto_publish=?, platforms=?, updated_at=? WHERE id=?""",
                (merged["name"].strip(), merged["main_category"].strip(), merged["website_url"].strip(),
                 merged["description"], merged["industry"], merged["audience"], _json(merged["topics"]),
                 _json(merged["keywords"]), _json(merged["competitors"]), _json(merged["services"]),
                 _json(merged["sources"]), _json(merged["intents"]), merged["language"], merged["tone"],
                 _json(merged["posting_times"]), merged["timezone"], merged["research_mode"],
                 max(1, int(merged["research_interval_hours"])), int(bool(merged["enabled"])),
                 int(bool(merged["auto_generate"])), int(bool(merged["auto_publish"])), _json(merged["platforms"]), now, profile_id),
            )
        db.commit()
        return _decode(db.execute("SELECT * FROM research_profiles WHERE id = ?", (profile_id,)).fetchone())
    finally:
        db.close()


def delete_profile(database_url: str, profile_id: int) -> bool:
    db = connect(database_url)
    try:
        cur = db.execute("DELETE FROM research_profiles WHERE id = ?", (profile_id,))
        db.commit()
        return cur.rowcount == 1
    finally:
        db.close()
