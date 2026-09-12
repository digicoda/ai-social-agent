from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import Settings
from .content_workflow import generate_for_problem
from .database import connect
from .intelligence import run_intelligence
from .profiles import due_profiles, mark_profile_run
from .approval import set_decision
from .research.search import search_research
from .scheduling import schedule_draft


def _next_run(profile: dict, now: datetime) -> str:
    cfg = profile["config"]
    tz_name = str(cfg.get("timezone") or "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    local = now.astimezone(tz)
    raw = str(cfg.get("daily_time") or "09:00")
    try:
        hour, minute = [int(x) for x in raw.split(":", 1)]
        candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except Exception:
        candidate = local.replace(hour=9, minute=0, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


def _tag_problems(database_url: str, profile_id: int, items: list[dict]) -> list[int]:
    db = connect(database_url)
    ids: list[int] = []
    try:
        for item in items:
            row = db.execute("SELECT id, metadata FROM problems WHERE source=? AND external_id=?", (item["source"], item["external_id"])).fetchone()
            if not row:
                continue
            metadata = json.loads(row["metadata"] or "{}")
            profiles = metadata.get("profile_ids", [])
            if profile_id not in profiles:
                profiles.append(profile_id)
            metadata["profile_ids"] = profiles
            db.execute("UPDATE problems SET metadata=? WHERE id=?", (json.dumps(metadata, ensure_ascii=False), int(row["id"])))
            ids.append(int(row["id"]))
        db.commit()
        return ids
    finally:
        db.close()


def _generate_profile_drafts(settings: Settings, profile_id: int, problem_ids: list[int], limit: int) -> dict[str, int]:
    db = connect(settings.database_url)
    try:
        ids = [int(r["id"]) for r in db.execute("""SELECT p.id FROM problems p JOIN ai_intelligence a ON a.problem_id=p.id
            LEFT JOIN content_drafts d ON d.problem_id=p.id AND d.status!='rejected'
            WHERE p.id IN (%s) AND d.id IS NULL ORDER BY a.opportunity_score DESC LIMIT ?""" % ",".join("?" for _ in problem_ids), (*problem_ids, limit)).fetchall()] if problem_ids else []
    finally:
        db.close()
    result = {"generated": 0, "skipped": 0, "failed": 0}
    for problem_id in ids:
        try:
            item = generate_for_problem(settings, problem_id)
            for key in result:
                result[key] += int(item.get(key, 0))
        except Exception:
            result["failed"] += 1
    return result


def run_profile_cycle(settings: Settings, profile: dict) -> dict:
    cfg = profile["config"]
    categories = cfg.get("categories") or ["technology"]
    sources = cfg.get("sources") or ["github", "reddit", "stackoverflow", "rss"]
    all_items: list[dict] = []
    failures: list[str] = []
    for category in categories:
        try:
            result = search_research(settings, query=str(cfg.get("query") or ""), sources=sources, category=str(category), intent="all", time_range=str(cfg.get("time_range") or "7d"), limit=min(int(cfg.get("research_limit") or 25), 100))
            all_items.extend(result.get("items", []))
            failures.extend(result.get("failed_sources", []))
        except Exception as exc:
            failures.append(f"{category}: {exc}")
    problem_ids = _tag_problems(settings.database_url, int(profile["id"]), all_items)
    intelligence = run_intelligence(settings, limit=min(max(len(problem_ids), 1), 100))
    generated = _generate_profile_drafts(settings, int(profile["id"]), problem_ids, int(cfg.get("content_limit") or 10))

    approved = scheduled = 0
    db = connect(settings.database_url)
    try:
        if problem_ids:
            marks = ",".join("?" for _ in problem_ids)
            drafts = db.execute(f"SELECT id FROM content_drafts WHERE problem_id IN ({marks}) AND status='pending_approval' ORDER BY created_at DESC LIMIT 50", tuple(problem_ids)).fetchall()
        else:
            drafts = []
    finally:
        db.close()
    if cfg.get("approval_mode") == "auto":
        for row in drafts:
            if set_decision(settings, int(row["id"]), "approved"):
                approved += 1
    if cfg.get("auto_publish"):
        db = connect(settings.database_url)
        try:
            approved_rows = db.execute(f"SELECT id FROM content_drafts WHERE problem_id IN ({','.join('?' for _ in problem_ids)}) AND status='approved' ORDER BY created_at DESC LIMIT 20", tuple(problem_ids)).fetchall() if problem_ids else []
        finally:
            db.close()
        for row in approved_rows:
            try:
                when = _next_run(profile, datetime.now(timezone.utc))
                schedule_draft(settings, int(row["id"]), str(cfg.get("publish_provider") or "linkedin"), when, 3, "none", [])
                scheduled += 1
            except Exception:
                failures.append(f"schedule draft {row['id']}")
    return {"profile_id": int(profile["id"]), "profile": profile["name"], "research_items": len(all_items), "problem_ids": len(problem_ids), "analyzed": int(intelligence.analyzed), "generated": generated["generated"], "approved": approved, "scheduled": scheduled, "failed": len(failures), "failures": failures[:10]}


def run_due_profile_automation(settings: Settings) -> dict:
    profiles = due_profiles(settings.database_url)
    results = []
    for profile in profiles:
        try:
            result = run_profile_cycle(settings, profile)
            mark_profile_run(settings.database_url, int(profile["id"]), "success", _next_run(profile, datetime.now(timezone.utc)))
            results.append(result)
        except Exception as exc:
            mark_profile_run(settings.database_url, int(profile["id"]), f"failed: {exc}", _next_run(profile, datetime.now(timezone.utc)))
            results.append({"profile_id": int(profile["id"]), "profile": profile["name"], "failed": 1, "error": str(exc)})
    return {"profiles": len(profiles), "results": results}
