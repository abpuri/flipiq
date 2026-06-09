"""Tests for the memo pre-generation pipeline (generate_memos.py)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_memos import generate_for_strategy, zip_key
from src.narrative_generator import NarrativeError


class TestZipKey:
    def test_pads_to_five_digits(self):
        assert zip_key(61925) == "61925"
        assert zip_key(2155) == "02155"
        assert zip_key("2155") == "02155"

    def test_handles_float_region_names(self):
        # CSV round-trips can turn ZIPs into floats like 61925.0
        assert zip_key(61925.0) == "61925"


def make_df(zips):
    return pd.DataFrame([
        {"region_name": z, "city": f"City{z}", "state": "IL",
         "composite_score": 70.0}
        for z in zips
    ])


class TestGenerateForStrategy:
    def test_generates_top_n_only(self):
        calls = []

        def fake_gen(row, strategy):
            calls.append(zip_key(row["region_name"]))
            return f"memo for {row['region_name']}"

        df = make_df([61925, 62554, 62573, 62501])
        memos = generate_for_strategy(df, "Balanced", {}, top_n=2,
                                      generator=fake_gen)
        assert calls == ["61925", "62554"]
        assert memos == {"61925": "memo for 61925", "62554": "memo for 62554"}

    def test_existing_memos_skipped(self):
        calls = []

        def fake_gen(row, strategy):
            calls.append(zip_key(row["region_name"]))
            return "new memo"

        existing = {"61925": "old memo"}
        df = make_df([61925, 62554])
        memos = generate_for_strategy(df, "Balanced", existing, top_n=2,
                                      generator=fake_gen)
        assert calls == ["62554"]
        assert memos["61925"] == "old memo"  # preserved, not regenerated
        assert memos["62554"] == "new memo"

    def test_force_regenerates(self):
        df = make_df([61925])
        memos = generate_for_strategy(
            df, "Balanced", {"61925": "old"}, top_n=1, force=True,
            generator=lambda row, s: "fresh",
        )
        assert memos["61925"] == "fresh"

    def test_failure_does_not_abort_batch(self):
        def flaky_gen(row, strategy):
            if zip_key(row["region_name"]) == "61925":
                raise NarrativeError("rate limited")
            return "ok"

        df = make_df([61925, 62554])
        memos = generate_for_strategy(df, "Balanced", {}, top_n=2,
                                      generator=flaky_gen)
        assert "61925" not in memos
        assert memos["62554"] == "ok"
