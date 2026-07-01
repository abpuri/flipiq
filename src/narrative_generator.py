"""
AI Narrative Generator

Generates an analyst-style "Deal Thesis" memo for a ZIP code using the
Claude API. Builds a structured fact sheet from scored data so the model
narrates real numbers instead of inventing them. Falls back gracefully:
callers should catch NarrativeError and show the rule-based narrative.
"""

import json
import os
from typing import Dict, Optional

import pandas as pd

# Override with a cheaper/faster model via env if needed.
DEFAULT_MODEL = os.environ.get("FLIPIQ_NARRATIVE_MODEL", "claude-opus-4-8")
MAX_TOKENS = 1500

SYSTEM_PROMPT = """You are FlipIQ's senior market analyst. You write tight, \
numbers-first investment memos for professional house flippers evaluating a \
ZIP code as a flip market.

Rules:
- Use ONLY the figures provided in the fact sheet. Never invent statistics, \
comps, or price points that are not given.
- Be opinionated: lead with a clear verdict on the market, not hedging.
- Respect data granularity: appreciation is ZIP-level; velocity, distress, \
and pricing power are metro-level; value gap is county-level. Metro/county \
signals apply to every ZIP in that area — say so where it matters.
- This is market screening from monthly Zillow Research data, not real-time \
or property-level intelligence. Do not imply otherwise.

Output format (Markdown, no preamble, ~200-280 words total):
## Deal Thesis
One short paragraph: the verdict and the single strongest reason.

## What the Numbers Say
3-5 bullets, each anchored to a specific figure from the fact sheet.

## Watch-Outs
2-3 bullets on the weakest signals or data caveats for this specific ZIP.

## Flipper's Move
One or two sentences: the concrete next step for a flipper running the \
given strategy in this market."""


class NarrativeError(Exception):
    """Raised when an AI narrative cannot be generated. Callers fall back."""


def get_api_key() -> Optional[str]:
    """Return the Anthropic API key from the environment, if set."""
    return os.environ.get("ANTHROPIC_API_KEY") or None


def _clean(value):
    """Convert a value to a JSON-safe number/string; None if missing."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return str(value)


def build_zip_facts(row: pd.Series, strategy_name: str = "Balanced") -> Dict:
    """Build a structured fact sheet for a ZIP from its scored row.

    Missing (NaN) metrics are dropped so the model never sees them.
    """
    facts = {
        "zip_code": _clean(row.get("region_name")),
        "city": _clean(row.get("city")),
        "state": _clean(row.get("state")),
        "metro": _clean(row.get("metro")),
        "county": _clean(row.get("county_name")),
        "strategy": strategy_name,
        "composite_score_0_100": _clean(row.get("composite_score")),
        "current_home_value_usd": _clean(row.get("current_value")),
        "signals": {
            "appreciation": {
                "level": "ZIP",
                "score_0_100": _clean(row.get("appreciation_score")),
                "value_change_12mo_pct": _clean(row.get("appreciation_pct")),
            },
            "velocity": {
                "level": "metro",
                "score_0_100": _clean(row.get("velocity_score")),
                "days_to_pending": _clean(row.get("days_to_pending")),
            },
            "distress": {
                "level": "metro",
                "score_0_100": _clean(row.get("distress_score")),
                "listings_with_price_cuts_pct": _clean(row.get("price_cut_pct")),
            },
            "pricing_power": {
                "level": "metro",
                "score_0_100": _clean(row.get("pricing_power_score")),
                "sale_to_list_ratio": _clean(row.get("sale_to_list")),
            },
            "value_gap": {
                "level": "county",
                "score_0_100": _clean(row.get("value_gap_score")),
                "entry_vs_median_gap_pct": _clean(row.get("value_gap_pct")),
            },
        },
    }

    # Drop empty top-level fields and signals with no data at all
    facts = {k: v for k, v in facts.items() if v is not None}
    facts["signals"] = {
        name: {k: v for k, v in sig.items() if v is not None}
        for name, sig in facts.get("signals", {}).items()
        if sig.get("score_0_100") is not None
    }
    return facts


def build_user_prompt(facts: Dict) -> str:
    """Render the fact sheet as the user message."""
    return (
        "Write the Deal Thesis memo for this ZIP code. Fact sheet:\n\n"
        + json.dumps(facts, indent=2, sort_keys=True)
    )


def generate_deal_thesis(
    row: pd.Series,
    strategy_name: str = "Balanced",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Generate an AI Deal Thesis memo for a scored ZIP row.

    Raises NarrativeError if no API key is configured or the call fails.
    """
    key = api_key or get_api_key()
    if not key:
        raise NarrativeError(
            "No Anthropic API key configured. Set ANTHROPIC_API_KEY to enable "
            "AI deal memos."
        )

    try:
        import anthropic
    except ImportError as exc:
        raise NarrativeError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from exc

    facts = build_zip_facts(row, strategy_name)
    client = anthropic.Anthropic(api_key=key)
    try:
        response = client.messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(facts)}],
        )
    except anthropic.APIError as exc:
        raise NarrativeError(f"Claude API error: {exc}") from exc

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise NarrativeError("Claude returned an empty response.")
    return text
