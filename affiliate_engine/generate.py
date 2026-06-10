"""Generate platform-native affiliate post drafts with the Claude API.

For each product x platform, we ask Claude for a structured draft (hook / body /
hashtags / CTA), then render it within the platform's limits with an FTC
disclosure placed up front. Drafts land in the review queue as `pending` — a
human approves them before anything is posted. This is the deliberate
human-in-the-loop design: full autopilot produces spam-flagged, low-converting
output and gets accounts banned.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m affiliate_engine.generate config.json
    python -m affiliate_engine.generate config.json --platforms instagram,x
    python -m affiliate_engine.generate config.json --dry-run   # no API calls
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from . import platforms as platforms_mod
from . import disclosure as disc

# Per the claude-api skill: default to Opus 4.8, override only via env.
MODEL = os.environ.get("AFFILIATE_MODEL", "claude-opus-4-8")

QUEUE_DIR = Path(os.environ.get("AFFILIATE_QUEUE", "review_queue"))


class PostDraft(BaseModel):
    """Structured draft returned by the model (before disclosure is added)."""

    hook: str = Field(description="Scroll-stopping first line, platform-native, no link.")
    body: str = Field(description="The main caption/description. Value-first, not spammy.")
    hashtags: list[str] = Field(description="Relevant hashtags WITHOUT the # symbol.")
    call_to_action: str = Field(description="What the viewer should do next.")


SYSTEM_PROMPT = """\
You are a senior affiliate-marketing copywriter who writes high-converting,
platform-native social posts. You write content that is genuinely useful and
specific — never generic "AI slop", never clickbait that overpromises.

Hard rules you always follow:
- Write for the SPECIFIC platform's native style and length.
- Lead with real value or a concrete hook, not the affiliate link.
- Never fabricate stats, prices, or claims. Only use facts you are given.
- Do NOT write the disclosure or the affiliate URL yourself — the system adds
  those. Just write the hook, body, hashtags, and CTA.
- Vary phrasing so posts for different platforms are NOT near-duplicates.
- Honest, helpful tone. Mention a real limitation or tradeoff when natural —
  it builds trust and converts better.
"""

USER_TEMPLATE = """\
Write one {platform_name} post promoting this affiliate product.

PRODUCT
  Name: {name}
  Category: {category}
  Price: {price}
  Who it's for: {audience}
  Key benefits: {benefits}
  Extra context: {context}

NICHE / BRAND VOICE
  Niche: {niche}
  Voice: {voice}

PLATFORM CONSTRAINTS
  Body character limit: {char_limit} (the disclosure + link are added on top, so
    leave headroom — aim for under {soft_limit} characters of body).
  Recommended hashtags: {hashtags}
  Platform notes: {notes}

Return the hook, body, hashtags (without #), and a call to action.
"""


def _render(draft: PostDraft, platform: platforms_mod.Platform, link: str) -> dict:
    """Assemble the final post text with the disclosure placed compliantly."""
    hashtags = " ".join(
        "#" + re.sub(r"[^A-Za-z0-9_]", "", h) for h in draft.hashtags[: platform.hashtags] if h
    )

    if platform.key == "x":
        # Tight budget: everything must fit in char_limit including link + tag.
        link_part = f" {link}" if link else ""
        budget = platform.char_limit - len(link_part) - 1
        tag = disc.disclosure_for(budget - len(draft.hook) - 2)
        text = f"{tag} {draft.hook}".strip()
        # Add body/CTA only if room remains.
        for extra in (draft.call_to_action,):
            if len(text) + len(extra) + 1 <= budget:
                text = f"{text} {extra}".strip()
        text = f"{text}{link_part}".strip()
        over_limit = len(text) > platform.char_limit
    else:
        # Disclosure first so it sits above the fold, then the post.
        tag = disc.FULL_DISCLOSURE
        link_line = f"\n\n👉 {draft.call_to_action}: {link}" if link else f"\n\n{draft.call_to_action}"
        text = f"{tag}\n\n{draft.hook}\n\n{draft.body}{link_line}\n\n{hashtags}".strip()
        over_limit = len(text) > platform.char_limit

    if not disc.has_disclosure(text):  # safety net — should never trigger
        text = f"{disc.FULL_DISCLOSURE}\n\n{text}"

    return {
        "text": text,
        "char_count": len(text),
        "over_limit": over_limit,
        "disclosure_present": disc.has_disclosure(text),
    }


def _generate_one(client, product: dict, platform: platforms_mod.Platform, niche: str, voice: str) -> PostDraft:
    soft_limit = max(50, platform.char_limit - 200)
    user = USER_TEMPLATE.format(
        platform_name=platform.name,
        name=product.get("name", ""),
        category=product.get("category", ""),
        price=product.get("price", "n/a"),
        audience=product.get("audience", "general"),
        benefits="; ".join(product.get("key_benefits", [])) or "n/a",
        context=product.get("context", "none"),
        niche=niche,
        voice=voice,
        char_limit=platform.char_limit,
        soft_limit=soft_limit,
        hashtags=platform.hashtags,
        notes=platform.notes,
    )
    # Structured output (Opus 4.8) returns a validated PostDraft.
    # cache_control on the system prompt keeps it cheap across many calls.
    response = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_format=PostDraft,
    )
    if response.parsed_output is None:
        raise RuntimeError(f"Model did not return a valid draft (stop: {response.stop_reason}).")
    return response.parsed_output


def _placeholder_draft(product: dict, platform: platforms_mod.Platform) -> PostDraft:
    """A fake draft so --dry-run works without an API key or spend."""
    name = product.get("name", "this tool")
    return PostDraft(
        hook=f"The {product.get('category', 'tool')} I wish I'd found sooner: {name}",
        body=f"[dry-run placeholder body for {name} on {platform.name}]",
        hashtags=(product.get("key_benefits") or ["affiliate"])[: platform.hashtags],
        call_to_action="Try it",
    )


def run(config_path: str, platform_keys: list[str] | None, dry_run: bool) -> int:
    config = json.loads(Path(config_path).read_text())
    niche = config.get("niche", "general")
    voice = config.get("brand_voice", "helpful, honest, concrete")
    products = config.get("products", [])
    if not products:
        print("No products in config. Add at least one to `products`.", file=sys.stderr)
        return 1

    targets = platform_keys or config.get("default_platforms") or list(platforms_mod.PLATFORMS)
    resolved: list[platforms_mod.Platform] = []
    for key in targets:
        try:
            resolved.append(platforms_mod.get(key))
        except ValueError as e:
            print(f"Skipping {key}: {e}", file=sys.stderr)

    client = None
    if not dry_run:
        try:
            import anthropic
        except ImportError:
            print("`anthropic` not installed. Run: pip install -r requirements.txt", file=sys.stderr)
            return 1
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for product in products:
        link = product.get("affiliate_url", "")
        for platform in resolved:
            try:
                draft = (
                    _placeholder_draft(product, platform)
                    if dry_run
                    else _generate_one(client, product, platform, niche, voice)
                )
            except Exception as e:  # keep going; one failure shouldn't kill the batch
                print(f"  ! {product.get('name')} / {platform.key}: {e}", file=sys.stderr)
                continue

            rendered = _render(draft, platform, link)
            record = {
                "id": uuid.uuid4().hex[:12],
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": "dry-run" if dry_run else MODEL,
                "product": product.get("name"),
                "affiliate_url": link,
                "platform": platform.key,
                "niche": niche,
                "draft": draft.model_dump(),
                "rendered": rendered,
                "platform_spec": asdict(platform),
                "recommended_cadence": platform.recommended_per_day,
            }
            out = QUEUE_DIR / f"{record['created_at'][:10]}_{platform.key}_{record['id']}.json"
            out.write_text(json.dumps(record, indent=2))
            flag = "  ⚠ OVER LIMIT" if rendered["over_limit"] else ""
            print(f"  ✓ {product.get('name')} / {platform.name} -> {out.name}{flag}")
            written += 1

    print(f"\n{written} draft(s) written to {QUEUE_DIR}/ as 'pending'.")
    print("Review them with:  python -m affiliate_engine.review")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate affiliate post drafts.")
    parser.add_argument("config", help="Path to config JSON (see config.example.json).")
    parser.add_argument("--platforms", help="Comma-separated platform keys to override config.")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls; emit placeholders.")
    args = parser.parse_args()
    keys = [p.strip() for p in args.platforms.split(",")] if args.platforms else None
    return run(args.config, keys, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
