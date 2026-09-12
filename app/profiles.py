from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

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
VALID_SOURCES = {"github", "reddit", "stackoverflow", "rss", "web"}
VALID_PROVIDERS = {"gemini", "openai", "huggingface"}


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
    value["categories"] = [str(x).strip() for x in value.get("categories", []) if str(x).strip()] or list(DEFAULT_PROFILE["categories"])
    value["sources"] = [str(x).strip().lower() for x in value.get("sources", []) if str(x).strip().lower() in VALID_SOURCES] or list(DEFAULT_PROFILE["sources"])
    value["automation_mode"] = "auto" if value.get("automation_mode") == "auto" else "manual"
    value["approval_mode"] = "auto" if value.get("approval_mode") == "auto" else "human"
    value["ai_provider"] = str(value.get("ai_provider") or "gemini").lower()
    if value["ai_provider"] not in VALID_PROVIDERS:
        value["ai_provider"] = "gemini"
    daily = str(value.get("daily_time") or "09:00")
    try:
        hour, minute = [int(x) for x in daily.split(":", 1)]
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        value["daily_time"] = f"{hour:02d}:{minute:02d}"
    except (ValueError, TypeError):
        raise ValueError("daily_time must use HH:MM (00:00-23:59)")
    tz_name = str(value.get("timezone") or "UTC")
    try:
        ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError("invalid timezone") from exc
    value["timezone"] = tz_name
    value["research_limit"] = min(max(int(value.get("research_limit") or 25), 1), 100)
    value["content_limit"] = min(max(int(value.get("content_limit") or 10), 1), 50)
    value["auto_publish"] = bool(value.get("auto_publish", False))
    return value


def _profile_db_url(database_url: str, profile_id: int) -> str:
    path = Path("data") / "profiles" / f"profile-{profile_id}.db"
    return f"sqlite:///{path.as_posix()}"


def next_profile_run(profile: dict[str, Any], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    cfg = profile.get("config") or {}
    try:
        tz = ZoneInfo(str(cfg.get("timezone") or "UTC"))
    except Exception:
        tz = timezone.utc
    local = now.astimezone(tz)
    hour, minute = [int(x) for x in str(cfg.get("daily_time") or "09:00").split(":", 1)]
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


def _row_to_profile(row, database_url: str) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "config": _merged(json.loads(row["config"] or "{}")),
        "enabled": bool(row["enabled"]),
        "next_run": row["next_run"],
        "last_run": row["last_run"],
        "last_status": row["last_status"],
        "database_url": _profile_db_url(database_url, int(row["id"])),
    }


def list_profiles(database_url: str) -> list[dict[str, Any]]:
    db = connect(database_url)
    try:
        _ensure(db)
        return [_row_to_profile(r, database_url) for r in db.execute("SELECT * FROM automation_profiles ORDER BY name COLLATE NOCASE").fetchall()]
    finally:
        db.close()


def get_profile(database_url: str, profile_id: int) -> dict[str, Any] | None:
    db = connect(database_url)
    try:
        _ensure(db)
        row = db.execute("SELECT * FROM automation_profiles WHERE id=?", (profile_id,)).fetchone()
        return _row_to_profile(row, database_url) if row else None
    finally:
        db.close()


def save_profile(database_url: str, name: str, config: dict[str, Any], profile_id: int | None = None, enabled: bool = True) -> dict[str, Any]:
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("profile name is required")
    value = _merged(config)
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    next_run = next_profile_run({"config": value}, now) if enabled and value["automation_mode"] == "auto" else None
    db = connect(database_url)
    try:
        _ensure(db)
        if profile_id:
            if not db.execute("SELECT id FROM automation_profiles WHERE id=?", (profile_id,)).fetchone():
                raise ValueError("profile not found")
            db.execute("UPDATE automation_profiles SET name=?, config=?, enabled=?, next_run=?, updated_at=? WHERE id=?", (name, json.dumps(value), int(enabled), next_run, now_text, profile_id))
        else:
            cur = db.execute("INSERT INTO automation_profiles (name, config, enabled, next_run, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", (name, json.dumps(value), int(enabled), next_run, now_text, now_text))
            profile_id = int(cur.lastrowid)
        db.commit()
        profile = get_profile(database_url, int(profile_id))
        connect(profile["database_url"]).close()
        return profile
    except Exception as exc:
        db.rollback()
        if "UNIQUE" in str(exc).upper():
            raise ValueError("profile name already exists") from exc
        raise
    finally:
        db.close()


def set_profile_enabled(database_url: str, profile_id: int, enabled: bool) -> dict[str, Any] | None:
    profile = get_profile(database_url, profile_id)
    if not profile:
        return None
    next_run = next_profile_run(profile) if enabled and profile["config"]["automation_mode"] == "auto" else None
    db = connect(database_url)
    try:
        _ensure(db)
        now = datetime.now(timezone.utc).isoformat()
        db.execute("UPDATE automation_profiles SET enabled=?, next_run=?, updated_at=? WHERE id=?", (int(enabled), next_run, now, profile_id))
        db.commit()
    finally:
        db.close()
    return get_profile(database_url, profile_id)


def delete_profile(database_url: str, profile_id: int) -> bool:
    db = connect(database_url)
    try:
        _ensure(db)
        cur = db.execute("DELETE FROM automation_profiles WHERE id=?", (profile_id,))
        db.commit()
        if cur.rowcount == 1:
            path = Path(_profile_db_url(database_url, profile_id).replace("sqlite:///", ""))
            if path.exists():
                path.unlink()
            return True
        return False
    finally:
        db.close()


def due_profiles(database_url: str, now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    return [p for p in list_profiles(database_url) if p["enabled"] and p["config"]["automation_mode"] == "auto" and (p["next_run"] is None or p["next_run"] <= now.isoformat())]


def mark_profile_run(database_url: str, profile_id: int, status: str, next_run: str | None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db = connect(database_url)
    try:
        _ensure(db)
        db.execute("UPDATE automation_profiles SET last_run=?, last_status=?, next_run=?, updated_at=? WHERE id=?", (now, status, next_run, now, profile_id))
        db.commit()
    finally:
        db.close()
