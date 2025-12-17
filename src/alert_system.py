"""
Alert System Module

Handles alert generation, prioritization, storage, and notifications.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class AlertPriority(Enum):
    """Alert priority levels."""
    HOT = "HOT"       # Immediate action required
    WARM = "WARM"     # Monitor closely
    WATCH = "WATCH"   # Track passively
    INFO = "INFO"     # Informational only


class AlertType(Enum):
    """Types of alerts."""
    NEW_OPPORTUNITY = "new_opportunity"
    SCORE_INCREASE = "score_increase"
    SCORE_DECREASE = "score_decrease"
    MARKET_SHIFT = "market_shift"
    DATA_REFRESH = "data_refresh"
    WEEKLY_SUMMARY = "weekly_summary"


@dataclass
class AlertConfig:
    """Configuration for alert thresholds."""
    hot_score_threshold: float = 70.0
    warm_score_threshold: float = 60.0
    watch_score_threshold: float = 50.0
    score_change_hot: float = 10.0
    score_change_warm: float = 5.0
    max_alerts_per_day: int = 50
    alert_cooldown_hours: int = 24  # Don't re-alert same ZIP within this period


@dataclass
class AlertRecord:
    """Single alert record."""
    alert_id: str
    timestamp: str
    alert_type: str
    priority: str
    zip_code: str
    city: str
    state: str
    metro: str
    title: str
    message: str
    current_score: float
    previous_score: Optional[float]
    score_change: float
    current_value: float
    details: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'AlertRecord':
        return cls(**data)


class AlertTemplates:
    """Alert message templates."""

    @staticmethod
    def new_opportunity(zip_code: str, city: str, state: str, score: float, value: float) -> Dict[str, str]:
        return {
            'title': f"New High-Score Opportunity: {zip_code}",
            'message': f"ZIP {zip_code} ({city}, {state}) has been identified as a new flip opportunity "
                      f"with a composite score of {score:.1f}. Current median value: ${value:,.0f}."
        }

    @staticmethod
    def score_increase(zip_code: str, city: str, old_score: float, new_score: float, change: float) -> Dict[str, str]:
        return {
            'title': f"Score Surge: {zip_code} (+{change:.1f})",
            'message': f"ZIP {zip_code} ({city}) score increased from {old_score:.1f} to {new_score:.1f} "
                      f"(+{change:.1f} points). This may indicate emerging opportunity."
        }

    @staticmethod
    def score_decrease(zip_code: str, city: str, old_score: float, new_score: float, change: float) -> Dict[str, str]:
        return {
            'title': f"Score Drop: {zip_code} ({change:.1f})",
            'message': f"ZIP {zip_code} ({city}) score decreased from {old_score:.1f} to {new_score:.1f} "
                      f"({change:.1f} points). Consider reviewing if on watchlist."
        }

    @staticmethod
    def market_shift(metro: str, direction: str, magnitude: float) -> Dict[str, str]:
        return {
            'title': f"Market Shift: {metro}",
            'message': f"Significant {direction} market shift detected in {metro}. "
                      f"Average scores changed by {magnitude:.1f} points."
        }

    @staticmethod
    def data_refresh(version: str, new_opportunities: int) -> Dict[str, str]:
        return {
            'title': f"Data Refresh: {version}",
            'message': f"New Zillow data has been processed. {new_opportunities} new opportunities identified."
        }

    @staticmethod
    def weekly_summary(period: str, hot_count: int, total_count: int) -> Dict[str, str]:
        return {
            'title': f"Weekly Summary: {period}",
            'message': f"Weekly alert summary: {hot_count} HOT alerts, {total_count} total alerts. "
                      f"Review recommended for all HOT priority items."
        }


class NotificationFormatter:
    """Format alerts for different channels."""

    @staticmethod
    def format_email(alert: AlertRecord) -> Dict[str, str]:
        """Format alert for email notification."""
        priority_emoji = {"HOT": "🔥", "WARM": "🌡️", "WATCH": "👀", "INFO": "ℹ️"}

        subject = f"[{alert.priority}] {alert.title}"

        body = f"""
{priority_emoji.get(alert.priority, '')} {alert.priority} ALERT

{alert.message}

Details:
- ZIP Code: {alert.zip_code}
- Location: {alert.city}, {alert.state}
- Metro: {alert.metro}
- Current Score: {alert.current_score:.1f}
- Home Value: ${alert.current_value:,.0f}
{f'- Score Change: {alert.score_change:+.1f}' if alert.score_change else ''}

Generated: {alert.timestamp}

---
Flip Opportunity Alert System
        """

        return {
            'subject': subject,
            'body': body.strip()
        }

    @staticmethod
    def format_sms(alert: AlertRecord) -> str:
        """Format alert for SMS notification."""
        priority_prefix = {"HOT": "🔥HOT", "WARM": "WARM", "WATCH": "WATCH", "INFO": "INFO"}

        return (
            f"[{priority_prefix.get(alert.priority, 'ALERT')}] "
            f"{alert.zip_code} ({alert.city}, {alert.state}) "
            f"Score: {alert.current_score:.1f} "
            f"Value: ${alert.current_value/1000:.0f}K"
        )[:160]  # SMS limit

    @staticmethod
    def format_slack(alert: AlertRecord) -> Dict:
        """Format alert for Slack notification."""
        color_map = {"HOT": "#FF0000", "WARM": "#FFA500", "WATCH": "#FFFF00", "INFO": "#0000FF"}

        return {
            "attachments": [{
                "color": color_map.get(alert.priority, "#808080"),
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "ZIP", "value": alert.zip_code, "short": True},
                    {"title": "Score", "value": f"{alert.current_score:.1f}", "short": True},
                    {"title": "Location", "value": f"{alert.city}, {alert.state}", "short": True},
                    {"title": "Value", "value": f"${alert.current_value:,.0f}", "short": True},
                ],
                "footer": "Flip Opportunity Alert",
                "ts": datetime.fromisoformat(alert.timestamp).timestamp()
            }]
        }


class AlertManager:
    """
    Manages alert lifecycle: generation, storage, and retrieval.
    """

    def __init__(self, storage_dir: Path, config: Optional[AlertConfig] = None):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.storage_dir / "alerts.json"
        self.config = config or AlertConfig()
        self.templates = AlertTemplates()
        self.formatter = NotificationFormatter()

    def _load_alerts(self) -> List[Dict]:
        """Load alerts from storage."""
        if self.alerts_file.exists():
            with open(self.alerts_file, 'r') as f:
                return json.load(f)
        return []

    def _save_alerts(self, alerts: List[Dict]):
        """Save alerts to storage."""
        # Keep last 1000 alerts
        alerts = alerts[-1000:]
        with open(self.alerts_file, 'w') as f:
            json.dump(alerts, f, indent=2)

    def _generate_alert_id(self, alert_type: str, zip_code: str, timestamp: datetime) -> str:
        """Generate unique alert ID."""
        return f"ALT-{timestamp.strftime('%Y%m%d%H%M%S')}-{alert_type[:3].upper()}-{zip_code}"

    def _check_cooldown(self, zip_code: str, alert_type: str) -> bool:
        """Check if ZIP is in cooldown period."""
        alerts = self._load_alerts()
        cutoff = datetime.now() - timedelta(hours=self.config.alert_cooldown_hours)

        for alert in reversed(alerts):
            if alert['zip_code'] == zip_code and alert['alert_type'] == alert_type:
                alert_time = datetime.fromisoformat(alert['timestamp'])
                if alert_time > cutoff:
                    return True  # In cooldown
        return False

    def classify_priority(self, score: float, score_change: float, is_new: bool) -> AlertPriority:
        """Classify alert priority based on thresholds."""
        if score >= self.config.hot_score_threshold:
            return AlertPriority.HOT
        if is_new and score >= self.config.warm_score_threshold:
            return AlertPriority.HOT
        if score_change >= self.config.score_change_hot:
            return AlertPriority.HOT
        if score >= self.config.warm_score_threshold:
            return AlertPriority.WARM
        if score_change >= self.config.score_change_warm:
            return AlertPriority.WARM
        if score >= self.config.watch_score_threshold:
            return AlertPriority.WATCH
        return AlertPriority.INFO

    def create_alert(
        self,
        alert_type: AlertType,
        zip_code: str,
        city: str,
        state: str,
        metro: str,
        current_score: float,
        current_value: float,
        previous_score: Optional[float] = None,
        additional_details: Optional[Dict] = None,
        force: bool = False
    ) -> Optional[AlertRecord]:
        """Create a new alert."""
        # Check cooldown unless forced
        if not force and self._check_cooldown(zip_code, alert_type.value):
            return None

        timestamp = datetime.now()
        score_change = (current_score - previous_score) if previous_score else 0
        is_new = alert_type == AlertType.NEW_OPPORTUNITY

        priority = self.classify_priority(current_score, score_change, is_new)

        # Generate title and message
        if alert_type == AlertType.NEW_OPPORTUNITY:
            template = self.templates.new_opportunity(zip_code, city, state, current_score, current_value)
        elif alert_type == AlertType.SCORE_INCREASE:
            template = self.templates.score_increase(zip_code, city, previous_score or 0, current_score, score_change)
        elif alert_type == AlertType.SCORE_DECREASE:
            template = self.templates.score_decrease(zip_code, city, previous_score or 0, current_score, score_change)
        else:
            template = {'title': f"Alert: {zip_code}", 'message': f"Alert for ZIP {zip_code}"}

        alert = AlertRecord(
            alert_id=self._generate_alert_id(alert_type.value, zip_code, timestamp),
            timestamp=timestamp.isoformat(),
            alert_type=alert_type.value,
            priority=priority.value,
            zip_code=zip_code,
            city=city,
            state=state,
            metro=metro,
            title=template['title'],
            message=template['message'],
            current_score=current_score,
            previous_score=previous_score,
            score_change=score_change,
            current_value=current_value,
            details=additional_details or {}
        )

        # Save alert
        alerts = self._load_alerts()
        alerts.append(alert.to_dict())
        self._save_alerts(alerts)

        return alert

    def get_alerts(
        self,
        limit: int = 50,
        priority: Optional[str] = None,
        alert_type: Optional[str] = None,
        since: Optional[datetime] = None,
        zip_code: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[AlertRecord]:
        """Get alerts with optional filters."""
        alerts = self._load_alerts()

        # Apply filters
        filtered = []
        for alert_dict in alerts:
            if priority and alert_dict['priority'] != priority:
                continue
            if alert_type and alert_dict['alert_type'] != alert_type:
                continue
            if since:
                alert_time = datetime.fromisoformat(alert_dict['timestamp'])
                if alert_time < since:
                    continue
            if zip_code and alert_dict['zip_code'] != zip_code:
                continue
            if acknowledged is not None and alert_dict['acknowledged'] != acknowledged:
                continue
            filtered.append(AlertRecord.from_dict(alert_dict))

        # Sort by timestamp descending and limit
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered[:limit]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """Mark an alert as acknowledged."""
        alerts = self._load_alerts()

        for alert in alerts:
            if alert['alert_id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now().isoformat()
                alert['acknowledged_by'] = acknowledged_by
                self._save_alerts(alerts)
                return True
        return False

    def get_alert_statistics(self, days: int = 7) -> Dict:
        """Get alert statistics for the specified period."""
        since = datetime.now() - timedelta(days=days)
        alerts = self.get_alerts(limit=1000, since=since)

        stats = {
            'total_alerts': len(alerts),
            'by_priority': {
                'HOT': len([a for a in alerts if a.priority == 'HOT']),
                'WARM': len([a for a in alerts if a.priority == 'WARM']),
                'WATCH': len([a for a in alerts if a.priority == 'WATCH']),
                'INFO': len([a for a in alerts if a.priority == 'INFO']),
            },
            'by_type': {
                'new_opportunity': len([a for a in alerts if a.alert_type == 'new_opportunity']),
                'score_increase': len([a for a in alerts if a.alert_type == 'score_increase']),
                'score_decrease': len([a for a in alerts if a.alert_type == 'score_decrease']),
            },
            'acknowledged': len([a for a in alerts if a.acknowledged]),
            'unacknowledged': len([a for a in alerts if not a.acknowledged]),
            'unique_zips': len(set(a.zip_code for a in alerts)),
            'period_days': days
        }

        return stats

    def get_notification(self, alert: AlertRecord, channel: str = "email") -> Any:
        """Get formatted notification for a specific channel."""
        if channel == "email":
            return self.formatter.format_email(alert)
        elif channel == "sms":
            return self.formatter.format_sms(alert)
        elif channel == "slack":
            return self.formatter.format_slack(alert)
        else:
            raise ValueError(f"Unknown channel: {channel}")

    def bulk_create_alerts(
        self,
        opportunities: List[Dict],
        alert_type: AlertType = AlertType.NEW_OPPORTUNITY
    ) -> List[AlertRecord]:
        """Create alerts for multiple opportunities."""
        created_alerts = []

        for opp in opportunities:
            alert = self.create_alert(
                alert_type=alert_type,
                zip_code=opp.get('zip_code', ''),
                city=opp.get('city', ''),
                state=opp.get('state', ''),
                metro=opp.get('metro', ''),
                current_score=opp.get('current_score', 0),
                current_value=opp.get('current_value', 0),
                previous_score=opp.get('previous_score'),
                additional_details=opp
            )
            if alert:
                created_alerts.append(alert)

        return created_alerts

    def clear_old_alerts(self, days: int = 90) -> int:
        """Remove alerts older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        alerts = self._load_alerts()

        original_count = len(alerts)
        alerts = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp']) > cutoff
        ]

        self._save_alerts(alerts)
        return original_count - len(alerts)
