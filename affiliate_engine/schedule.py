"""Turn approved drafts into a cadence-aware posting schedule + CSV export.

This is the bridge between the review queue and a compliant scheduler (Buffer,
Publer, Metricool, etc.). It does NOT post anything itself — it assigns each
approved draft a sensible date/time that respects the platform's safe cadence
(from the research report), marks it `scheduled`, and writes a CSV you bulk-import
into your scheduler of choice.

Why a scheduler and not direct auto-posting: posting through an official-API
scheduler at a human cadence is what keeps accounts alive. Blasting a platform
API directly, many times a day, is the pattern that gets banned.

Usage:
    python -m affiliate_engine.schedule                 # schedule approved drafts -> schedule.csv
    python -m affiliate_engine.schedule --start 2026-06-15
    python -m affiliate_engine.schedule --out posts.csv
    python -m affiliate_engine.schedule --no-mark       # don't change draft status
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

QUEUE_DIR = Path(os.environ.get("AFFILIATE_QUEUE", "review_queue"))

# Reasonable posting time slots per platform (local time, naive). The number of
# slots also caps how many posts/day we'll schedule for that platform.
TIME_SLOTS: dict[str, list[str]] = {
    "instagram": ["11:00", "14:00", "19:00"],
    "tiktok": ["09:00", "12:00", "19:00"],
    "youtube": ["15:00", "17:00"],
    "pinterest": ["20:00", "21:00"],
    "x": ["08:00", "12:00", "17:00", "21:00"],
}


def _daily_cap(cadence: str, platform: str) -> int:
    """Largest safe posts/day, bounded by available time slots."""
    nums = [int(n) for n in re.findall(r"\d+", cadence or "")]
    cap = max(nums) if nums else 1
    slots = len(TIME_SLOTS.get(platform, ["12:00"]))
    return max(1, min(cap, slots))


def _load_approved() -> list[tuple[Path, dict]]:
    items = []
    for path in sorted(QUEUE_DIR.glob("*.json")):
        try:
            rec = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("status") == "approved":
            items.append((path, rec))
    # Stable order: oldest drafts get the earliest slots.
    items.sort(key=lambda pr: pr[1].get("created_at", ""))
    return items


def _assign_times(records: list[dict], start: date) -> list[datetime]:
    """Spread records across days per-platform without exceeding the daily cap."""
    # Track, per platform, which (day_offset, slot_index) we've filled.
    used: dict[str, int] = {}  # platform -> count assigned so far
    assignments: list[datetime] = []
    for rec in records:
        platform = rec["platform"]
        slots = TIME_SLOTS.get(platform, ["12:00"])
        cap = _daily_cap(rec.get("recommended_cadence", ""), platform)
        n = used.get(platform, 0)
        day_offset = n // cap
        slot_index = n % cap
        hh, mm = (int(x) for x in slots[slot_index].split(":"))
        when = datetime.combine(start + timedelta(days=day_offset), time(hh, mm))
        assignments.append(when)
        used[platform] = n + 1
    return assignments


def run(start: date, out_path: Path, mark: bool) -> int:
    items = _load_approved()
    if not items:
        print("No approved drafts to schedule. Approve some with: "
              "python -m affiliate_engine.review")
        return 0

    records = [rec for _, rec in items]
    times = _assign_times(records, start)

    rows = []
    for (path, rec), when in zip(items, times):
        rendered = rec["rendered"]
        rec["scheduled_for"] = when.isoformat()
        rows.append({
            "scheduled_date": when.date().isoformat(),
            "scheduled_time": when.strftime("%H:%M"),
            "platform": rec["platform"],
            "product": rec.get("product", ""),
            "content": rendered["text"],
            "link": rec.get("affiliate_url", ""),  # also embedded in content
        })
        if mark:
            rec["status"] = "scheduled"
            path.write_text(json.dumps(rec, indent=2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["scheduled_date", "scheduled_time", "platform", "product", "content", "link"],
            quoting=csv.QUOTE_ALL,
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scheduled {len(rows)} post(s) starting {start.isoformat()}.")
    # Quick per-platform summary so the cadence is visible.
    by_platform: dict[str, int] = {}
    for r in rows:
        by_platform[r["platform"]] = by_platform.get(r["platform"], 0) + 1
    for platform, n in sorted(by_platform.items()):
        print(f"  {platform}: {n} post(s)")
    print(f"\nCSV written to {out_path} — bulk-import it into Buffer/Publer/Metricool.")
    if mark:
        print("Drafts marked 'scheduled'.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Schedule approved drafts into a CSV.")
    parser.add_argument("--start", help="First posting date (YYYY-MM-DD). Default: tomorrow.")
    parser.add_argument("--out", default="schedule.csv", help="Output CSV path.")
    parser.add_argument("--no-mark", action="store_true", help="Don't change draft status.")
    args = parser.parse_args()
    start = (
        date.fromisoformat(args.start)
        if args.start
        else date.today() + timedelta(days=1)
    )
    return run(start, Path(args.out), mark=not args.no_mark)


if __name__ == "__main__":
    raise SystemExit(main())
