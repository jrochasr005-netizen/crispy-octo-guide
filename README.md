# Affiliate Viral Content Engine

A **niche-agnostic** pipeline that turns a product list into platform-native
affiliate post drafts using the Claude API, auto-appends FTC-compliant
disclosures, and routes everything through a **human review queue** before
anything is posted.

> **Read this first.** This tool deliberately does **not** auto-post spam to
> every platform all day and night. That approach gets your accounts banned and
> your affiliate commissions clawed back — see `affiliate-research-report.md` for
> the evidence. This builds the *sustainable* version: AI drafts, you approve,
> you post at a human cadence with proper disclosures. That's the difference
> between a business and a banned account.

## What it does

1. **You** keep a `config.json` of products (configured for AI/SaaS to start,
   extendable to **any niche** — finance, hosting, health — by adding entries).
2. **Generate** drafts: for each product × platform, Claude writes a
   platform-native post (different copy per platform, no identical cross-posting).
3. **Disclose**: an FTC disclosure is added by code (never left to chance) and
   placed where it's visible — above the "more" fold, not buried in hashtags.
4. **Review**: drafts land in `review_queue/` as `pending`. You approve or reject
   each one. Nothing is posted automatically.
5. **Post**: take approved texts and schedule them via an official-API tool
   (Buffer, Publer) at a sane cadence. (Posting integration is intentionally
   left to a compliant scheduler — see the report.)

Platforms supported: **Instagram, TikTok, YouTube, Pinterest, X.**
Reddit and LinkedIn are intentionally **blocked** — the research found automated
affiliate posting there gets you shadowbanned/violates ToS.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...          # your Claude API key
cp config.example.json config.json            # then edit with your products + real affiliate URLs
```

## Use

```bash
# Try the wiring with NO API calls / no spend:
python -m affiliate_engine.generate config.json --dry-run

# Real generation (all default platforms):
python -m affiliate_engine.generate config.json

# Just two platforms:
python -m affiliate_engine.generate config.json --platforms instagram,x

# Review the queue (approve/reject interactively):
python -m affiliate_engine.review

# See status counts / dump approved posts:
python -m affiliate_engine.review --list
python -m affiliate_engine.review --approved

# Schedule approved drafts at a safe cadence -> CSV for Buffer/Publer/Metricool:
python -m affiliate_engine.schedule
python -m affiliate_engine.schedule --start 2026-06-15 --out posts.csv
```

The scheduler spreads approved posts across days so no platform exceeds its safe
posts/day (e.g. X capped at 4, Instagram at 2), assigns sensible time slots, marks
the drafts `scheduled`, and writes a CSV you bulk-import into your scheduler. It
does **not** post for you — that final step stays in a compliant, official-API
scheduler at a human pace.

## Tests

```bash
pip install pytest
python -m pytest -q
```

The suite guards the compliance-critical rules: every rendered post carries an
FTC disclosure, X stays within 280 characters, the Instagram disclosure sits
above the "more" fold, hostile platforms (Reddit/LinkedIn) are refused, and the
cadence caps are honored.

## Adding a new niche

There's no code to change — just add products to `config.json` (or keep separate
config files per niche, e.g. `config.finance.json`) and run the generator against
them. Set `niche` and `brand_voice` so the copy matches the audience.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Your Claude API key (required for real runs). |
| `AFFILIATE_MODEL` | `claude-opus-4-8` | Model used for generation. |
| `AFFILIATE_QUEUE` | `review_queue` | Where drafts are written. |

## Compliance notes (do not skip)

- Every post carries an FTC disclosure. Keep it — undisclosed affiliate posts are
  a Section 5 violation and the 2024 reviews rule carries per-violation penalties.
- Respect each platform's cadence (shown on every draft). "10 mediocre posts hurt
  you more than 3 strong ones."
- Don't post identical text across platforms — the engine varies copy per
  platform specifically to avoid spam/platform-manipulation flags.
- Use a compliant link tool (Pretty Links / Geniuslink); never cookie-stuff or
  hide that a link points to Amazon.

See `affiliate-research-report.md` for the full sourced research behind these rules.
