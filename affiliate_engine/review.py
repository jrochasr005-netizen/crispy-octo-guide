"""Minimal review queue: approve or reject generated drafts before posting.

This is the human-in-the-loop gate. Nothing leaves this tool already posted —
approving just moves a draft to status 'approved' so your (separate) scheduler
or you can publish it via an official platform API / scheduler like Buffer.

Usage:
    python -m affiliate_engine.review              # interactive review of pending
    python -m affiliate_engine.review --list       # list statuses, no changes
    python -m affiliate_engine.review --approved   # print approved post texts
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

QUEUE_DIR = Path(os.environ.get("AFFILIATE_QUEUE", "review_queue"))


def _load() -> list[tuple[Path, dict]]:
    items = []
    for path in sorted(QUEUE_DIR.glob("*.json")):
        try:
            items.append((path, json.loads(path.read_text())))
        except json.JSONDecodeError:
            continue
    return items


def _save(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=2))


def cmd_list() -> int:
    items = _load()
    if not items:
        print(f"No drafts in {QUEUE_DIR}/. Generate some first.")
        return 0
    by_status: dict[str, int] = {}
    for _, rec in items:
        by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
    print(f"{len(items)} draft(s) in {QUEUE_DIR}/:")
    for status, n in sorted(by_status.items()):
        print(f"  {status}: {n}")
    return 0


def cmd_approved() -> int:
    for _, rec in _load():
        if rec["status"] == "approved":
            print("=" * 60)
            print(f"{rec['platform'].upper()}  |  {rec['product']}  |  {rec['recommended_cadence']}")
            print("-" * 60)
            print(rec["rendered"]["text"])
            print()
    return 0


def cmd_review() -> int:
    pending = [(p, r) for p, r in _load() if r["status"] == "pending"]
    if not pending:
        print("No pending drafts. All caught up.")
        return 0
    print(f"{len(pending)} pending draft(s). [a]pprove  [r]eject  [s]kip  [q]uit\n")
    for path, rec in pending:
        r = rec["rendered"]
        print("=" * 64)
        print(f"{rec['platform'].upper()}  |  {rec['product']}  |  {r['char_count']} chars"
              + ("  ⚠ OVER LIMIT" if r["over_limit"] else ""))
        print("-" * 64)
        print(r["text"])
        print("-" * 64)
        if not r["disclosure_present"]:
            print("⚠ WARNING: no disclosure detected — do not approve as-is.")
        choice = input("[a/r/s/q] > ").strip().lower()
        if choice == "q":
            break
        if choice == "a":
            rec["status"] = "approved"
            _save(path, rec)
            print("  approved.\n")
        elif choice == "r":
            rec["status"] = "rejected"
            _save(path, rec)
            print("  rejected.\n")
        else:
            print("  skipped.\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Review affiliate post drafts.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="Show counts by status.")
    group.add_argument("--approved", action="store_true", help="Print approved post texts.")
    args = parser.parse_args()
    if args.list:
        return cmd_list()
    if args.approved:
        return cmd_approved()
    return cmd_review()


if __name__ == "__main__":
    raise SystemExit(main())
