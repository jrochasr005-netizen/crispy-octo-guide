"""Per-platform rules: character limits, hashtag norms, posting cadence, and the
compliance facts that came out of the research report.

These specs drive both the generation prompt (so the model writes within limits)
and the renderer (so disclosures land where FTC + platform rules require).
Figures are approximate and change often — confirm against each platform's
current docs before relying on them.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    # Max characters for the caption/description body we generate.
    char_limit: int
    # Characters visible before the platform truncates with a "more" link.
    # Disclosure must sit inside this window to be "clear and conspicuous".
    visible_before_fold: int
    # Recommended number of hashtags (research: don't bury disclosure in them).
    hashtags: int
    # Realistic posts/day that avoids spam flags (from the research report).
    recommended_per_day: str
    # Whether the platform tolerates affiliate links well.
    affiliate_friendly: bool
    # Platform-specific notes injected into the prompt.
    notes: str = ""


PLATFORMS: dict[str, Platform] = {
    "instagram": Platform(
        key="instagram",
        name="Instagram",
        char_limit=2200,
        visible_before_fold=125,
        hashtags=5,
        recommended_per_day="1-2 feed posts + stories",
        affiliate_friendly=True,
        notes=(
            "Disclosure MUST be visible before the 'more' cutoff (~125 chars) — "
            "lead with it. No clickable links in captions, so the CTA points to "
            "'link in bio'. API cap is ~25 published posts/24h; do not max it."
        ),
    ),
    "tiktok": Platform(
        key="tiktok",
        name="TikTok",
        char_limit=2200,
        visible_before_fold=100,
        hashtags=5,
        recommended_per_day="1-2",
        affiliate_friendly=True,
        notes=(
            "Put the disclosure in the first 1-2 lines. Branded-content toggle is "
            "forced by TikTok and is NOT sufficient alone — keep an in-caption "
            "disclosure too. Never overlay links/logos on the video itself."
        ),
    ),
    "youtube": Platform(
        key="youtube",
        name="YouTube (Shorts/description)",
        char_limit=1500,
        visible_before_fold=150,
        hashtags=3,
        recommended_per_day="~1 (quota-limited)",
        affiliate_friendly=True,
        notes=(
            "This is the video description. Disclose affiliate links here AND say "
            "it on-screen/in the video. Links in descriptions are clickable."
        ),
    ),
    "pinterest": Platform(
        key="pinterest",
        name="Pinterest",
        char_limit=500,
        visible_before_fold=100,
        hashtags=3,
        recommended_per_day="~1",
        affiliate_friendly=True,
        notes=(
            "Most affiliate-friendly platform — affiliate links are explicitly "
            "allowed but must be used 'in moderation' and disclosed. Pin "
            "descriptions are short; keep it tight and value-first."
        ),
    ),
    "x": Platform(
        key="x",
        name="X (Twitter)",
        char_limit=280,
        visible_before_fold=280,
        hashtags=2,
        recommended_per_day="3-5",
        affiliate_friendly=True,
        notes=(
            "Hard 280-char limit INCLUDING the disclosure and the link. Posts "
            "with a URL now cost more via the API — keep them high-value. Never "
            "post duplicate/near-identical text (platform-manipulation ban)."
        ),
    ),
}

# Platforms the research flagged as hostile to automated affiliate posting.
# We refuse to generate for these to keep accounts safe.
BLOCKED = {
    "reddit": "Most subreddits ban affiliate links; cross-posting triggers shadowbans.",
    "linkedin": "Automated posting is not permitted for individual accounts.",
}


def get(platform_key: str) -> Platform:
    key = platform_key.lower().strip()
    if key in BLOCKED:
        raise ValueError(
            f"{key!r} is not supported for automated affiliate posting: {BLOCKED[key]} "
            "Post there manually instead."
        )
    if key not in PLATFORMS:
        raise ValueError(
            f"Unknown platform {key!r}. Supported: {', '.join(PLATFORMS)}."
        )
    return PLATFORMS[key]
