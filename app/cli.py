import argparse

from .analytics import publishing_history, publishing_stats
from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .publish_service import publish_draft
from .publishing import PublishingError
from .research.runner import run_research
from .scheduler import run_due_schedules
from .scheduling import cancel_draft_schedule, schedule_draft, schedules


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Social Agent CLI")
    parser.add_argument("command", choices=["research", "analyze", "generate", "queue", "approve", "reject", "publish", "schedule", "cancel-schedule", "schedules", "worker", "history", "stats"])
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--draft-id", type=int)
    parser.add_argument("--schedule-id", type=int)
    parser.add_argument("--reason", default="")
    parser.add_argument("--provider", default="linkedin")
    parser.add_argument("--media-path", default="")
    parser.add_argument("--media-type", choices=["image", "document"], default="image")
    parser.add_argument("--scheduled-for", default="")
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "research":
        result = run_research(settings)
        print(f"discovered={result.discovered} saved={result.saved} duplicates={result.duplicates} failed={result.failed_sources}")
    elif args.command == "analyze":
        result = run_analysis(settings, limit=args.limit)
        print(f"analyzed={result.analyzed} auto_publish_candidates={result.auto_publish_candidates} approval_queue={result.approval_queue} discarded={result.discarded} failed={result.failed}")
    elif args.command == "generate":
        try: print(generate_content(settings, limit=args.limit))
        except ContentGenerationError as exc: parser.error(str(exc))
    elif args.command == "queue":
        for item in queue(settings, limit=args.limit): print(f"[{item['id']}] {item['title']} (confidence={item['generation_confidence']})")
    elif args.command in {"approve", "reject"}:
        if not args.draft_id: parser.error("--draft-id is required")
        try: changed = set_decision(settings, args.draft_id, "approved" if args.command == "approve" else "rejected", args.reason)
        except ValueError as exc: parser.error(str(exc))
        if not changed: parser.error("draft not found")
        print(f"draft={args.draft_id} status={'approved' if args.command == 'approve' else 'rejected'}")
    elif args.command == "publish":
        if not args.draft_id: parser.error("--draft-id is required")
        try:
            media_paths = [args.media_path] if args.media_path else None
            print(publish_draft(settings, args.draft_id, args.provider, media_paths=media_paths, media_type=args.media_type))
        except PublishingError as exc: parser.error(str(exc))
    elif args.command == "schedule":
        if not args.draft_id or not args.scheduled_for: parser.error("--draft-id and --scheduled-for are required")
        try: print(schedule_draft(settings, args.draft_id, args.provider, args.scheduled_for, args.max_attempts))
        except (ValueError, PublishingError) as exc: parser.error(str(exc))
    elif args.command == "cancel-schedule":
        if not args.schedule_id: parser.error("--schedule-id is required")
        if not cancel_draft_schedule(settings, args.schedule_id): parser.error("active schedule not found")
        print(f"schedule={args.schedule_id} status=cancelled")
    elif args.command == "schedules":
        for item in schedules(settings, limit=args.limit): print(item)
    elif args.command == "worker":
        print(run_due_schedules(settings, limit=args.limit))
    elif args.command == "history":
        for item in publishing_history(settings.database_url, limit=args.limit, provider=args.provider): print(item)
    elif args.command == "stats":
        print(publishing_stats(settings.database_url))


if __name__ == "__main__":
    main()
