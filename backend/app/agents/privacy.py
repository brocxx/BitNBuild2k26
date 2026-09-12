"""Last-line defence for what agents are allowed to say.

Two separate problems, both filtered before an explanation is persisted:

1. A private limit leaking into prose. The fake provider never writes one, but
   a language model might, so limits are stripped in paise, in rupees, and in
   a few common spoken forms.

2. An invented market claim. This system has no pricing feed, benchmark or
   index of any kind - prices come only from what participants entered. An
   agent writing "current market conditions" is stating something false about
   the product, and it would be on screen during the demo. Gemini did exactly
   this on the first live run, which is why this filter exists rather than
   trusting the prompt alone.

Both run on every provider, so the test suite exercises the same path the demo
uses.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

REDACTION = "[redacted limit]"

# Phrases asserting knowledge of a market this application cannot see.
MARKET_CLAIM_PATTERN = re.compile(
    r"""(?ix)
    \b(
        (current\s+|prevailing\s+|local\s+|open\s+)?market\s+
            (rates?|prices?|conditions?|values?|levels?|trends?)
      | going\s+rate
      | industry\s+(standard|norm|average|benchmark)s?
      | fair\s+market\s+value
      | (benchmark|spot|reference|published|quoted\s+market)\s+(rates?|prices?)
      | prevailing\s+(rates?|prices?)
      | market\s+(standard|norm)s?
    )\b
    """
)

MARKET_CLAIM_REPLACEMENT = "the terms of this shipment"


def _number_variants(value: int) -> list[str]:
    rupees = value / 100
    variants = {
        str(value),
        f"{value:,}",
        f"{rupees:.2f}".rstrip("0").rstrip("."),
        f"{rupees:,.2f}".rstrip("0").rstrip("."),
        str(int(rupees)),
        f"{int(rupees):,}",
    }
    # Also catch a value quoted to the nearest thousand rupees, which is how a
    # model is most likely to paraphrase a limit.
    if int(rupees) >= 1000:
        variants.add(f"{int(rupees) // 1000}")
    return [variant for variant in variants if len(variant) >= 3]


def strip_market_claims(text: str) -> str:
    """Replace assertions about market prices this system cannot know."""
    if not text:
        return ""
    cleaned, count = MARKET_CLAIM_PATTERN.subn(MARKET_CLAIM_REPLACEMENT, text)
    if count:
        logger.warning(
            "Removed %s unsupported market claim(s) from an agent explanation.", count
        )
    return cleaned


def scrub_explanation(text: str, private_values: list[int]) -> str:
    """Remove private limits and unsupported market claims from free text."""
    if not text:
        return ""
    cleaned = strip_market_claims(text)
    for value in private_values:
        for variant in _number_variants(value):
            cleaned = re.sub(
                rf"(?<![\d.]){re.escape(variant)}(?![\d])", REDACTION, cleaned
            )
    return cleaned.strip()


def mentions_private_value(text: str, private_values: list[int]) -> bool:
    return scrub_explanation(text, private_values) != (text or "").strip()


def claims_market_knowledge(text: str) -> bool:
    return bool(MARKET_CLAIM_PATTERN.search(text or ""))
