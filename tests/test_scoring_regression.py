"""Regression check: scoring engine output is unchanged by the AI memo work.

Traces a sample ZIP through the composite-score math and verifies the
pre-scored CSVs still reconcile with the strategy weights.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scoring_engine import BALANCED, FAST_FLIP, VALUE_ADD_FLIP

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

STRATEGIES = [
    ("top_opportunities_balanced.csv", BALANCED),
    ("top_opportunities_fast_flip.csv", FAST_FLIP),
    ("top_opportunities_value_add_flip.csv", VALUE_ADD_FLIP),
]


@pytest.mark.parametrize("filename,strategy", STRATEGIES)
def test_composite_is_weighted_sum_of_components(filename, strategy):
    path = PROCESSED / filename
    if not path.exists():
        pytest.skip(f"{filename} not present")
    df = pd.read_csv(path).head(50)

    # Mirror the engine: missing metro/county scores are imputed at 50
    expected = (
        df["appreciation_score"] * strategy.appreciation_weight
        + df["velocity_score"].fillna(50) * strategy.velocity_weight
        + df["distress_score"].fillna(50) * strategy.distress_weight
        + df["pricing_power_score"].fillna(50) * strategy.pricing_power_weight
        + df["value_gap_score"].fillna(50) * strategy.value_gap_weight
    )
    assert (df["composite_score"] - expected).abs().max() < 0.01


def test_sample_zip_trace():
    """Trace ZIP 61925 (rank 1 balanced): facts used by the AI memo match
    the scored CSV exactly."""
    path = PROCESSED / "top_opportunities_balanced.csv"
    if not path.exists():
        pytest.skip("balanced CSV not present")
    df = pd.read_csv(path)
    row = df[df["region_name"] == 61925].iloc[0]

    from src.narrative_generator import build_zip_facts

    facts = build_zip_facts(row, "Balanced")
    assert facts["composite_score_0_100"] == round(row["composite_score"], 2)
    assert (facts["signals"]["appreciation"]["value_change_12mo_pct"]
            == round(row["appreciation_pct"], 2))
    assert (facts["signals"]["velocity"]["days_to_pending"]
            == round(row["days_to_pending"], 2))
