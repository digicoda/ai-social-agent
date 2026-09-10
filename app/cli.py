import argparse

from .analysis import run_analysis
from .config import get_settings
from .research.runner import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Social Agent CLI")
    parser.add_argument("command", choices=["research", "analyze"])
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "research":
        result = run_research(settings)
        print(f"discovered={result.discovered} saved={result.saved} duplicates={result.duplicates} failed={result.failed_sources}")
    elif args.command == "analyze":
        result = run_analysis(settings, limit=args.limit)
        print(
            f"analyzed={result.analyzed} auto_publish_candidates={result.auto_publish_candidates} "
            f"approval_queue={result.approval_queue} discarded={result.discarded} failed={result.failed}"
        )


if __name__ == "__main__":
    main()
