"""
Generate JSON data file for the HTML dashboard.

Converts pre-scored CSV files to a single JSON bundle consumed by dashboard.html.
Run after refreshing data or recomputing scores:
    python generate_dashboard_data.py
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "dashboard_data.json"

STRATEGY_FILES = {
    "balanced": "top_opportunities_balanced.csv",
    "fast_flip": "top_opportunities_fast_flip.csv",
    "value_add": "top_opportunities_value_add_flip.csv",
}


def load_csv(filename: str) -> list:
    path = PROCESSED_DIR / filename
    if not path.exists():
        print(f"  WARNING: {filename} not found, skipping")
        return []
    df = pd.read_csv(path)
    # Round floats then replace NaN/inf with None
    float_cols = df.select_dtypes("float64").columns
    df[float_cols] = df[float_cols].round(2)
    df = df.where(pd.notna(df), None)
    records = df.to_dict(orient="records")
    # Sanitize any remaining non-finite floats (inf, -inf)
    import math
    def clean(v):
        if isinstance(v, float) and not math.isfinite(v):
            return None
        return v
    return [{k: clean(v) for k, v in r.items()} for r in records]


def state_summary(records: list) -> dict:
    buckets = defaultdict(lambda: {"scores": [], "values": [], "count": 0})
    for r in records:
        s = r.get("state")
        if not s:
            continue
        score = r.get("composite_score")
        value = r.get("current_value")
        if score is not None:
            buckets[s]["scores"].append(score)
        if value is not None:
            buckets[s]["values"].append(value)
        buckets[s]["count"] += 1

    out = {}
    for state, d in buckets.items():
        scores = d["scores"]
        values = sorted(d["values"])
        out[state] = {
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "count": d["count"],
            "median_value": values[len(values) // 2] if values else 0,
        }
    return out


def main():
    print("Generating dashboard data...")
    strategies = {}
    for key, filename in STRATEGY_FILES.items():
        records = load_csv(filename)
        strategies[key] = records
        print(f"  {key}: {len(records)} records")

    output = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        **strategies,
        "state_summary": state_summary(strategies.get("balanced", [])),
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"), allow_nan=False)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
