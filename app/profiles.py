from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .database import connect

DEFAULT_PROFILE = {
    "categories": ["technology", "ai", "marketing"],
    "sources": ["github", "reddit", "stackoverflow", "rss"],
    "query": "",
    "research_limit": 25,
    "automation_mode": "manual",
    "approval_mode": "human",
    "daily_time": "09:00",
    "publish_provider": "linkedin",
    "auto_publish": False,
    "ai_provider": "gemini",
    "ai_model": "gemini-2.5-flash",
}


def _ensure(connection):
    connection.execute("""CREATE TABLE IF NOT EXISTS automation_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        config TEXT NOT NULL DEFAULT '{}',
        enabled INTEGER NOT NULL DEFAULT 1,
        next_run TEXT,
        last_run TEXT,
        last_status TEXT NOT NULL DEFAULT 'never',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    connection.commit()


def _merged(config: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(DEFAULT_PROFILE)
    if isinstance(config, dict):
        value.update(config)
    value["categories"] = [str(x) for x in value.get("categories", []) if str(x)] or list(DEFAULT_PROFILE["categories"])
    value["sources"] = [str(x) for x in value.get("sources", []) if str(x) in {"github", "reddit", "stackoverflow", "rss"}] or list(DEFAULT_PROFILE["sources"])
    value["automation_mode"] = "auto" if value.get("automation_mode") == "auto" else "manual"
    value["approval_mode"] = "auto" if value.get("approval_mode") == "auto" else "human"
    return value


def list_profiles(database_url: str) -> list[dict[str, Any]]:
    db = connect(database_url)
    try:
        _ensure(db)
        rows = db.execute("SELECT * FROM automation_profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [{"id": int(r["id"]), "name": r["name"], "config": _merged(json.loads(r["config"])), "enabled": bool(r["enabled"]), "next_run": r["next_run"], "last_run": r["last_run"], "last_status": r["last_status"]} for r in rows]
    finally:
        db.close()


def get_profile(database_url: str, profile_id: int) -> dict[str, Any] | None:
    return next((p for p in list_profiles(database_url) if p["id"] == profile_id), None)


def save_profile(database_url: str, name: str, config: dict[str, Any], profile_id: int | None = None, enabled: bool = True) -> dict[str, Any]:
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("profile name is required")
    value = _merged(config)
    now = datetime.now(timezone.utc).isoformat()
    db = connect(database_url)
    try:
        _ensure(db)
        if profile_id:
            db.execute("UPDATE automation_profiles SET name=?, config=?, enabled=?, updated_at=? WHERE id=?", (name, json.dumps(value), int(enabled), now, profile_id))
        else:
            db.execute("INSERT INTO automation_profiles (name, config, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (name, json.dumps(value), int(enabled), now, now))
        db.commit()
        row = db.execute("SELECT id FROM automation_profiles WHERE name=?", (name,)).fetchone()
        return get_profile(database_url, int(row["id"]))
    except Exception as exc:
        db.rollback()
        if "UNIQUE" in str(exc).upper():
            raise ValueError("profile name already exists") from exc
        raise
    finally:
        db.close()


def delete_profile(database_url: str, profile_id: int) -> bool:
    db = connect(database_url)
    try:
        _ensure(db)
        cur = db.execute("DELETE FROM automation_profiles WHERE id=?", (profile_id,))
        db.commit()
        return cur.rowcount == 1
    finally:
        db.close()


def due_profiles(database_url: str, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    db = connect(database_url)
    try:
        _ensure(db)
        rows = db.execute("SELECT * FROM automation_profiles WHERE enabled=1 AND config LIKE '%\"automation_mode\": \"auto\"%' AND (next_run IS NULL OR next_run <= ?)", (now.isoformat(),)).fetchall()
        return [{"id": int(r["id"]), "name": r["name"], "config": _merged(json.loads(r["config"])), "enabled": True, "next_run": r["next_run"], "last_run": r["last_run"], "last_status": r["last_status"]} for r in rows]
    finally:
        db.close()


def mark_profile_run(database_url: str, profile_id: int, status: str, next_run: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db = connect(database_url)
    try:
        _ensure(db)
        db.execute("UPDATE automation_profiles SET last_run=?, last_status=?, next_run=?, updated_at=? WHERE id=?", (now, status, next_run, now, profile_id))
        db.commit()
    finally:
        db.close()
