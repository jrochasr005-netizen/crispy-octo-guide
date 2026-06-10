"""Tests for the compliance-critical logic. No API key or network required.

Run with:  python -m pytest -q     (or:  python tests/test_engine.py)

These guard the rules that, if they silently broke, would get accounts banned or
violate FTC rules: every post carries a disclosure, X stays within 280 chars,
and hostile platforms are refused.
"""

from datetime import date

import pytest

from affiliate_engine import disclosure as disc
from affiliate_engine import platforms as platforms_mod
from affiliate_engine import schedule
from affiliate_engine.generate import PostDraft, _render


def _draft() -> PostDraft:
    return PostDraft(
        hook="The SEO tool I wish I'd found sooner",
        body="Cheaper than the big players and beginner-friendly. Tradeoff: smaller index.",
        hashtags=["seo", "affiliate", "bloggingtips"],
        call_to_action="Try it free",
    )


# --- disclosure -----------------------------------------------------------

def test_has_disclosure_detects_markers():
    assert disc.has_disclosure("#ad great tool")
    assert disc.has_disclosure("This is #Sponsored content")
    assert not disc.has_disclosure("just a normal caption with #tips")


def test_disclosure_falls_back_to_short_tag_when_tight():
    assert disc.disclosure_for(5) == disc.SHORT_TAG
    assert disc.disclosure_for(1000) == disc.FULL_DISCLOSURE


# --- rendering ------------------------------------------------------------

@pytest.mark.parametrize("platform_key", list(platforms_mod.PLATFORMS))
def test_every_rendered_post_has_a_disclosure(platform_key):
    platform = platforms_mod.get(platform_key)
    rendered = _render(_draft(), platform, "https://example.com/?ref=ID")
    assert rendered["disclosure_present"], f"{platform_key} missing disclosure"


def test_x_stays_within_280_chars():
    platform = platforms_mod.get("x")
    rendered = _render(_draft(), platform, "https://example.com/?ref=ID")
    assert rendered["char_count"] <= 280
    assert not rendered["over_limit"]


def test_instagram_disclosure_is_above_the_fold():
    platform = platforms_mod.get("instagram")
    rendered = _render(_draft(), platform, "https://example.com/?ref=ID")
    # Disclosure must appear within the visible-before-"more" window.
    head = rendered["text"][: platform.visible_before_fold]
    assert disc.has_disclosure(head)


# --- platform safety ------------------------------------------------------

@pytest.mark.parametrize("blocked", ["reddit", "linkedin"])
def test_hostile_platforms_are_refused(blocked):
    with pytest.raises(ValueError):
        platforms_mod.get(blocked)


def test_unknown_platform_raises():
    with pytest.raises(ValueError):
        platforms_mod.get("myspace")


# --- scheduling -----------------------------------------------------------

def test_daily_cap_parsing_respects_slots_and_cadence():
    # "3-5" wants 5 but X only has 4 slots -> capped at 4.
    assert schedule._daily_cap("3-5", "x") == 4
    # "1-2 feed posts + stories" -> 2, IG has 3 slots -> 2.
    assert schedule._daily_cap("1-2 feed posts + stories", "instagram") == 2
    # "~1" -> 1.
    assert schedule._daily_cap("~1", "pinterest") == 1
    # empty -> 1.
    assert schedule._daily_cap("", "tiktok") == 1


def test_assign_times_spreads_over_days_when_cap_exceeded():
    start = date(2026, 6, 15)
    # 5 X posts, cap 4/day -> day 0 gets 4, day 1 gets 1.
    records = [{"platform": "x", "recommended_cadence": "3-5"} for _ in range(5)]
    times = schedule._assign_times(records, start)
    days = sorted({t.date() for t in times})
    assert days == [date(2026, 6, 15), date(2026, 6, 16)]
    assert sum(1 for t in times if t.date() == start) == 4


# --- postiz integration (no network) -------------------------------------

def test_postiz_payload_schedules_when_time_present():
    from affiliate_engine import postiz
    rec = {
        "scheduled_for": "2026-06-15T08:00:00",
        "rendered": {"text": "#ad great tool https://x.com/?ref=ID"},
    }
    payload = postiz._build_payload(rec, "channel-123")
    assert payload["type"] == "schedule"
    assert payload["date"] == "2026-06-15T08:00:00"
    assert payload["posts"][0]["integration"]["id"] == "channel-123"
    assert payload["posts"][0]["value"][0]["content"].startswith("#ad")


def test_postiz_payload_falls_back_to_draft_without_time():
    from affiliate_engine import postiz
    rec = {"rendered": {"text": "#ad hello"}}
    payload = postiz._build_payload(rec, "channel-123")
    assert payload["type"] == "draft"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
