"""Tests for src/narrative_generator.py — no network calls, API is mocked."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.narrative_generator import (
    NarrativeError,
    build_user_prompt,
    build_zip_facts,
    generate_deal_thesis,
)


@pytest.fixture
def sample_row():
    return pd.Series({
        "region_name": "61925",
        "city": "Dalton City",
        "state": "IL",
        "metro": "Decatur, IL",
        "county_name": "Macon County",
        "current_value": 198539.27,
        "appreciation_pct": 12.63,
        "appreciation_score": 100.0,
        "velocity_score": 97.93,
        "distress_score": 67.66,
        "pricing_power_score": np.nan,
        "value_gap_score": 68.92,
        "composite_score": 76.9,
        "days_to_pending": 27.0,
        "price_cut_pct": 26.12,
        "sale_to_list": np.nan,
        "value_gap_pct": 266.39,
    })


class TestBuildZipFacts:
    def test_core_fields(self, sample_row):
        facts = build_zip_facts(sample_row, "Balanced")
        assert facts["zip_code"] == "61925"
        assert facts["city"] == "Dalton City"
        assert facts["strategy"] == "Balanced"
        assert facts["composite_score_0_100"] == 76.9
        assert facts["current_home_value_usd"] == 198539.27

    def test_signal_values_and_levels(self, sample_row):
        facts = build_zip_facts(sample_row)
        sig = facts["signals"]
        assert sig["appreciation"]["value_change_12mo_pct"] == 12.63
        assert sig["appreciation"]["level"] == "ZIP"
        assert sig["velocity"]["days_to_pending"] == 27.0
        assert sig["velocity"]["level"] == "metro"
        assert sig["value_gap"]["level"] == "county"

    def test_nan_signal_dropped(self, sample_row):
        facts = build_zip_facts(sample_row)
        # pricing_power_score is NaN → entire signal removed
        assert "pricing_power" not in facts["signals"]

    def test_nan_metric_within_signal_dropped(self, sample_row):
        row = sample_row.copy()
        row["days_to_pending"] = np.nan
        facts = build_zip_facts(row)
        assert "days_to_pending" not in facts["signals"]["velocity"]
        assert facts["signals"]["velocity"]["score_0_100"] == 97.93

    def test_facts_are_json_serializable(self, sample_row):
        json.dumps(build_zip_facts(sample_row))


class TestBuildUserPrompt:
    def test_contains_key_numbers(self, sample_row):
        prompt = build_user_prompt(build_zip_facts(sample_row, "Fast Flip"))
        assert "61925" in prompt
        assert "12.63" in prompt
        assert "Fast Flip" in prompt
        assert "NaN" not in prompt


class TestGenerateDealThesis:
    def test_no_api_key_raises(self, sample_row, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(NarrativeError, match="No Anthropic API key"):
            generate_deal_thesis(sample_row)

    def _mock_client(self, text="## Deal Thesis\nStrong market."):
        block = MagicMock()
        block.type = "text"
        block.text = text
        response = MagicMock()
        response.content = [block]
        client = MagicMock()
        client.messages.create.return_value = response
        return client

    def test_successful_generation(self, sample_row):
        client = self._mock_client()
        with patch("anthropic.Anthropic", return_value=client):
            result = generate_deal_thesis(sample_row, "Balanced", api_key="test-key")
        assert result == "## Deal Thesis\nStrong market."

        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-opus-4-8"
        assert "61925" in kwargs["messages"][0]["content"]
        assert "house flippers" in kwargs["system"]

    def test_model_override(self, sample_row):
        client = self._mock_client()
        with patch("anthropic.Anthropic", return_value=client):
            generate_deal_thesis(sample_row, api_key="k", model="claude-haiku-4-5")
        assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"

    def test_empty_response_raises(self, sample_row):
        client = self._mock_client(text="   ")
        with patch("anthropic.Anthropic", return_value=client):
            with pytest.raises(NarrativeError, match="empty response"):
                generate_deal_thesis(sample_row, api_key="k")

    def test_api_error_wrapped(self, sample_row):
        import anthropic
        client = MagicMock()
        client.messages.create.side_effect = anthropic.APIConnectionError(
            request=MagicMock()
        )
        with patch("anthropic.Anthropic", return_value=client):
            with pytest.raises(NarrativeError, match="Claude API error"):
                generate_deal_thesis(sample_row, api_key="k")
