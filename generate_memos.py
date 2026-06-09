"""
Pre-generate AI Deal Thesis memos for the HTML dashboard.

Calls the Claude API for the top-ranked ZIPs in each strategy and writes
data/processed/ai_memos.json, which dashboard.html fetches alongside
dashboard_data.json. Run after regenerating dashboard data:

    export ANTHROPIC_API_KEY=sk-ant-...
    python generate_memos.py --top 25

Existing memos are kept (skipped) unless --force is passed, so re-runs only
pay for new ZIPs. The dashboard hides the AI section if this file is absent.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.narrative_generator import (
    DEFAULT_MODEL,
    NarrativeError,
    generate_deal_thesis,
    get_api_key,
)

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "ai_memos.json"

STRATEGY_FILES = {
    "balanced": ("Balanced", "top_opportunities_balanced.csv"),
    "fast_flip": ("Fast Flip", "top_opportunities_fast_flip.csv"),
    "value_add": ("Value-Add Flip", "top_opportunities_value_add_flip.csv"),
}


def zip_key(region_name) -> str:
    """Normalize a ZIP to the 5-digit string the dashboard uses."""
    return str(region_name).split(".")[0].zfill(5)


def generate_for_strategy(
    df: pd.DataFrame,
    strategy_label: str,
    existing: dict,
    top_n: int,
    force: bool = False,
    generator=generate_deal_thesis,
) -> dict:
    """Generate memos for the top N rows, reusing existing ones unless force."""
    memos = dict(existing)
    rows = df.head(top_n)
    for _, row in rows.iterrows():
        key = zip_key(row["region_name"])
        if key in memos and not force:
            continue
        try:
            memos[key] = generator(row, strategy_label)
            print(f"    {key} ({row.get('city', '')}, {row.get('state', '')}) ✓")
        except NarrativeError as e:
            print(f"    {key} FAILED: {e}")
    return memos


def main():
    parser = argparse.ArgumentParser(description="Pre-generate AI deal memos")
    parser.add_argument("--top", type=int, default=25,
                        help="Number of top ZIPs per strategy (default 25)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate memos that already exist")
    args = parser.parse_args()

    if not get_api_key():
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Export it and re-run:\n"
            "    export ANTHROPIC_API_KEY=sk-ant-...\n"
            "    python generate_memos.py"
        )

    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            existing = json.load(f).get("memos", {})

    output_memos = {}
    for strategy, (label, filename) in STRATEGY_FILES.items():
        path = PROCESSED_DIR / filename
        if not path.exists():
            print(f"  WARNING: {filename} not found, skipping {strategy}")
            continue
        print(f"  {strategy}: generating up to {args.top} memos...")
        df = pd.read_csv(path)
        output_memos[strategy] = generate_for_strategy(
            df, label, existing.get(strategy, {}), args.top, args.force
        )

    output = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "model": DEFAULT_MODEL,
        "memos": output_memos,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    total = sum(len(m) for m in output_memos.values())
    print(f"\nWrote {OUTPUT_PATH} ({total} memos)")


if __name__ == "__main__":
    main()
