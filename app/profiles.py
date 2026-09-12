from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
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
    "timezone": "UTC",
    "publish_provider": "linkedin",
    "auto_publish": False,
    "ai_provider": "gemini",
    "ai_model": "gemini-2.5-flash",
    "content_limit": 10,
    "time_range": "7d",
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
    if isinstance(config, dict): value.update(config)
    value["categories"] = [str(x) for x in value.get("categories", []) if str(x)] or list(DEFAULT_PROFILE["categories"])
    value["sources"] = [str(x) for x in value.get("sources", []) if str(x) in {"github", "reddit", "stackoverflow", "rss", "web"}] or list(DEFAULT_PROFILE["sources"])
    value["automation_mode"] = "auto" if value.get("automation_mode") == "auto" else "manual"
    value["approval_mode"] = "auto" if value.get("approval_mode") == "auto" else "human"
    value["ai_provider"] = str(value.get("ai_provider") or "gemini").lower()
    if value["ai_provider"] not in {"gemini", "openai", "huggingface"}: value["ai_provider"] = "gemini"
    return value


def _profile_db_url(database_url: str, profile_id: int) -> str:
    path = Path("data") / "profiles" / f"profile-{profile_id}.db"
    return f"sqlite:///{path.as_posix()}"


def list_profiles(database_url: str) -> list[dict[str, Any]]:
    db = connect(database_url)
    try:
        _ensure(db)
        rows = db.execute("SELECT * FROM automation_profiles ORDER BY name COLLATE NOCASE").fetchall()
        return [{"id": int(r["id"]), "name": r["name"], "config": _merged(json.loads(r["config"])), "enabled": bool(r["enabled"]), "next_run": r["next_run"], "last_run": r["last_run"], "last_status": r["last_status"]} for r in rows]
    finally: db.close()


def get_profile(database_url: str, profile_id: int) -> dict[str, Any] | None:
    item = next((p for p in list_profiles(database_url) if p["id"] == profile_id), None)
    if item:
        item["database_url"] = _profile_db_url(database_url, profile_id)
    return item


def save_profile(database_url: str, name: str, config: dict[str, Any], profile_id: int | None = None, enabled: bool = True) -> dict[str, Any]:
    name = name.strip()
    if not name or len(name) > 100: raise ValueError("profile name is required")
    value = _merged(config)
    now = datetime.now(timezone.utc).isoformat()
    db = connect(database_url)
    try:
        _ensure(db)
        if profile_id:
            existing = db.execute("SELECT id FROM automation_profiles WHERE id=?", (profile_id,)).fetchone()
            if not existing: raise ValueError("profile not found")
            db.execute("UPDATE automation_profiles SET name=?, config=?, enabled=?, updated_at=? WHERE id=?", (name, json.dumps(value), int(enabled), now, profile_id))
        else:
            cur = db.execute("INSERT INTO automation_profiles (name, config, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (name, json.dumps(value), int(enabled), now, now))
            profile_id = int(cur.lastrowid)
        db.commit()
        profile = get_profile(database_url, int(profile_id))
        # Initialize the isolated profile database immediately so persistence is real, not UI-only.
        connect(profile["database_url"]).close()
        return profile
    except Exception as exc:
        db.rollback()
        if "UNIQUE" in str(exc).upper(): raise ValueError("profile name already exists") from exc
        raise
    finally: db.close()


def delete_profile(database_url: str, profile_id: int) -> bool:
    db = connect(database_url)
    try:
        _ensure(db)
        cur = db.execute("DELETE FROM automation_profiles WHERE id=?", (profile_id,))
        db.commit()
        if cur.rowcount == 1:
            path = Path(_profile_db_url(database_url, profile_id).replace("sqlite:///", ""))
            if path.exists(): path.unlink()
            return True
        return False
    finally: db.close()


def due_profiles(database_url: str, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    db = connect(database_url)
    try:
        _ensure(db)
        rows = db.execute("SELECT * FROM automation_profiles WHERE enabled=1 AND config LIKE '%\"automation_mode\": \"auto\"%' AND (next_run IS NULL OR next_run <= ?)", (now.isoformat(),)).fetchall()
        result = []
        for r in rows:
            result.append({"id": int(r["id"]), "name": r["name"], "config": _merged(json.loads(r["config"])), "enabled": True, "next_run": r["next_run"], "last_run": r["last_run"], "last_status": r["last_status"], "database_url": _profile_db_url(database_url, int(r["id"]))})
        return result
    finally: db.close()


def mark_profile_run(database_url: str, profile_id: int, status: str, next_run: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db = connect(database_url)
    try:
        _ensure(db)
        db.execute("UPDATE automation_profiles SET last_run=?, last_status=?, next_run=?, updated_at=? WHERE id=?", (now, status, next_run, now, profile_id))
        db.commit()
    finally: db.close()
