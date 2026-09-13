from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .approval import set_decision
from .config import Settings
from .content_workflow import generate_for_problem
from .database import connect
from .intelligence import run_intelligence
from .profiles import due_profiles, mark_profile_run
from .research.search import search_research
from .scheduling import schedule_draft


def _profile_settings(settings: Settings, profile: dict) -> Settings:
    cfg = profile.get("config") or {}
    values = {"database_url": profile.get("database_url") or settings.database_url, "image_enabled": cfg.get("image_enabled", settings.image_enabled), "image_model": cfg.get("image_model", settings.image_model), "image_shortcode": cfg.get("image_shortcode", settings.image_shortcode), "image_prompt": cfg.get("image_prompt", settings.image_prompt), "image_aspect_ratio": cfg.get("image_aspect_ratio", settings.image_aspect_ratio), "image_reference_path": cfg.get("image_reference_path", settings.image_reference_path), "humanize_content": cfg.get("humanize_content", settings.humanize_content)}
    provider = str(cfg.get("ai_provider") or settings.ai_provider).lower()
    model = str(cfg.get("ai_model") or "")
    values["ai_provider"] = provider
    if provider == "gemini" and model: values["gemini_model"] = model
    elif provider == "openai" and model: values["openai_model"] = model
    elif provider == "huggingface" and model: values["huggingface_model"] = model
    return settings.model_copy(update=values)


def _next_run(profile, now):
    cfg = profile["config"]
    try: tz = ZoneInfo(str(cfg.get("timezone") or "UTC"))
    except Exception: tz = timezone.utc
    local = now.astimezone(tz)
    try: hour, minute = [int(x) for x in str(cfg.get("daily_time") or "09:00").split(":", 1)]
    except Exception: hour, minute = 9, 0
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local: candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc).isoformat()


def _ensure_pipeline_schema(connection):
    connection.execute("""CREATE TABLE IF NOT EXISTS pipeline_runs (id TEXT PRIMARY KEY,profile_id INTEGER NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,stages TEXT NOT NULL DEFAULT '{}',error TEXT)""")
    connection.commit()


def _pipeline_start(database_url, profile_id):
    run_id = uuid.uuid4().hex; db = connect(database_url)
    try:
        _ensure_pipeline_schema(db); db.execute("INSERT INTO pipeline_runs(id,profile_id,started_at,status,stages) VALUES(?,?,?,?,?)", (run_id, profile_id, datetime.now(timezone.utc).isoformat(), "running", json.dumps({}))); db.commit(); return run_id
    finally: db.close()


def _pipeline_stage(database_url, run_id, name, status, data=None):
    db = connect(database_url)
    try:
        _ensure_pipeline_schema(db); row = db.execute("SELECT stages FROM pipeline_runs WHERE id=?", (run_id,)).fetchone(); stages = json.loads(row["stages"] or "{}") if row else {}; stages[name] = {"status": status, **(data or {})}; db.execute("UPDATE pipeline_runs SET stages=? WHERE id=?", (json.dumps(stages, ensure_ascii=False), run_id)); db.commit()
    finally: db.close()


def _pipeline_finish(database_url, run_id, status, error=None):
    db = connect(database_url)
    try: _ensure_pipeline_schema(db); db.execute("UPDATE pipeline_runs SET status=?,finished_at=?,error=? WHERE id=?", (status, datetime.now(timezone.utc).isoformat(), error, run_id)); db.commit()
    finally: db.close()


def _tag_problems(database_url, profile_id, items):
    db = connect(database_url); ids = []
    try:
        for item in items:
            row = db.execute("SELECT id,metadata FROM problems WHERE source=? AND external_id=?", (item["source"], item["external_id"])).fetchone()
            if not row: continue
            metadata = json.loads(row["metadata"] or "{}"); profiles = metadata.get("profile_ids", [])
            if profile_id not in profiles: profiles.append(profile_id)
            metadata["profile_ids"] = profiles; db.execute("UPDATE problems SET metadata=? WHERE id=?", (json.dumps(metadata, ensure_ascii=False), int(row["id"]))); ids.append(int(row["id"]))
        db.commit(); return ids
    finally: db.close()


def _generate_profile_drafts(settings, problem_ids, limit):
    if not problem_ids: return {"generated": 0, "skipped": 0, "failed": 0, "images": 0}
    db = connect(settings.database_url)
    try:
        marks = ",".join("?" for _ in problem_ids); ids = [int(r["id"]) for r in db.execute(f"SELECT p.id FROM problems p LEFT JOIN ai_intelligence a ON a.problem_id=p.id LEFT JOIN problem_analyses pa ON pa.problem_id=p.id LEFT JOIN content_drafts d ON d.problem_id=p.id AND d.status!='rejected' WHERE p.id IN ({marks}) AND d.id IS NULL AND (a.problem_id IS NOT NULL OR pa.problem_id IS NOT NULL) ORDER BY COALESCE(a.opportunity_score,0) DESC,COALESCE(a.confidence,pa.confidence,0) DESC LIMIT ?", (*problem_ids, limit)).fetchall()]
    finally: db.close()
    result = {"generated": 0, "skipped": 0, "failed": 0, "images": 0}
    for pid in ids:
        try:
            item = generate_for_problem(settings, pid)
            for key in ("generated", "skipped", "failed"): result[key] += int(item.get(key, 0))
            if item.get("image"): result["images"] += 1
        except Exception: result["failed"] += 1
    return result


def _effective_sources(cfg):
    manual = [str(x).lower() for x in (cfg.get("sources") or [])]
    if str(cfg.get("source_mode") or "auto") != "auto":
        return manual or ["web"]
    categories = {str(x).lower() for x in (cfg.get("categories") or [])}
    # Auto mode uses the sources that are most useful for the selected intent,
    # while always keeping Web Search available for broad market signals.
    sources = {"web", "reddit", "rss"}
    if categories & {"technology", "ai", "development", "security", "wordpress", "ecommerce"}: sources.add("github"); sources.add("stackoverflow")
    if categories & {"business", "marketing", "seo", "finance", "education", "news"}: sources.add("rss")
    return sorted(sources)


def run_profile_cycle(settings: Settings, profile: dict) -> dict:
    settings = _profile_settings(settings, profile); cfg = profile["config"]; profile_id = int(profile["id"]); run_id = _pipeline_start(settings.database_url, profile_id); failures = []; all_items = []; problem_ids = []
    try:
        categories = cfg.get("categories") or ["technology"]; sources = _effective_sources(cfg); website_url = str(cfg.get("website_url") or "")
        for category in categories:
            try:
                result = search_research(settings, query=str(cfg.get("query") or ""), website_url=website_url, sources=sources, category=str(category), intent=str(cfg.get("intent") or "all"), time_range=str(cfg.get("time_range") or "7d"), limit=min(int(cfg.get("research_limit") or 25), 100)); all_items.extend(result.get("items", [])); failures.extend(result.get("failed_sources", []))
            except Exception as exc: failures.append(f"{category}: {exc}")
        problem_ids = _tag_problems(settings.database_url, profile_id, all_items); _pipeline_stage(settings.database_url, run_id, "research", "completed", {"categories": list(categories), "sources": list(sources), "website_url": website_url, "source_mode": str(cfg.get("source_mode") or "auto"), "items": len(all_items), "problems": len(problem_ids), "failures": len(failures)})
        if problem_ids:
            intelligence = run_intelligence(settings, limit=min(max(len(problem_ids), 1), 100)); _pipeline_stage(settings.database_url, run_id, "ai_analysis", "completed", {"processed": int(intelligence.processed), "analyzed": int(intelligence.analyzed), "duplicates": int(intelligence.duplicates), "failed": int(intelligence.failed)})
            if intelligence.failed: failures.append(f"AI analysis failed for {intelligence.failed} item(s)")
        else:
            intelligence = type("Result", (), {"processed": 0, "analyzed": 0, "duplicates": 0, "failed": 0})(); _pipeline_stage(settings.database_url, run_id, "ai_analysis", "skipped", {"reason": "no research items"})
        generated = _generate_profile_drafts(settings, problem_ids, int(cfg.get("content_limit") or 10)); _pipeline_stage(settings.database_url, run_id, "content_generation", "completed", generated)
        if generated["failed"]: failures.append(f"content generation failed for {generated['failed']} item(s)")
        approved = 0; db = connect(settings.database_url)
        try:
            if problem_ids:
                marks = ",".join("?" for _ in problem_ids); drafts = db.execute(f"SELECT id FROM content_drafts WHERE problem_id IN ({marks}) AND status='pending_approval' ORDER BY created_at DESC LIMIT 50", tuple(problem_ids)).fetchall()
            else: drafts = []
        finally: db.close()
        if cfg.get("approval_mode") == "auto":
            for row in drafts:
                if set_decision(settings, int(row["id"]), "approved"): approved += 1
            approval_status = "completed"
        else: approval_status = "pending_human"
        _pipeline_stage(settings.database_url, run_id, "approval", approval_status, {"queued": len(drafts), "approved": approved, "mode": str(cfg.get("approval_mode") or "human")})
        scheduled = 0; providers = cfg.get("publish_providers") or [cfg.get("publish_provider") or "linkedin"]
        if isinstance(providers, str): providers = [providers]
        if problem_ids and cfg.get("auto_publish"):
            db = connect(settings.database_url)
            try:
                marks = ",".join("?" for _ in problem_ids); approved_rows = db.execute(f"SELECT id FROM content_drafts WHERE problem_id IN ({marks}) AND status='approved' ORDER BY created_at DESC LIMIT 20", tuple(problem_ids)).fetchall()
            finally: db.close()
            scheduled_for = _next_run(profile, datetime.now(timezone.utc))
            for row in approved_rows:
                for provider in providers:
                    try: schedule_draft(settings, int(row["id"]), str(provider), scheduled_for, 3, "none", []); scheduled += 1
                    except Exception as exc: failures.append(f"schedule draft {row['id']} for {provider}: {exc}")
        _pipeline_stage(settings.database_url, run_id, "scheduling", "completed" if cfg.get("auto_publish") else "disabled", {"scheduled": scheduled, "auto_publish": bool(cfg.get("auto_publish")), "providers": list(providers)})
        _pipeline_stage(settings.database_url, run_id, "publishing", "queued" if scheduled else "waiting_for_schedule", {"scheduled": scheduled, "providers": list(providers)})
        status = "completed_with_warnings" if failures else "completed"; _pipeline_finish(settings.database_url, run_id, status, "; ".join(failures[:10]) if failures else None)
        return {"pipeline_run_id": run_id, "profile_id": profile_id, "profile": profile["name"], "research_items": len(all_items), "problem_ids": len(problem_ids), "analyzed": int(intelligence.analyzed), "generated": generated["generated"], "images": generated.get("images", 0), "approved": approved, "scheduled": scheduled, "failed": len(failures), "status": status, "failures": failures[:10]}
    except Exception as exc:
        _pipeline_stage(settings.database_url, run_id, "pipeline", "failed", {"error": str(exc)}); _pipeline_finish(settings.database_url, run_id, "failed", str(exc)); raise


def run_due_profile_automation(settings: Settings) -> dict:
    profiles = due_profiles(settings.database_url); results = []
    for profile in profiles:
        try:
            result = run_profile_cycle(settings, profile); mark_profile_run(settings.database_url, int(profile["id"]), result.get("status", "success"), _next_run(profile, datetime.now(timezone.utc))); results.append(result)
        except Exception as exc:
            mark_profile_run(settings.database_url, int(profile["id"]), f"failed: {exc}", _next_run(profile, datetime.now(timezone.utc))); results.append({"profile_id": int(profile["id"]), "profile": profile["name"], "failed": 1, "status": "failed", "error": str(exc)})
    return {"profiles": len(profiles), "results": results}
