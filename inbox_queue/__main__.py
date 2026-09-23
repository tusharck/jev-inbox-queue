"""Command line entry point.

    python -m inbox_queue demo        # build the queue from the fake inbox
    python -m inbox_queue imap        # build it from your own mailbox (see .env)
    python -m inbox_queue evaluate    # measure against the labelled fake inbox
    python -m inbox_queue save-password   # store your mail app password in the keychain
"""

import argparse
import json
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from .classify import CACHE_DIR, classify_all
from .evaluate import evaluate
from .policy import DEFAULT_HIGH, DEFAULT_LOW, build_queue
from .render import render
from .sources import load_demo, load_imap, save_password

OUT_DIR = Path("out")


def _run_stats(command: str, stats: dict) -> dict:
    """Timing to show on the page. When everything came from the cache, reuse the last real run."""
    saved = CACHE_DIR.parent / f"last_run_{command}.json"
    if stats["sorted"]:
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps(stats))
        return stats
    if saved.exists():
        return {**json.loads(saved.read_text()), "from_cache": True}
    return stats


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="inbox_queue", description="Turn an inbox into an action queue with Jev.")
    parser.add_argument("command", choices=["demo", "imap", "evaluate", "save-password"])
    parser.add_argument("--high", type=float, default=DEFAULT_HIGH, help="needs_action at or above this goes in the queue")
    parser.add_argument("--low", type=float, default=DEFAULT_LOW, help="needs_action at or above this goes in 'check these'")
    parser.add_argument("--days", type=int, default=7, help="imap: how many days back to read")
    parser.add_argument("--limit", type=int, default=40, help="imap: maximum number of threads")
    parser.add_argument("--fresh", action="store_true", help="ignore cached answers and ask Jev again")
    parser.add_argument("--no-open", action="store_true", help="don't open the page in a browser")
    args = parser.parse_args()

    if args.command == "save-password":
        save_password()
        return
    if args.command == "imap":
        threads, source = load_imap(args.days, args.limit), "Your mailbox"
    else:
        threads, source = load_demo(), "Demo inbox"
    answers, stats = classify_all(threads, fresh=args.fresh)

    if args.command == "evaluate":
        evaluate(threads, answers, args.high, args.low)
        return

    buckets = build_queue(threads, answers, args.high, args.low)
    OUT_DIR.mkdir(exist_ok=True)
    page = OUT_DIR / f"{args.command}_queue.html"
    run = _run_stats(args.command, stats)
    page.write_text(render(buckets, source, run))
    if stats["sorted"]:
        print(f"Jev sorted {stats['sorted']} emails in {stats['seconds']:.1f}s")
    print(f"{len(buckets['queue'])} to do, {len(buckets['check'])} to check, {len(buckets['skip'])} kept out")
    print(f"Wrote {page}")
    if not args.no_open:
        webbrowser.open(page.resolve().as_uri())


if __name__ == "__main__":
    main()
