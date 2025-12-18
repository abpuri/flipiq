# FlipIQ Demo Script

## 5-Minute Walkthrough

This script guides you through demonstrating FlipIQ's key capabilities. Designed for portfolio presentations, investor meetings, or technical interviews.

---

## Pre-Demo Setup

```bash
# Ensure simulation data exists
python workflows/simulate_agent_run.py --days 90

# Launch dashboard
streamlit run streamlit_app.py
```

**Verify:** Dashboard loads at `http://localhost:8501`

---

## Demo Flow (5 Minutes)

### Opening (30 seconds)

**Say:**
> "FlipIQ is an AI-powered opportunity detection platform for house flippers. It uses autonomous agents to analyze 26,000+ US ZIP codes and proactively surface high-potential flip opportunities—before they become obvious to the competition."

**Key Point:** Emphasize "proactive" vs "reactive" — this is the core differentiator.

---

### Part 1: The Problem (30 seconds)

**Say:**
> "House flippers currently spend 40+ hours per month manually researching markets. They use tools like PropStream and DealMachine, but these are reactive—you have to search for opportunities. FlipIQ flips this model: opportunities come to you."

**Don't show anything yet** — set up the contrast before showing the solution.

---

### Part 2: Top Opportunities (1 minute)

**Navigate to:** Tab 1 - Top Opportunities

**Show:**
1. The ranked list of ZIPs with composite scores
2. Hover over a few rows to show the detail columns
3. Point out the 5 score components (appreciation, velocity, distress, etc.)

**Say:**
> "This is a ranked list of 26,000+ ZIP codes scored by our 5-factor model. Each factor captures a different dimension of flip potential: appreciation for price growth, velocity for how fast homes sell, distress for motivated sellers, and so on."

**Action:** Adjust the "Minimum Score" slider from 50 to 60

**Say:**
> "Users can filter by score threshold, price range, and geography. This surfaces only the opportunities that meet their criteria."

---

### Part 3: Geographic Intelligence (45 seconds)

**Navigate to:** Tab 2 - Geographic View

**Show:**
1. The US choropleth map (hover over states)
2. The "Top 15 States by Avg Score" bar chart
3. The metro area analysis

**Say:**
> "The geographic view shows where opportunities are concentrated. Right now, we can see that [point to high-scoring states] are showing strong flip potential. Users can drill down to specific metros to find the best markets."

**Key Point:** This replaces hours of manual geographic research.

---

### Part 4: Agent Monitoring (1.5 minutes)

**Navigate to:** Tab 6 - Agent Monitoring

**Show:**
1. Agent Status Panel (6 green checkmarks)
2. Recent Alerts Section

**Say:**
> "This is where FlipIQ really differentiates. We have 6 autonomous agents working 24/7: data refresh, scoring, opportunity detection, property analysis, alerting, and reporting."

**Action:** Filter alerts by "HOT" priority

**Show:** Expand one HOT alert to show details

**Say:**
> "HOT alerts are the highest priority—these are ZIPs with scores above 70 or new opportunities above 60. Each alert includes the trigger reason and a recommended action. In our 90-day simulation, we generated 538 alerts, including 171 HOT alerts."

**Action:** Scroll down to Opportunity Timeline

**Show:** The cumulative charts

**Say:**
> "The timeline shows how opportunities accumulate over time. Notice the spikes—those correspond to data refresh days when the system detects changes in the market."

---

### Part 5: Property Deep Dive (45 seconds)

**Navigate to:** Still in Agent Monitoring tab, scroll to "Property Deep Dive"

**Action:** Select a ZIP from the dropdown, click "Analyze ZIP"

**Show:** The full analysis output

**Say:**
> "For any opportunity, users can do a one-click deep dive. This shows trend analysis—is the market going up or down, how volatile is it. Momentum scoring—is demand accelerating. Risk assessment—what could go wrong. And finally, an investment recommendation: buy, hold, or avoid."

**Point out:**
- Trend direction and strength
- Recommendation action (BUY/HOLD/AVOID)
- Estimated profit calculation
- Exit strategy suggestion

**Say:**
> "This replaces 30 minutes of manual research with a 1-second analysis."

---

### Part 6: Closing (30 seconds)

**Say:**
> "To recap: FlipIQ analyzes 26,000+ ZIP codes using a 5-factor scoring model. Six autonomous agents work around the clock to detect opportunities and generate alerts. Users get proactive intelligence delivered to them—no more manual searching."

**Key Metrics to Mention:**
- 26,307 ZIPs analyzed
- 6 autonomous agents
- 90-day simulation with 538 alerts
- 5-factor scoring model

**If time permits:** Show the Compare ZIPs tab (radar chart) or Market Trends (time series).

---

## Key Points to Emphasize

### Business Value

| Point | Supporting Evidence |
|-------|---------------------|
| **Saves 40 hours/month** | Replaces manual market research |
| **30-60 days earlier** | Proactive alerts vs reactive searching |
| **One-click analysis** | Property deep dive in seconds |
| **Prioritized workflow** | HOT/WARM/WATCH eliminates noise |

### Technical Differentiators

| Feature | Why It Matters |
|---------|----------------|
| **Agent architecture** | Autonomous, scalable, maintainable |
| **5-factor scoring** | Multidimensional analysis, not just price |
| **Strategy presets** | Customizable for different flip styles |
| **Proactive alerts** | Push vs pull model |

### What Makes This MVP Impressive

1. **End-to-end system** — Not just a model, but a complete workflow
2. **Working simulation** — 90 days of realistic agent activity
3. **Production-ready architecture** — Clear path to live deployment
4. **Business viability** — Backed by market research and financial projections

---

## Common Questions & Answers

### "How accurate is the scoring?"

> "The 5-factor model is backtested against historical data. Each factor is normalized to a 0-100 scale and weighted according to the chosen strategy. In testing, ZIPs with scores above 70 consistently show 5%+ appreciation and sub-45-day liquidity."

### "What data do you use?"

> "We use Zillow Research's public datasets: ZHVI for home values at the ZIP level, plus metro-level indicators for market velocity, price cuts, and sale-to-list ratios. For production, we'd integrate MLS data for property-level analysis."

### "How does the agent system work?"

> "Six specialized agents handle different parts of the workflow. The Data Refresh Agent monitors for new Zillow releases. The Scoring Agent computes scores. The Detection Agent identifies changes. The Analysis Agent performs deep dives. The Alert Agent generates notifications. And the Report Agent creates weekly summaries. They're coordinated by an orchestrator that manages state and execution order."

### "What would production deployment look like?"

> "The architecture document details this. We'd add scheduled jobs (Airflow/Celery) for daily agent runs, a database layer for multi-user support, authentication, and alert delivery via email/SMS/push. The core scoring and agent logic stays the same."

### "Why is this better than PropStream?"

> "PropStream is a search tool—you query for properties. FlipIQ is an intelligence platform—opportunities come to you. We use AI agents that work 24/7, analyze entire markets, and push alerts. It's the difference between fishing with a rod and fishing with a net."

---

## Demo Variations

### For Technical Audiences (Engineers/Investors)

Add time to show:
- `docs/architecture.md` — System design diagrams
- `src/scoring_engine.py` — 5-factor model implementation
- `src/agent_workflow.py` — Agent class structure

### For Business Audiences (Investors/Partners)

Add time to show:
- `landing_page.html` — Marketing positioning
- `docs/market_analysis.md` — TAM/SAM/SOM
- `docs/unit_economics.md` — LTV/CAC, pricing model

### For Quick Showcase (2 minutes)

Focus only on:
1. Top Opportunities tab (30 sec)
2. Agent Monitoring tab with HOT alerts (1 min)
3. Property Deep Dive (30 sec)

---

## Screenshot Guide

For static presentations, capture:

1. **Hero Shot:** Top Opportunities tab with data table
2. **Geographic View:** US choropleth map
3. **Agent Dashboard:** Agent status panel + HOT alerts
4. **Timeline:** Cumulative opportunities chart
5. **Deep Dive:** Property analysis output

---

## Troubleshooting

### Dashboard Won't Load

```bash
# Check Streamlit is installed
pip install streamlit

# Run with explicit host
streamlit run streamlit_app.py --server.address localhost
```

### No Agent Data

```bash
# Re-run simulation
python workflows/simulate_agent_run.py --days 90
```

### Slow Loading

- First load caches data (~8 seconds)
- Subsequent loads are faster (~3 seconds)
- Reduce "Top N Results" slider to speed up rendering

---

## Post-Demo Resources

Share these links:
- **GitHub Repository:** [link]
- **Live Demo (if hosted):** [link]
- **Architecture Docs:** `docs/architecture.md`
- **Business Plan:** `docs/investor_memo.md`
