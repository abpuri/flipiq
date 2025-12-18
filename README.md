# FlipIQ: AI-Powered House Flip Opportunity Detection

> **Autonomous agent system that identifies high-potential real estate flip opportunities using Zillow data, predictive scoring, and proactive market intelligence.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## The Problem

House flippers spend **40+ hours per month** manually researching markets across fragmented tools, missing **80% of emerging opportunities** due to reactive workflows. Current solutions require constant monitoring and provide historical data—not actionable intelligence.

## The Solution

FlipIQ is an **AI-powered opportunity detection platform** that deploys autonomous agents to monitor 26,000+ US ZIP codes, score opportunities using a proprietary 5-factor model, and proactively alert investors to high-potential markets **30-60 days before competitors**.

### Key Features

- **Proactive Alert System** — HOT/WARM/WATCH priority notifications based on customizable thresholds
- **5-Factor Scoring Engine** — Composite scores combining appreciation, velocity, distress, pricing power, and value gap
- **6 Autonomous Agents** — End-to-end workflow automation from data refresh to report generation
- **Interactive Dashboard** — 6-tab Streamlit interface for analysis, visualization, and deep-dives
- **Property Deep Dive** — Comprehensive analysis with trend, momentum, risk, and investment recommendations

---

## Project Highlights

| Metric | Value |
|--------|-------|
| ZIP Codes Analyzed | **26,307** |
| Autonomous Agents | **6** |
| Simulation Period | **90 days** |
| Alerts Generated | **538** (171 HOT, 367 WARM) |
| Scoring Factors | **5** |
| Dashboard Tabs | **6** |
| Strategy Presets | **3** (Fast Flip, Value-Add, Balanced) |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.9+ |
| **Data Processing** | Pandas, NumPy |
| **Machine Learning** | Scikit-learn (normalization, scoring) |
| **Visualization** | Plotly, Matplotlib, Seaborn |
| **Dashboard** | Streamlit |
| **Architecture** | Agent-based orchestration pattern |
| **Data Source** | Zillow Research (public datasets) |

---

## Repository Structure

```
zillow/
├── data/
│   ├── raw/zillow/              # Original Zillow CSV datasets (6 files)
│   └── processed/
│       ├── agent_logs/          # Simulation outputs (alerts, logs, reports)
│       └── *.csv                # Scored opportunities by strategy
│
├── src/
│   ├── data_loader.py           # Dataset loading & transformation
│   ├── scoring_engine.py        # 5-factor opportunity scoring
│   ├── agent_workflow.py        # 6 autonomous agents + orchestrator
│   ├── property_analyzer.py     # Deep-dive property analysis
│   └── alert_system.py          # Alert generation & management
│
├── workflows/
│   └── simulate_agent_run.py    # 90-day agent simulation script
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_opportunity_scoring.ipynb
│   └── 03_agent_simulation.ipynb
│
├── docs/
│   ├── architecture.md          # System architecture & design
│   ├── DEMO.md                  # 5-minute demo walkthrough
│   ├── market_analysis.md       # TAM/SAM/SOM analysis
│   ├── unit_economics.md        # LTV, CAC, pricing model
│   ├── financial_projections.md # 3-year financial model
│   ├── investor_pitch_deck_content.md
│   ├── investor_memo.md         # Confidential investment memo
│   └── risk_analysis.md         # Comprehensive risk assessment
│
├── streamlit_app.py             # Main dashboard application
├── landing_page.html            # Marketing landing page
└── requirements.txt             # Python dependencies
```

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/flipiq.git
cd flipiq

# Install dependencies
pip install -r requirements.txt
```

### Running the Dashboard

```bash
# Launch Streamlit dashboard
streamlit run streamlit_app.py
```

The dashboard will open at `http://localhost:8501`

### Running the Agent Simulation

```bash
# Run 90-day agent simulation (generates alerts, logs, reports)
python workflows/simulate_agent_run.py --days 90
```

### Exploring the Notebooks

```bash
# Launch Jupyter
jupyter notebook notebooks/
```

---

## Dashboard Overview

The Streamlit dashboard includes 6 interactive tabs:

| Tab | Description |
|-----|-------------|
| **Top Opportunities** | Ranked list of flip opportunities with composite scores |
| **Geographic View** | US choropleth map and state/metro analysis |
| **Score Analysis** | Score distributions, correlations, scatter plots |
| **Market Trends** | ZHVI time series and YoY appreciation charts |
| **Compare ZIPs** | Side-by-side ZIP code comparison with radar chart |
| **Agent Monitoring** | Agent status, alerts, timeline, decision logs, deep dive |

---

## Key Deliverables

### 1. Technical MVP
- Fully functional scoring engine analyzing 26K+ ZIPs
- 6 autonomous agents with orchestration
- Interactive 6-tab dashboard
- Property analysis with investment recommendations

### 2. Business Documentation
- Market analysis with $118B TAM sizing
- Unit economics (5.4:1 LTV:CAC)
- 3-year financial projections ($10.7M ARR)
- Comprehensive risk analysis (19 risks, 6 categories)

### 3. Investor Materials
- 13-slide pitch deck content
- Confidential investment memorandum
- One-page executive summary
- Professional landing page

---

## Scoring Model

The 5-factor composite score (0-100) combines:

| Factor | Weight | Signal |
|--------|--------|--------|
| **Appreciation** | 25% | 12-month price growth (ZHVI) |
| **Velocity** | 25% | Days to pending sale (liquidity) |
| **Distress** | 20% | % of listings with price cuts |
| **Pricing Power** | 15% | Sale-to-list ratio |
| **Value Gap** | 15% | Bottom-tier vs all-homes spread |

### Strategy Presets

| Strategy | Best For |
|----------|----------|
| **Fast Flip** | Quick turns, high liquidity markets |
| **Value-Add** | Renovation opportunities, distressed sellers |
| **Balanced** | General-purpose scoring |

---

## Agent System

The autonomous agent system includes:

| Agent | Function |
|-------|----------|
| **DataRefreshAgent** | Monitors for new Zillow data releases |
| **ScoringAgent** | Computes opportunity scores for all ZIPs |
| **OpportunityDetectionAgent** | Identifies new/changed opportunities |
| **PropertyAnalysisAgent** | Performs deep-dive analysis |
| **AlertAgent** | Generates priority-based alerts |
| **ReportGeneratorAgent** | Creates weekly summary reports |

---

## Future Roadmap

If deployed with live data infrastructure:

| Phase | Enhancement |
|-------|-------------|
| **Phase 1** | Live Zillow API integration (monthly refresh) |
| **Phase 2** | MLS data integration for property-level analysis |
| **Phase 3** | User accounts with saved searches and custom alerts |
| **Phase 4** | Mobile app with push notifications |
| **Phase 5** | ML model training on flip outcome data |

---

## Important Notes

> **This is an MVP demonstration** built to showcase the concept and technical architecture. The system uses historical Zillow Research data (2022-2025) and simulated agent runs.

> For production deployment, the system would require:
> - Live data feeds (Zillow API, MLS, county records)
> - Database layer for multi-user support
> - Authentication and authorization
> - Scheduled job infrastructure (cron/Airflow)
> - Alert delivery system (email, SMS, push)

---

## Data Sources

- [Zillow Research Data](https://www.zillow.com/research/data/) — Public datasets
- ZHVI (Zillow Home Value Index) — ZIP, County, Metro levels
- Market indicators — Days to pending, price cuts, sale-to-list ratio

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Contact

**Abhay Puri** — [LinkedIn](https://linkedin.com/in/abhaypuri) | [Email](mailto:abhay@example.com)

---

*Built with Python, Pandas, Streamlit, and a lot of real estate data.*
