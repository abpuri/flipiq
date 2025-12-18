# System Architecture

## Overview

FlipIQ is built on a modular, agent-based architecture designed for scalability and maintainability. The system processes real estate data through a pipeline that culminates in actionable intelligence delivered via an interactive dashboard.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Streamlit Dashboard                              │   │
│  │  ┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐ │   │
│  │  │   Top    │Geographic│  Score   │  Market  │ Compare  │ Agent  │ │   │
│  │  │  Opps    │   View   │ Analysis │  Trends  │   ZIPs   │Monitor │ │   │
│  │  └──────────┴──────────┴──────────┴──────────┴──────────┴────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT ORCHESTRATION                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AgentOrchestrator                               │   │
│  │  Coordinates agent execution, manages state, handles scheduling      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │  Data    │ Scoring  │Detection │ Property │  Alert   │  Report  │      │
│  │ Refresh  │  Agent   │  Agent   │ Analysis │  Agent   │Generator │      │
│  │  Agent   │          │          │  Agent   │          │  Agent   │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CORE SERVICES                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Scoring Engine │  │    Property     │  │  Alert System   │             │
│  │  - 5-factor     │  │    Analyzer     │  │  - Priorities   │             │
│  │  - 3 strategies │  │  - Trends       │  │  - Thresholds   │             │
│  │  - Normalization│  │  - Momentum     │  │  - Templates    │             │
│  │                 │  │  - Risk         │  │  - Notifications│             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Data Loader                                   │   │
│  │  - CSV parsing        - Column normalization    - Date handling      │   │
│  │  - Wide-to-long       - Missing data handling   - Validation         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐      │
│  │  ZHVI    │  ZHVI    │  Market  │  Days to │  Price   │ Sale-to- │      │
│  │All Homes │Bottom Tr │   Heat   │ Pending  │   Cuts   │   List   │      │
│  │  (ZIP)   │ (County) │  (Metro) │  (Metro) │  (Metro) │  (Metro) │      │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Zillow     │     │    Data      │     │   Scoring    │     │    Agent     │
│    CSVs      │────▶│   Loader     │────▶│   Engine     │────▶│   System     │
│  (6 files)   │     │              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                                                                       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Dashboard   │◀────│    Alert     │◀────│   Property   │◀────│  Detection   │
│  (Streamlit) │     │   System     │     │   Analyzer   │     │   Results    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Data Flow Steps

1. **Ingest** — Raw Zillow CSVs loaded from `data/raw/zillow/`
2. **Transform** — Data Loader normalizes columns, handles dates, validates
3. **Score** — Scoring Engine computes 5-factor composite scores for each ZIP
4. **Detect** — Agent System identifies new/changed opportunities
5. **Analyze** — Property Analyzer performs deep-dive on top opportunities
6. **Alert** — Alert System generates HOT/WARM/WATCH notifications
7. **Display** — Dashboard renders interactive visualizations

---

## Component Details

### 1. Data Pipeline (`src/data_loader.py`)

**Purpose:** Load, validate, and transform raw Zillow datasets.

```python
# Key functions
load_all_datasets()       # Load all 6 datasets into dict
get_date_columns(df)      # Extract date columns (YYYY-MM-DD format)
get_metadata_columns(df)  # Extract non-date columns
melt_to_long_format(df)   # Convert wide → long format
```

**Datasets Processed:**

| Dataset | Granularity | Records | Key Columns |
|---------|-------------|---------|-------------|
| ZHVI All Homes | ZIP | 26,307 | region_name, city, state, metro, date columns |
| ZHVI Bottom Tier | County | 3,001 | region_name, state_name, date columns |
| Market Heat | Metro | 928 | region_name, date columns |
| Days to Pending | Metro | 702 | region_name, date columns |
| Price Cuts | Metro | 928 | region_name, date columns |
| Sale to List | Metro | 192 | region_name, date columns |

---

### 2. Scoring Engine (`src/scoring_engine.py`)

**Purpose:** Compute composite opportunity scores using 5-factor model.

```python
# Key components
@dataclass
class FlipStrategy:
    appreciation_weight: float
    velocity_weight: float
    distress_weight: float
    pricing_power_weight: float
    value_gap_weight: float

# Predefined strategies
FAST_FLIP      # Prioritizes velocity (0.35) and appreciation (0.25)
VALUE_ADD_FLIP # Prioritizes value_gap (0.30) and distress (0.25)
BALANCED       # Equal weights (0.20 each)

# Main function
flip_opportunity_score(datasets, strategy, min_value, max_value) → DataFrame
```

**Scoring Algorithm:**

1. Calculate 12-month appreciation from ZHVI
2. Get latest days-to-pending (velocity)
3. Get latest price-cut percentage (distress)
4. Get latest sale-to-list ratio (pricing power)
5. Calculate value gap (bottom tier vs all homes)
6. Normalize each metric to 0-100 scale
7. Apply strategy weights
8. Return composite score

---

### 3. Agent System (`src/agent_workflow.py`)

**Purpose:** Orchestrate autonomous agents for end-to-end workflow automation.

#### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentOrchestrator                           │
│  - Manages agent lifecycle                                      │
│  - Maintains shared state (AgentState)                          │
│  - Coordinates execution order                                  │
│  - Persists logs and state to disk                             │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ DataRefreshAgent│  │  ScoringAgent   │  │ DetectionAgent  │
│ - Check new data│  │ - Run scoring   │  │ - Find new opps │
│ - Track version │  │ - All ZIPs      │  │ - Track changes │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│PropertyAnalysis │  │   AlertAgent    │  │ReportGenerator  │
│ - Deep dives    │  │ - Create alerts │  │ - Weekly reports│
│ - Top N opps    │  │ - Set priority  │  │ - Summaries     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

#### Agent Execution Flow

```python
# Typical daily run
orchestrator.run_daily_check(context)
  → DataRefreshAgent.run()      # Check for new data
  → ScoringAgent.run()          # Compute scores
  → OpportunityDetectionAgent.run()  # Find opportunities
  → PropertyAnalysisAgent.run() # Analyze top opps
  → AlertAgent.run()            # Generate alerts

# Weekly run (Sundays)
orchestrator.run_weekly_report(context)
  → ReportGeneratorAgent.run()  # Create weekly summary
```

---

### 4. Property Analyzer (`src/property_analyzer.py`)

**Purpose:** Perform comprehensive analysis on individual ZIP codes.

```python
# Analysis components
@dataclass
class TrendAnalysis:
    current_value, yoy_change_pct, trend_direction, volatility_score

@dataclass
class MomentumScore:
    momentum_score, momentum_grade, velocity_score, demand_score

@dataclass
class RiskAssessment:
    overall_risk_score, risk_grade, market_risk, liquidity_risk

@dataclass
class InvestmentRecommendation:
    action, confidence, target_price, estimated_profit, exit_strategy

# Main class
PropertyAnalyzer.analyze_zip(zip_code) → PropertyAnalysisReport
```

---

### 5. Alert System (`src/alert_system.py`)

**Purpose:** Generate, store, and manage priority-based alerts.

```python
# Priority levels
class AlertPriority(Enum):
    HOT   # Score ≥70 or new opportunity ≥60
    WARM  # Score ≥60 or score change ≥5
    WATCH # Score ≥50
    INFO  # Everything else

# Alert configuration
@dataclass
class AlertConfig:
    hot_score_threshold: float = 70.0
    warm_score_threshold: float = 60.0
    score_change_hot: float = 10.0
    alert_cooldown_hours: int = 24

# Main class
AlertManager.create_alert()
AlertManager.get_alerts(priority, since, limit)
AlertManager.acknowledge_alert(alert_id)
```

---

### 6. Dashboard (`streamlit_app.py`)

**Purpose:** Interactive web interface for analysis and monitoring.

#### Tab Structure

| Tab | Components |
|-----|------------|
| **Top Opportunities** | Data table, score columns, CSV export |
| **Geographic View** | US choropleth, state/metro bar charts |
| **Score Analysis** | Histograms, box plots, correlation heatmap, scatter plots |
| **Market Trends** | Time series line charts, YoY change visualization |
| **Compare ZIPs** | Side-by-side table, radar chart, trend comparison |
| **Agent Monitoring** | Status panel, alerts list, timeline charts, decision logs, deep dive |

---

## Production Architecture

For a production deployment with live data, the architecture would extend to:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Zillow     │     │     MLS      │     │   County     │
│     API      │     │    Feeds     │     │   Records    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
              ┌──────────────────────────┐
              │    Data Ingestion Layer   │
              │  (Airflow / Prefect)      │
              │  - Scheduled monthly      │
              │  - Incremental updates    │
              │  - Data validation        │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │      Data Warehouse       │
              │  (PostgreSQL / Snowflake) │
              │  - Historical data        │
              │  - User configurations    │
              │  - Alert history          │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │     Agent Scheduler       │
              │  (Celery / Airflow)       │
              │  - Daily scoring jobs     │
              │  - Alert generation       │
              │  - Weekly reports         │
              └────────────┬─────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │   Email    │  │    SMS     │  │    Push    │
    │  (SendGrid)│  │  (Twilio)  │  │  (Firebase)│
    └────────────┘  └────────────┘  └────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │      API Gateway          │
              │  (FastAPI / Django)       │
              │  - REST endpoints         │
              │  - Authentication         │
              │  - Rate limiting          │
              └────────────┬─────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │    Web     │  │   Mobile   │  │  Third-    │
    │ Dashboard  │  │    App     │  │  Party API │
    └────────────┘  └────────────┘  └────────────┘
```

### Production Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Data Ingestion** | Airflow / Prefect | Scheduled data pipeline orchestration |
| **Data Warehouse** | PostgreSQL / Snowflake | Persistent storage, user data |
| **Job Scheduler** | Celery + Redis | Async agent execution |
| **API Layer** | FastAPI | REST API for web/mobile clients |
| **Authentication** | Auth0 / Firebase Auth | User management |
| **Alert Delivery** | SendGrid, Twilio, Firebase | Multi-channel notifications |
| **Caching** | Redis | Session state, API caching |
| **Monitoring** | DataDog / CloudWatch | System health, alerting |

### Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Data Refresh | Monthly (16th) | Pull new Zillow data releases |
| Full Scoring | Monthly | Recompute all ZIP scores |
| Delta Detection | Daily (6am) | Identify new/changed opportunities |
| Alert Generation | Daily (7am) | Create alerts for qualifying ZIPs |
| Weekly Report | Sundays | Generate weekly summary |
| Data Cleanup | Monthly | Archive old alerts, compress logs |

---

## Technology Choices

### Why Python?

- Rich data science ecosystem (Pandas, NumPy, Scikit-learn)
- Streamlit enables rapid dashboard development
- Easy prototyping and iteration
- Strong community for real estate data processing

### Why Streamlit?

- Rapid prototyping (days vs weeks)
- Python-native (no frontend expertise needed)
- Built-in state management
- Easy deployment to Streamlit Cloud

### Why Agent Architecture?

- Modular design enables independent testing
- Clear separation of concerns
- Easier to add new agents (e.g., ML prediction agent)
- Natural fit for scheduled workflows
- Each agent can be scaled independently in production

### Why 5-Factor Scoring?

- Captures multiple dimensions of opportunity quality
- Weights can be tuned per strategy/user preference
- Normalization enables apples-to-apples comparison
- Interpretable (users understand why a score is high)
- Extensible (can add more factors)

---

## Data Model

### Core Entities

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    ZIPCode      │     │     Score       │     │     Alert       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ region_name (PK)│────▶│ region_name (FK)│────▶│ alert_id (PK)   │
│ city            │     │ composite_score │     │ zip_code (FK)   │
│ state           │     │ appreciation_sc │     │ priority        │
│ metro           │     │ velocity_score  │     │ timestamp       │
│ county          │     │ distress_score  │     │ current_score   │
│ current_value   │     │ pricing_power_sc│     │ trigger_reason  │
│ appreciation_pct│     │ value_gap_score │     │ acknowledged    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### State Management

```python
@dataclass
class AgentState:
    last_data_refresh: datetime
    last_scoring_run: datetime
    last_detection_run: datetime
    last_alert_generation: datetime
    last_report_generation: datetime
    data_version: str
    total_opportunities_detected: int
    opportunities_this_week: int
    known_opportunity_hashes: Set[str]
```

---

## Security Considerations

### MVP (Current)

- No authentication (single-user local deployment)
- Data stored on local filesystem
- No PII in processed data

### Production Requirements

| Area | Requirement |
|------|-------------|
| **Authentication** | OAuth2 / JWT for API access |
| **Authorization** | Role-based access (admin, user, viewer) |
| **Encryption** | TLS for transit, AES-256 for rest |
| **Data Privacy** | No PII storage, GDPR compliance |
| **Audit Logging** | All data access logged |
| **Rate Limiting** | API rate limits per user tier |

---

## Performance Characteristics

### Current (MVP)

| Operation | Time | Notes |
|-----------|------|-------|
| Load all datasets | ~3s | 6 CSV files, 31K total rows |
| Compute all scores | ~5s | 26K ZIPs |
| Full dashboard load | ~8s | Cached after first load |
| Property deep dive | ~1s | Single ZIP analysis |
| 90-day simulation | ~2min | Generates 500+ alerts |

### Production Targets

| Operation | Target | Strategy |
|-----------|--------|----------|
| API response | <200ms | Caching, pre-computed scores |
| Dashboard load | <3s | CDN, lazy loading |
| Alert generation | <5min | Parallel processing |
| Full refresh | <30min | Incremental updates |

---

## Extensibility Points

### Adding a New Agent

```python
class NewAgent(BaseAgent):
    def __init__(self, output_dir):
        super().__init__("NewAgent", output_dir)

    def run(self, context: dict) -> dict:
        # Implement agent logic
        self.log("action", "status", {"details": {}})
        return {"result": "success"}

# Register with orchestrator
orchestrator.agents.append(NewAgent(output_dir))
```

### Adding a New Scoring Factor

```python
# In scoring_engine.py
def _calculate_new_factor(row, datasets):
    # Implement calculation
    return normalized_score

# Add to FlipStrategy dataclass
@dataclass
class FlipStrategy:
    # ... existing weights ...
    new_factor_weight: float = 0.10

# Include in composite calculation
composite = (
    appreciation * weights.appreciation_weight +
    # ... existing factors ...
    new_factor * weights.new_factor_weight
)
```

### Adding a New Dashboard Tab

```python
# In streamlit_app.py
tab1, tab2, ..., tab7 = st.tabs([
    "...", "...", "...", "...", "...", "...",
    "New Tab"
])

with tab7:
    st.subheader("New Analysis")
    # Implement tab content
```
