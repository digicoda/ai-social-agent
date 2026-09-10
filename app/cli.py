import argparse

from .config import get_settings
from .research.runner import run_research


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Social Agent research CLI")
    parser.add_argument("command", choices=["research"])
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "research":
        result = run_research(settings)
        print(f"discovered={result.discovered} saved={result.saved} duplicates={result.duplicates} failed={result.failed_sources}")


if __name__ == "__main__":
    main()
