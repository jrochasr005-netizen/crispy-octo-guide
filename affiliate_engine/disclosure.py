"""FTC affiliate disclosure helpers.

The FTC requires a clear, conspicuous disclosure of the affiliate/material
connection, placed near the recommendation (not buried in hashtags, not behind
a 'more' link). See the research report, section 3.

This module owns the disclosure text and the logic that guarantees every
rendered post carries one in the right place. The model is told to write the
post; the disclosure is appended by code so it can never be silently dropped.
"""

# Short tag for tight-character platforms (X). "#ad" is FTC-acceptable.
SHORT_TAG = "#ad"

# Full sentence the FTC suggests; used where there is room.
FULL_DISCLOSURE = (
    "#ad I earn a commission from purchases made through links in this post."
)


def disclosure_for(char_budget_remaining: int) -> str:
    """Pick the longest disclosure that fits the remaining character budget."""
    if char_budget_remaining >= len(FULL_DISCLOSURE):
        return FULL_DISCLOSURE
    return SHORT_TAG


def has_disclosure(text: str) -> bool:
    """True if the text already contains an FTC-acceptable disclosure marker."""
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("#ad", "#sponsored", "advertisement", "i earn a commission")
    )
