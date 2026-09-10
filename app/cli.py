import argparse

from .analysis import run_analysis
from .approval import queue, set_decision
from .config import get_settings
from .content import ContentGenerationError, generate_content
from .publish_service import publish_draft
from .publishing import PublishingError
from .research.runner import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Social Agent CLI")
    parser.add_argument("command", choices=["research", "analyze", "generate", "queue", "approve", "reject", "publish"])
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--draft-id", type=int)
    parser.add_argument("--reason", default="")
    parser.add_argument("--provider", default="linkedin")
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
        try: print(publish_draft(settings, args.draft_id, args.provider))
        except PublishingError as exc: parser.error(str(exc))


if __name__ == "__main__":
    main()
