"""
Agentic Workflow System for Flip Opportunity Detection

This module contains autonomous agents that work together to:
- Monitor for new data
- Score opportunities
- Detect emerging markets
- Generate alerts and reports
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class AlertPriority(Enum):
    HOT = "HOT"      # Immediate action - score >= 70, new or +10 change
    WARM = "WARM"    # Monitor closely - score >= 60, +5 change
    WATCH = "WATCH"  # Track - score >= 50, emerging


@dataclass
class AgentLog:
    """Represents a single agent action log entry."""
    timestamp: str
    agent_name: str
    action: str
    details: Dict[str, Any]
    status: str
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Alert:
    """Represents an opportunity alert."""
    alert_id: str
    timestamp: str
    priority: str
    zip_code: str
    city: str
    state: str
    metro: str
    current_score: float
    previous_score: Optional[float]
    score_change: float
    trigger_reason: str
    current_value: float
    appreciation_pct: float
    days_to_pending: float
    recommended_action: str
    is_new_opportunity: bool = False
    acknowledged: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AgentState:
    """Tracks the state of all agents."""
    last_data_refresh: Optional[str] = None
    last_scoring_run: Optional[str] = None
    last_detection_run: Optional[str] = None
    last_alert_generation: Optional[str] = None
    last_report_generation: Optional[str] = None
    data_version: str = "v1"
    total_opportunities_detected: int = 0
    opportunities_this_week: int = 0
    opportunities_this_month: int = 0
    known_opportunity_hashes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentState':
        return cls(**data)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, log_dir: Path):
        self.name = name
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.status = AgentStatus.IDLE
        self.last_run: Optional[datetime] = None
        self.logs: List[AgentLog] = []

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main task."""
        pass

    def log_action(self, action: str, details: Dict[str, Any],
                   status: str = "success", duration: float = 0.0):
        """Log an agent action."""
        log_entry = AgentLog(
            timestamp=datetime.now().isoformat(),
            agent_name=self.name,
            action=action,
            details=details,
            status=status,
            duration_seconds=duration
        )
        self.logs.append(log_entry)
        self.logger.info(f"{action}: {details}")

    def save_logs(self):
        """Save logs to file."""
        log_file = self.log_dir / f"{self.name}_logs.json"
        existing_logs = []

        if log_file.exists():
            with open(log_file, 'r') as f:
                existing_logs = json.load(f)

        all_logs = existing_logs + [log.to_dict() for log in self.logs]

        # Keep only last 1000 logs
        all_logs = all_logs[-1000:]

        with open(log_file, 'w') as f:
            json.dump(all_logs, f, indent=2)

        self.logs = []


class DataRefreshAgent(BaseAgent):
    """
    Agent that checks for new Zillow data updates.
    Simulates monthly data refresh (typically around 16th of month).
    """

    def __init__(self, log_dir: Path):
        super().__init__("DataRefreshAgent", log_dir)
        self.refresh_day = 16  # Day of month Zillow typically updates

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if new data is available."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        current_date = context.get('current_date', datetime.now())
        state = context.get('state', AgentState())

        # Check if it's refresh day and we haven't refreshed this month
        is_refresh_day = current_date.day >= self.refresh_day
        last_refresh = None
        if state.last_data_refresh:
            last_refresh = datetime.fromisoformat(state.last_data_refresh)

        needs_refresh = False
        if last_refresh is None:
            needs_refresh = True
        elif last_refresh.month != current_date.month or last_refresh.year != current_date.year:
            if is_refresh_day:
                needs_refresh = True

        # Simulate data check
        new_data_available = needs_refresh
        new_version = f"v{current_date.strftime('%Y%m')}"

        result = {
            'new_data_available': new_data_available,
            'data_version': new_version if new_data_available else state.data_version,
            'checked_at': current_date.isoformat()
        }

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "data_check",
            {
                'new_data': new_data_available,
                'version': result['data_version'],
                'refresh_day': self.refresh_day
            },
            duration=duration
        )

        if new_data_available:
            state.last_data_refresh = current_date.isoformat()
            state.data_version = new_version

        self.status = AgentStatus.COMPLETED
        self.last_run = current_date

        return result


class ScoringAgent(BaseAgent):
    """
    Agent that runs the opportunity scoring when triggered.
    """

    def __init__(self, log_dir: Path):
        super().__init__("ScoringAgent", log_dir)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run scoring on all ZIPs."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        current_date = context.get('current_date', datetime.now())
        scores_df = context.get('scores_df')
        state = context.get('state', AgentState())

        if scores_df is None:
            self.log_action("scoring_skipped", {"reason": "no_data"})
            self.status = AgentStatus.COMPLETED
            return {'success': False, 'reason': 'no_data'}

        # Calculate statistics
        stats = {
            'total_zips': len(scores_df),
            'high_score_count': len(scores_df[scores_df['composite_score'] >= 65]),
            'very_high_count': len(scores_df[scores_df['composite_score'] >= 70]),
            'avg_score': float(scores_df['composite_score'].mean()),
            'max_score': float(scores_df['composite_score'].max()),
            'median_value': float(scores_df['current_value'].median())
        }

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "scoring_completed",
            stats,
            duration=duration
        )

        state.last_scoring_run = current_date.isoformat()

        self.status = AgentStatus.COMPLETED
        self.last_run = current_date

        return {
            'success': True,
            'stats': stats,
            'scored_at': current_date.isoformat()
        }


class OpportunityDetectionAgent(BaseAgent):
    """
    Agent that detects NEW high-scoring opportunities vs previous runs.
    """

    def __init__(self, log_dir: Path):
        super().__init__("OpportunityDetectionAgent", log_dir)
        self.score_threshold = 60
        self.high_score_threshold = 70

    def _compute_hash(self, row: pd.Series) -> str:
        """Compute a hash for a ZIP opportunity."""
        key = f"{row['region_name']}_{row['state']}_{row['composite_score']:.1f}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect new and changed opportunities."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        current_date = context.get('current_date', datetime.now())
        scores_df = context.get('scores_df')
        previous_scores_df = context.get('previous_scores_df')
        state = context.get('state', AgentState())

        if scores_df is None:
            self.status = AgentStatus.COMPLETED
            return {'new_opportunities': [], 'changed_opportunities': []}

        # Filter to high-scoring opportunities
        high_scores = scores_df[scores_df['composite_score'] >= self.score_threshold].copy()

        new_opportunities = []
        changed_opportunities = []

        for _, row in high_scores.iterrows():
            zip_hash = self._compute_hash(row)
            is_new = zip_hash not in state.known_opportunity_hashes

            # Check for score change if we have previous data
            previous_score = None
            score_change = 0

            if previous_scores_df is not None:
                prev_row = previous_scores_df[
                    previous_scores_df['region_name'] == row['region_name']
                ]
                if len(prev_row) > 0:
                    previous_score = prev_row.iloc[0]['composite_score']
                    score_change = row['composite_score'] - previous_score

            opportunity = {
                'zip_code': row['region_name'],
                'city': row.get('city', ''),
                'state': row.get('state', ''),
                'metro': row.get('metro', ''),
                'current_score': float(row['composite_score']),
                'previous_score': float(previous_score) if previous_score else None,
                'score_change': float(score_change),
                'current_value': float(row['current_value']),
                'appreciation_pct': float(row.get('appreciation_pct', 0)),
                'days_to_pending': float(row.get('days_to_pending', 0)) if pd.notna(row.get('days_to_pending')) else None,
                'is_new': is_new,
                'detected_at': current_date.isoformat()
            }

            if is_new:
                new_opportunities.append(opportunity)
                state.known_opportunity_hashes.append(zip_hash)
            elif abs(score_change) >= 3:  # Significant change
                changed_opportunities.append(opportunity)

        # Update state
        state.total_opportunities_detected += len(new_opportunities)

        # Calculate weekly/monthly counts
        week_ago = current_date - timedelta(days=7)
        month_ago = current_date - timedelta(days=30)

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "detection_completed",
            {
                'new_count': len(new_opportunities),
                'changed_count': len(changed_opportunities),
                'total_high_score': len(high_scores)
            },
            duration=duration
        )

        state.last_detection_run = current_date.isoformat()
        self.status = AgentStatus.COMPLETED
        self.last_run = current_date

        return {
            'new_opportunities': new_opportunities,
            'changed_opportunities': changed_opportunities,
            'detection_time': current_date.isoformat()
        }


class PropertyAnalysisAgent(BaseAgent):
    """
    Agent that generates detailed analysis reports for specific properties.
    """

    def __init__(self, log_dir: Path):
        super().__init__("PropertyAnalysisAgent", log_dir)

    def analyze_property(self, zip_data: Dict, historical_df: Optional[pd.DataFrame] = None) -> Dict:
        """Generate detailed analysis for a ZIP code."""

        # Calculate momentum score based on available data
        momentum_score = self._calculate_momentum(zip_data, historical_df)
        risk_assessment = self._assess_risk(zip_data)
        recommendation = self._generate_recommendation(zip_data, momentum_score, risk_assessment)

        analysis = {
            'zip_code': zip_data.get('zip_code'),
            'analysis_timestamp': datetime.now().isoformat(),
            'current_metrics': {
                'composite_score': zip_data.get('current_score'),
                'home_value': zip_data.get('current_value'),
                'appreciation_12mo': zip_data.get('appreciation_pct'),
                'days_to_pending': zip_data.get('days_to_pending'),
            },
            'momentum_analysis': momentum_score,
            'risk_assessment': risk_assessment,
            'recommendation': recommendation,
            'comparable_markets': self._find_comparables(zip_data),
        }

        return analysis

    def _calculate_momentum(self, zip_data: Dict, historical_df: Optional[pd.DataFrame]) -> Dict:
        """Calculate market momentum indicators."""
        appreciation = zip_data.get('appreciation_pct', 0)

        # Momentum classification
        if appreciation > 8:
            momentum_class = "Strong Upward"
            momentum_score = 90
        elif appreciation > 5:
            momentum_class = "Moderate Upward"
            momentum_score = 75
        elif appreciation > 2:
            momentum_class = "Slight Upward"
            momentum_score = 60
        elif appreciation > -2:
            momentum_class = "Stable"
            momentum_score = 50
        else:
            momentum_class = "Declining"
            momentum_score = 30

        return {
            'momentum_score': momentum_score,
            'momentum_class': momentum_class,
            'appreciation_trend': appreciation,
            'velocity_indicator': 'Fast' if zip_data.get('days_to_pending', 60) < 40 else 'Normal'
        }

    def _assess_risk(self, zip_data: Dict) -> Dict:
        """Assess investment risk."""
        risks = []
        risk_score = 50  # Base risk

        # Price risk
        value = zip_data.get('current_value', 0)
        if value > 400000:
            risks.append("High entry cost")
            risk_score += 15
        elif value < 100000:
            risks.append("Very low value - verify market stability")
            risk_score += 10

        # Market speed risk
        dtp = zip_data.get('days_to_pending', 60)
        if dtp and dtp > 60:
            risks.append("Slow market - longer holding period likely")
            risk_score += 10

        # Appreciation risk
        appr = zip_data.get('appreciation_pct', 0)
        if appr > 10:
            risks.append("Rapid appreciation - potential overheating")
            risk_score += 5
        elif appr < 0:
            risks.append("Negative appreciation - declining market")
            risk_score += 20

        risk_level = "Low" if risk_score < 50 else "Medium" if risk_score < 70 else "High"

        return {
            'risk_score': min(100, risk_score),
            'risk_level': risk_level,
            'risk_factors': risks,
            'mitigation': self._get_mitigation_strategies(risks)
        }

    def _get_mitigation_strategies(self, risks: List[str]) -> List[str]:
        """Get risk mitigation strategies."""
        strategies = []
        if "High entry cost" in risks:
            strategies.append("Consider partnering or financing options")
        if "Slow market" in risks:
            strategies.append("Build in longer holding period to projections")
        if "Rapid appreciation" in risks:
            strategies.append("Lock in purchase quickly, verify comps")
        if "Negative appreciation" in risks:
            strategies.append("Focus on deep value-add opportunities only")
        return strategies

    def _generate_recommendation(self, zip_data: Dict, momentum: Dict, risk: Dict) -> Dict:
        """Generate investment recommendation."""
        score = zip_data.get('current_score', 0)
        momentum_score = momentum.get('momentum_score', 50)
        risk_score = risk.get('risk_score', 50)

        # Calculate target price (10-20% below current value for flip margin)
        current_value = zip_data.get('current_value', 0)
        discount_pct = 0.15 if score >= 70 else 0.12 if score >= 60 else 0.10
        target_price = current_value * (1 - discount_pct)

        # Action recommendation
        if score >= 70 and momentum_score >= 70 and risk_score < 60:
            action = "STRONG BUY"
            confidence = "High"
        elif score >= 65 and momentum_score >= 60:
            action = "BUY"
            confidence = "Medium-High"
        elif score >= 60:
            action = "CONSIDER"
            confidence = "Medium"
        else:
            action = "WATCH"
            confidence = "Low"

        return {
            'action': action,
            'confidence': confidence,
            'target_purchase_price': round(target_price, 0),
            'target_discount_pct': discount_pct * 100,
            'estimated_arv': round(current_value * 1.15, 0),  # After repair value
            'estimated_profit_margin': f"{15 + discount_pct * 100:.0f}%",
            'holding_period_estimate': f"{zip_data.get('days_to_pending', 60):.0f} days" if zip_data.get('days_to_pending') else "60-90 days",
            'rationale': self._build_rationale(zip_data, momentum, risk)
        }

    def _build_rationale(self, zip_data: Dict, momentum: Dict, risk: Dict) -> str:
        """Build recommendation rationale."""
        parts = []
        if zip_data.get('current_score', 0) >= 70:
            parts.append("Strong composite score indicates high flip potential")
        if momentum.get('momentum_score', 0) >= 70:
            parts.append("Positive market momentum supports appreciation")
        if zip_data.get('days_to_pending', 100) < 45:
            parts.append("Fast market velocity reduces holding risk")
        if risk.get('risk_score', 100) < 50:
            parts.append("Lower than average risk profile")

        return ". ".join(parts) if parts else "Standard opportunity - proceed with normal due diligence"

    def _find_comparables(self, zip_data: Dict) -> List[Dict]:
        """Find comparable markets (simplified)."""
        # In production, this would query the database
        return [
            {"type": "Same Metro", "note": "Compare with other ZIPs in metro for validation"},
            {"type": "Price Range", "note": f"Look for similar ${zip_data.get('current_value', 0):,.0f} properties"},
        ]

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze properties from detected opportunities."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        opportunities = context.get('opportunities', [])
        analyses = []

        for opp in opportunities[:10]:  # Limit to top 10
            analysis = self.analyze_property(opp)
            analyses.append(analysis)

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "analysis_completed",
            {'properties_analyzed': len(analyses)},
            duration=duration
        )

        self.status = AgentStatus.COMPLETED
        return {'analyses': analyses}


class AlertAgent(BaseAgent):
    """
    Agent that generates and manages alerts based on detected opportunities.
    """

    def __init__(self, log_dir: Path):
        super().__init__("AlertAgent", log_dir)
        self.alerts_file = log_dir / "alerts.json"
        self.hot_threshold = 70
        self.warm_threshold = 60
        self.change_threshold_hot = 10
        self.change_threshold_warm = 5

    def _classify_priority(self, opportunity: Dict) -> AlertPriority:
        """Classify alert priority."""
        score = opportunity.get('current_score', 0)
        change = opportunity.get('score_change', 0)
        is_new = opportunity.get('is_new', False)

        if score >= self.hot_threshold or (is_new and score >= 65) or change >= self.change_threshold_hot:
            return AlertPriority.HOT
        elif score >= self.warm_threshold or change >= self.change_threshold_warm:
            return AlertPriority.WARM
        else:
            return AlertPriority.WATCH

    def _determine_trigger_reason(self, opportunity: Dict, priority: AlertPriority) -> str:
        """Determine why the alert was triggered."""
        reasons = []
        score = opportunity.get('current_score', 0)
        change = opportunity.get('score_change', 0)
        is_new = opportunity.get('is_new', False)

        if is_new:
            reasons.append("New high-scoring opportunity detected")
        if score >= 70:
            reasons.append(f"Score {score:.1f} exceeds HOT threshold (70)")
        elif score >= 60:
            reasons.append(f"Score {score:.1f} exceeds WARM threshold (60)")
        if change >= 10:
            reasons.append(f"Score increased by {change:.1f} points")
        elif change >= 5:
            reasons.append(f"Score increased by {change:.1f} points")

        return "; ".join(reasons) if reasons else "Score meets monitoring threshold"

    def _generate_recommended_action(self, opportunity: Dict, priority: AlertPriority) -> str:
        """Generate recommended action based on priority."""
        if priority == AlertPriority.HOT:
            return "Immediate review recommended. Consider property search in this ZIP."
        elif priority == AlertPriority.WARM:
            return "Add to watchlist. Monitor for further score improvements."
        else:
            return "Track passively. Review if score increases."

    def generate_alert(self, opportunity: Dict, current_date: datetime) -> Alert:
        """Generate an alert from an opportunity."""
        priority = self._classify_priority(opportunity)

        alert = Alert(
            alert_id=f"ALT-{current_date.strftime('%Y%m%d')}-{opportunity['zip_code']}",
            timestamp=current_date.isoformat(),
            priority=priority.value,
            zip_code=opportunity.get('zip_code', ''),
            city=opportunity.get('city', ''),
            state=opportunity.get('state', ''),
            metro=opportunity.get('metro', ''),
            current_score=opportunity.get('current_score', 0),
            previous_score=opportunity.get('previous_score'),
            score_change=opportunity.get('score_change', 0),
            trigger_reason=self._determine_trigger_reason(opportunity, priority),
            current_value=opportunity.get('current_value', 0),
            appreciation_pct=opportunity.get('appreciation_pct', 0),
            days_to_pending=opportunity.get('days_to_pending', 0) or 0,
            recommended_action=self._generate_recommended_action(opportunity, priority),
            is_new_opportunity=opportunity.get('is_new', False)
        )

        return alert

    def save_alerts(self, alerts: List[Alert]):
        """Save alerts to file."""
        existing_alerts = []
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                existing_alerts = json.load(f)

        all_alerts = existing_alerts + [a.to_dict() for a in alerts]

        # Keep last 500 alerts
        all_alerts = all_alerts[-500:]

        with open(self.alerts_file, 'w') as f:
            json.dump(all_alerts, f, indent=2)

    def load_alerts(self) -> List[Dict]:
        """Load existing alerts."""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        return []

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alerts for detected opportunities."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        current_date = context.get('current_date', datetime.now())
        new_opportunities = context.get('new_opportunities', [])
        changed_opportunities = context.get('changed_opportunities', [])
        state = context.get('state', AgentState())

        all_opportunities = new_opportunities + changed_opportunities
        alerts = []

        for opp in all_opportunities:
            alert = self.generate_alert(opp, current_date)
            alerts.append(alert)

        # Save alerts
        if alerts:
            self.save_alerts(alerts)

        # Count by priority
        priority_counts = {
            'HOT': len([a for a in alerts if a.priority == 'HOT']),
            'WARM': len([a for a in alerts if a.priority == 'WARM']),
            'WATCH': len([a for a in alerts if a.priority == 'WATCH'])
        }

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "alerts_generated",
            {
                'total_alerts': len(alerts),
                'by_priority': priority_counts
            },
            duration=duration
        )

        state.last_alert_generation = current_date.isoformat()
        self.status = AgentStatus.COMPLETED
        self.last_run = current_date

        return {
            'alerts': [a.to_dict() for a in alerts],
            'priority_counts': priority_counts,
            'generated_at': current_date.isoformat()
        }


class ReportGeneratorAgent(BaseAgent):
    """
    Agent that generates periodic summary reports.
    """

    def __init__(self, log_dir: Path):
        super().__init__("ReportGeneratorAgent", log_dir)
        self.reports_dir = log_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def generate_weekly_report(self, context: Dict[str, Any]) -> Dict:
        """Generate weekly summary report."""
        current_date = context.get('current_date', datetime.now())
        scores_df = context.get('scores_df')
        alerts = context.get('alerts', [])
        state = context.get('state', AgentState())

        week_start = current_date - timedelta(days=7)

        # Filter recent alerts
        recent_alerts = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp']) >= week_start
        ]

        report = {
            'report_type': 'weekly',
            'generated_at': current_date.isoformat(),
            'period': {
                'start': week_start.isoformat(),
                'end': current_date.isoformat()
            },
            'summary': {
                'total_opportunities_monitored': len(scores_df) if scores_df is not None else 0,
                'new_opportunities_this_week': len([a for a in recent_alerts if a.get('is_new_opportunity')]),
                'total_alerts': len(recent_alerts),
                'hot_alerts': len([a for a in recent_alerts if a['priority'] == 'HOT']),
                'warm_alerts': len([a for a in recent_alerts if a['priority'] == 'WARM']),
            },
            'top_opportunities': [],
            'market_highlights': [],
            'recommendations': []
        }

        # Add top opportunities
        if scores_df is not None:
            top_5 = scores_df.head(5)
            report['top_opportunities'] = [
                {
                    'zip': row['region_name'],
                    'city': row.get('city', ''),
                    'state': row.get('state', ''),
                    'score': round(row['composite_score'], 1),
                    'value': round(row['current_value'], 0)
                }
                for _, row in top_5.iterrows()
            ]

        # Market highlights
        if scores_df is not None:
            report['market_highlights'] = [
                f"Average opportunity score: {scores_df['composite_score'].mean():.1f}",
                f"Highest score: {scores_df['composite_score'].max():.1f}",
                f"Median home value: ${scores_df['current_value'].median():,.0f}"
            ]

        # Save report
        report_file = self.reports_dir / f"weekly_{current_date.strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        return report

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate reports."""
        self.status = AgentStatus.RUNNING
        start_time = datetime.now()

        current_date = context.get('current_date', datetime.now())
        state = context.get('state', AgentState())

        # Check if it's time for weekly report (every Sunday)
        is_weekly = current_date.weekday() == 6

        reports_generated = []

        if is_weekly:
            report = self.generate_weekly_report(context)
            reports_generated.append('weekly')

        duration = (datetime.now() - start_time).total_seconds()
        self.log_action(
            "reports_generated",
            {'reports': reports_generated},
            duration=duration
        )

        state.last_report_generation = current_date.isoformat()
        self.status = AgentStatus.COMPLETED
        self.last_run = current_date

        return {
            'reports_generated': reports_generated,
            'generated_at': current_date.isoformat()
        }


class AgentOrchestrator:
    """
    Coordinates all agents and manages the workflow.
    """

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = log_dir / "agent_state.json"
        self.state = self._load_state()

        # Initialize agents
        self.data_refresh_agent = DataRefreshAgent(log_dir)
        self.scoring_agent = ScoringAgent(log_dir)
        self.detection_agent = OpportunityDetectionAgent(log_dir)
        self.property_agent = PropertyAnalysisAgent(log_dir)
        self.alert_agent = AlertAgent(log_dir)
        self.report_agent = ReportGeneratorAgent(log_dir)

        self.agents = [
            self.data_refresh_agent,
            self.scoring_agent,
            self.detection_agent,
            self.property_agent,
            self.alert_agent,
            self.report_agent
        ]

    def _load_state(self) -> AgentState:
        """Load agent state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return AgentState.from_dict(data)
        return AgentState()

    def _save_state(self):
        """Save agent state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def run_daily_check(
        self,
        current_date: datetime,
        scores_df: Optional[pd.DataFrame] = None,
        previous_scores_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Run the daily agent workflow.
        """
        results = {
            'run_date': current_date.isoformat(),
            'agents': {}
        }

        context = {
            'current_date': current_date,
            'state': self.state,
            'scores_df': scores_df,
            'previous_scores_df': previous_scores_df
        }

        # 1. Check for data refresh
        data_result = self.data_refresh_agent.run(context)
        results['agents']['DataRefreshAgent'] = data_result

        # 2. Run scoring
        scoring_result = self.scoring_agent.run(context)
        results['agents']['ScoringAgent'] = scoring_result

        # 3. Detect opportunities
        detection_result = self.detection_agent.run(context)
        results['agents']['OpportunityDetectionAgent'] = detection_result

        # 4. Analyze top opportunities
        context['opportunities'] = (
            detection_result.get('new_opportunities', []) +
            detection_result.get('changed_opportunities', [])
        )
        analysis_result = self.property_agent.run(context)
        results['agents']['PropertyAnalysisAgent'] = analysis_result

        # 5. Generate alerts
        context['new_opportunities'] = detection_result.get('new_opportunities', [])
        context['changed_opportunities'] = detection_result.get('changed_opportunities', [])
        alert_result = self.alert_agent.run(context)
        results['agents']['AlertAgent'] = alert_result

        # 6. Generate reports (if scheduled)
        context['alerts'] = self.alert_agent.load_alerts()
        report_result = self.report_agent.run(context)
        results['agents']['ReportGeneratorAgent'] = report_result

        # Save state and logs
        self._save_state()
        for agent in self.agents:
            agent.save_logs()

        return results

    def get_agent_status(self) -> Dict[str, Dict]:
        """Get status of all agents."""
        return {
            agent.name: {
                'status': agent.status.value,
                'last_run': agent.last_run.isoformat() if agent.last_run else None
            }
            for agent in self.agents
        }

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        alerts = self.alert_agent.load_alerts()
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)[:limit]

    def get_state(self) -> Dict:
        """Get current agent state."""
        return self.state.to_dict()
