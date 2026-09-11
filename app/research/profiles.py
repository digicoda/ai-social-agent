"""Lightweight multi-profile research configuration."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..database import connect

PROFILE_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_profiles (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, main_category TEXT NOT NULL,
 website_url TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', industry TEXT NOT NULL DEFAULT '',
 audience TEXT NOT NULL DEFAULT '', topics TEXT NOT NULL DEFAULT '[]', keywords TEXT NOT NULL DEFAULT '[]',
 competitors TEXT NOT NULL DEFAULT '[]', services TEXT NOT NULL DEFAULT '[]', sources TEXT NOT NULL DEFAULT '[]',
 intents TEXT NOT NULL DEFAULT '[]', language TEXT NOT NULL DEFAULT 'English', tone TEXT NOT NULL DEFAULT 'professional',
 posting_times TEXT NOT NULL DEFAULT '["09:00","18:00"]', timezone TEXT NOT NULL DEFAULT 'UTC',
 research_mode TEXT NOT NULL DEFAULT 'monitoring', research_interval_hours INTEGER NOT NULL DEFAULT 24,
 enabled INTEGER NOT NULL DEFAULT 1, auto_generate INTEGER NOT NULL DEFAULT 0, auto_publish INTEGER NOT NULL DEFAULT 0,
 platforms TEXT NOT NULL DEFAULT '["linkedin"]', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_research_profiles_enabled ON research_profiles(enabled);
"""

REQUIRED = {"name", "main_category"}
OPTIONAL = {"website_url", "description", "industry", "audience", "topics", "keywords", "competitors", "services", "sources", "intents", "language", "tone", "posting_times", "timezone", "research_mode", "research_interval_hours", "enabled", "auto_generate", "auto_publish", "platforms"}


def _db(database_url: str):
    db = connect(database_url)
    db.executescript(PROFILE_SCHEMA)
    db.commit()
    return db


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def _decode(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ("topics", "keywords", "competitors", "services", "sources", "intents", "posting_times", "platforms"):
        try: item[key] = json.loads(item.get(key) or "[]")
        except (TypeError, json.JSONDecodeError): item[key] = []
    for key in ("enabled", "auto_generate", "auto_publish"): item[key] = bool(item[key])
    return item


def list_profiles(database_url: str, enabled_only: bool = False) -> list[dict[str, Any]]:
    db = _db(database_url)
    try:
        sql = "SELECT * FROM research_profiles" + (" WHERE enabled = 1" if enabled_only else "") + " ORDER BY created_at ASC, id ASC"
        return [_decode(row) for row in db.execute(sql).fetchall()]
    finally: db.close()


def get_profile(database_url: str, profile_id: int) -> dict[str, Any] | None:
    db = _db(database_url)
    try:
        row = db.execute("SELECT * FROM research_profiles WHERE id = ?", (profile_id,)).fetchone()
        return _decode(row) if row else None
    finally: db.close()


def save_profile(database_url: str, values: dict[str, Any], profile_id: int | None = None) -> dict[str, Any]:
    missing = [key for key in REQUIRED if not str(values.get(key, "")).strip()]
    if missing: raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")
    unknown = set(values) - REQUIRED - OPTIONAL
    if unknown: raise ValueError(f"Unknown profile fields: {', '.join(sorted(unknown))}")
    defaults = {"website_url":"", "description":"", "industry":"", "audience":"", "topics":[], "keywords":[], "competitors":[], "services":[], "sources":["github","reddit","stackoverflow","rss"], "intents":["problems","questions","trends"], "language":"English", "tone":"professional", "posting_times":["09:00","18:00"], "timezone":"UTC", "research_mode":"monitoring", "research_interval_hours":24, "enabled":True, "auto_generate":False, "auto_publish":False, "platforms":["linkedin"]}
    merged = {**defaults, **values}
    db = _db(database_url); now = datetime.now(timezone.utc).isoformat()
    args = (merged["name"].strip(), merged["main_category"].strip(), merged["website_url"].strip(), merged["description"], merged["industry"], merged["audience"], _json(merged["topics"]), _json(merged["keywords"]), _json(merged["competitors"]), _json(merged["services"]), _json(merged["sources"]), _json(merged["intents"]), merged["language"], merged["tone"], _json(merged["posting_times"]), merged["timezone"], merged["research_mode"], max(1, int(merged["research_interval_hours"])), int(bool(merged["enabled"])), int(bool(merged["auto_generate"])), int(bool(merged["auto_publish"])), _json(merged["platforms"]), now)
    try:
        if profile_id is None:
            cur = db.execute("INSERT INTO research_profiles (name,main_category,website_url,description,industry,audience,topics,keywords,competitors,services,sources,intents,language,tone,posting_times,timezone,research_mode,research_interval_hours,enabled,auto_generate,auto_publish,platforms,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", args + (now,))
            profile_id = int(cur.lastrowid)
        else:
            if not db.execute("SELECT 1 FROM research_profiles WHERE id=?", (profile_id,)).fetchone(): raise ValueError("Profile not found")
            db.execute("UPDATE research_profiles SET name=?,main_category=?,website_url=?,description=?,industry=?,audience=?,topics=?,keywords=?,competitors=?,services=?,sources=?,intents=?,language=?,tone=?,posting_times=?,timezone=?,research_mode=?,research_interval_hours=?,enabled=?,auto_generate=?,auto_publish=?,platforms=?,updated_at=? WHERE id=?", args + (profile_id,))
        db.commit()
        return _decode(db.execute("SELECT * FROM research_profiles WHERE id=?", (profile_id,)).fetchone())
    finally: db.close()


def delete_profile(database_url: str, profile_id: int) -> bool:
    db = _db(database_url)
    try:
        cur = db.execute("DELETE FROM research_profiles WHERE id=?", (profile_id,)); db.commit(); return cur.rowcount == 1
    finally: db.close()
