"""Push approved/scheduled drafts into Postiz, which posts them to your social
accounts through official, approved platform connections.

Postiz is the compliant "last mile": our engine writes the posts and adds
disclosures, Postiz handles the actual scheduling/publishing. This keeps you on
the safe side of every platform's rules.

SECURITY: your Postiz API key is read from the POSTIZ_API_KEY environment
variable. Never hardcode it, never commit it, never paste it into chat. The code
needs the key at runtime only — it is never stored by this tool.

Two keys, don't confuse them:
  - POSTIZ_API_KEY  -> Postiz's own API key (Settings -> Public API). THIS is
                       what this connector uses to push posts in.
  - An OpenAI/AI key you may have pasted *inside* Postiz for its AI writing
    feature is a DIFFERENT thing and is NOT used here.

Setup:
  1. export POSTIZ_API_KEY=...                 (your Postiz Public API key)
  2. python -m affiliate_engine.postiz --list  (shows your connected accounts + IDs)
  3. Put those IDs in config.json under "postiz_channels", e.g.
       "postiz_channels": { "instagram": "abc123", "x": "def456" }
  4. python -m affiliate_engine.postiz --channels config.json          (PREVIEW only)
  5. python -m affiliate_engine.postiz --channels config.json --send   (actually queue)

Nothing is sent without --send. Without it you only see a preview.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

QUEUE_DIR = Path(os.environ.get("AFFILIATE_QUEUE", "review_queue"))
API_URL = os.environ.get("POSTIZ_API_URL", "https://api.postiz.com/public/v1").rstrip("/")


def _api_key() -> str:
    key = os.environ.get("POSTIZ_API_KEY")
    if not key:
        raise SystemExit(
            "POSTIZ_API_KEY is not set. Set it privately first, e.g.:\n"
            "  export POSTIZ_API_KEY=your-postiz-public-api-key\n"
            "Never paste the key into a file or chat."
        )
    return key


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _api_key())  # Postiz expects the raw key here
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        return e.code, detail
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach Postiz at {url}: {e.reason}")


def list_integrations() -> int:
    """Show connected social accounts and their integration IDs."""
    status, payload = _request("GET", "/integrations")
    if status >= 400:
        print(f"Postiz returned {status}: {payload}")
        print("Check that POSTIZ_API_KEY is correct and POSTIZ_API_URL matches your instance.")
        return 1
    items = payload if isinstance(payload, list) else (payload or {}).get("integrations", [])
    if not items:
        print("No connected accounts found in Postiz. Connect your social accounts in Postiz first.")
        return 0
    print("Connected accounts (copy the id into config.json -> postiz_channels):\n")
    for it in items:
        iid = it.get("id", "?")
        name = it.get("name", "")
        platform = it.get("identifier") or it.get("providerIdentifier") or it.get("platform") or ""
        print(f"  id={iid}   platform={platform}   name={name}")
    return 0


def _load_channels(config_path: str) -> dict[str, str]:
    cfg = json.loads(Path(config_path).read_text())
    channels = cfg.get("postiz_channels", {})
    if not channels:
        raise SystemExit(
            f"No 'postiz_channels' in {config_path}. Run '--list' to get your account IDs, "
            "then add a mapping like: \"postiz_channels\": {\"instagram\": \"<id>\"}"
        )
    return channels


def _scheduled_drafts() -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(QUEUE_DIR.glob("*.json")):
        try:
            rec = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if rec.get("status") in ("scheduled", "approved"):
            out.append((path, rec))
    return out


def _build_payload(rec: dict, integration_id: str) -> dict:
    """Assemble the Postiz create-post body for one draft.

    Uses 'schedule' with the draft's scheduled_for time when present, else queues
    as a draft inside Postiz so you can place it manually. Text-only (no images);
    add images in Postiz if you want them.
    """
    when = rec.get("scheduled_for")
    return {
        "type": "schedule" if when else "draft",
        "date": when or "",
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration_id},
                "value": [{"content": rec["rendered"]["text"], "image": []}],
                "settings": {},
            }
        ],
    }


def push(config_path: str, send: bool) -> int:
    channels = _load_channels(config_path)
    drafts = _scheduled_drafts()
    if not drafts:
        print("No approved/scheduled drafts to push. Approve some first "
              "(python -m affiliate_engine.review) and optionally schedule them.")
        return 0

    pushed = skipped = 0
    for path, rec in drafts:
        platform = rec["platform"]
        integration_id = channels.get(platform)
        if not integration_id:
            print(f"  - skip {rec.get('product')}/{platform}: no Postiz channel mapped for '{platform}'.")
            skipped += 1
            continue
        payload = _build_payload(rec, integration_id)

        if not send:
            print(f"\n[PREVIEW] {rec.get('product')} / {platform} -> integration {integration_id}")
            print(json.dumps(payload, indent=2))
            continue

        status, resp = _request("POST", "/posts", payload)
        if status >= 400:
            print(f"  ! {rec.get('product')}/{platform}: Postiz error {status}: {resp}")
            skipped += 1
            continue
        rec["status"] = "queued_to_postiz"
        rec["postiz_response"] = resp if isinstance(resp, (dict, list)) else str(resp)
        path.write_text(json.dumps(rec, indent=2))
        print(f"  ✓ queued {rec.get('product')}/{platform} to Postiz.")
        pushed += 1

    if send:
        print(f"\nDone. {pushed} queued, {skipped} skipped. Check your Postiz calendar to confirm.")
    else:
        print("\nThis was a PREVIEW. Re-run with --send to actually queue these in Postiz.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Push drafts to Postiz for scheduling/posting.")
    parser.add_argument("--list", action="store_true", help="List your connected accounts + IDs.")
    parser.add_argument("--channels", default="config.json", help="Config file with postiz_channels map.")
    parser.add_argument("--send", action="store_true", help="Actually queue posts (default is preview).")
    args = parser.parse_args()
    if args.list:
        return list_integrations()
    return push(args.channels, args.send)


if __name__ == "__main__":
    raise SystemExit(main())
