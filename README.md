# FlipIQ — House Flip Opportunity Scorecard

A data-driven scoring tool that ranks 26,000+ US ZIP codes for house flip potential using Zillow Research data and a 5-factor model. Built as an interactive Streamlit dashboard.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io)

**[Live Dashboard →](https://flipiq.streamlit.app/)** &nbsp;|&nbsp; **[Landing Page →](https://abpuri.github.io/flipiq/landing_page.html)**

---

## What it does

FlipIQ scores every ZIP code in the Zillow dataset on five market signals, then surfaces the top opportunities in an interactive dashboard. A flipper can filter by state, metro, price range, and strategy preset — and see a plain-English breakdown of exactly why each ZIP ranked where it did.

**What it is not:** real-time data, property-level analysis, or a predictive model. It's a fast, systematic first-pass filter across 26K+ ZIPs — the research leg of the deal-finding process.

---

## Scoring model

Five factors, combined into a 0–100 composite score:

| Factor | Weight | Data level | Signal |
|--------|--------|------------|--------|
| **Appreciation** | 25% | ZIP | 12-month ZHVI price growth |
| **Velocity** | 25% | Metro | Days to pending (market liquidity) |
| **Distress** | 20% | Metro | % of listings with price cuts |
| **Pricing Power** | 15% | Metro | Sale-to-list ratio |
| **Value Gap** | 15% | County | Bottom-tier vs median home value spread |

**Important:** appreciation is ZIP-level (precise). The other four signals are metro- or county-level — all ZIPs within a metro share the same velocity, distress, and pricing power scores. This is a meaningful limitation for surgical analysis; the scores are directional, not surgical.

### Strategy presets

| Strategy | Best for |
|----------|----------|
| **Fast Flip** | High-turnover markets, minimal renovation |
| **Value-Add** | Renovation plays, distressed sellers |
| **Balanced** | General-purpose screening |

---

## Dashboard tabs

| Tab | What's in it |
|-----|-------------|
| **Top Opportunities** | Ranked table + plain-English score breakdown per ZIP |
| **Geographic View** | US choropleth and state/metro bar charts |
| **Score Analysis** | Distributions, correlations, scatter plots |
| **Market Trends** | ZHVI time series and YoY charts for selected ZIPs |
| **Compare ZIPs** | Side-by-side comparison with radar chart |
| **Pipeline Status** | Last pipeline run results, alerts, and timeline |

---

## Getting started

```bash
git clone https://github.com/abpuri/flipiq
cd flipiq
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## AI Deal Thesis memos

FlipIQ can generate analyst-style investment memos per ZIP using the Claude API
(`src/narrative_generator.py`). Memos synthesize all five signals into a verdict,
numbers-backed bullets, watch-outs, and a recommended next move — with the data
granularity caveats built into the prompt so the model never overstates precision.

- **HTML dashboard:** memos are pre-generated server-side (the API key never
  reaches the browser). Run `export ANTHROPIC_API_KEY=sk-ant-...` then
  `python generate_memos.py --top 25` to write `data/processed/ai_memos.json`;
  the dashboard picks it up automatically and hides the section if it's absent.
- **Streamlit app:** memos generate on demand in the Top Opportunities score
  breakdown when `ANTHROPIC_API_KEY` is set (env var or Streamlit secrets).
  Without a key, the rule-based narrative still works.

---

## Keeping data current

Zillow Research publishes updated datasets monthly (typically around the 16th). To refresh:

```bash
python refresh_data.py
```

This downloads the latest CSVs directly from Zillow Research and replaces the local files. Restart the Streamlit app afterward to load the new data.

If a download fails, verify the current URLs at [zillow.com/research/data](https://www.zillow.com/research/data/) and update `DATASET_URLS` in `refresh_data.py`.

---

## Data sources

All data is from [Zillow Research public datasets](https://www.zillow.com/research/data/):

| File | Coverage | Granularity |
|------|----------|-------------|
| `zhvi_all_homes_zip.csv` | 26,307 ZIP codes | Monthly |
| `zhvi_bottom_tier_county.csv` | 3,001 counties | Monthly |
| `market_heat_index_metro.csv` | 928 metros | Monthly |
| `days_to_pending_metro.csv` | 702 metros | Monthly |
| `price_cuts_metro.csv` | 928 metros | Monthly |
| `sale_to_list_metro.csv` | 192 metros | Weekly |

---

## Project structure

```
flipiq/
├── streamlit_app.py          # Dashboard
├── refresh_data.py           # Download latest Zillow data
├── requirements.txt
│
├── src/
│   ├── data_loader.py        # Load and standardize CSVs
│   ├── scoring_engine.py     # 5-factor scoring model
│   ├── agent_workflow.py     # Analysis pipeline (6 steps)
│   ├── property_analyzer.py  # Deep-dive ZIP analysis
│   └── alert_system.py       # Alert generation
│
├── workflows/
│   └── simulate_agent_run.py # Run full pipeline, generate alerts
│
├── data/
│   ├── raw/zillow/           # Zillow CSV datasets
│   └── processed/
│       ├── agent_logs/       # Pipeline run outputs
│       └── *.csv             # Scored results
│
└── docs/                     # Business and validation docs
```

---

## Analysis pipeline

Running `python workflows/simulate_agent_run.py` executes a 6-step pipeline:

1. **Data refresh** — checks for updated Zillow data
2. **Scoring** — computes 5-factor scores for all ZIPs
3. **Opportunity detection** — identifies new and changed opportunities
4. **Property analysis** — deep-dives on the top-ranked ZIPs
5. **Alert generation** — classifies opportunities as HOT (≥70), WARM (≥60), or WATCH (≥50)
6. **Report generation** — writes a summary to `data/processed/agent_logs/`

The Pipeline Status tab in the dashboard shows results from the last run.

---

## What's next

To turn this into a production tool, the meaningful upgrades are:

- **Richer data signals** — tax delinquencies, permit pulls, MLS days-on-market at the ZIP level
- **Outcome tracking** — log which alerts led to actual deals and use that to validate/tune the model
- **Automated refresh** — scheduled job (cron or Airflow) to pull new data on publish day
- **User accounts and saved searches** — multi-user support with personalized filters
- **Alert delivery** — email or SMS when a watched ZIP crosses a threshold

---

## Contact

**Abhay Puri** — [LinkedIn](https://linkedin.com/in/abhaypuri1)  
**Anthony Nastasi** — [LinkedIn](https://www.linkedin.com/in/anthony-g-nastasi-b8a387143/)  

Interested in testing FlipIQ on real deals? [Sign up for beta access](https://abpuri.github.io/flipiq/landing_page.html)
