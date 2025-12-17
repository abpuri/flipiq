"""
Property Analyzer Module

Deep-dive analysis for specific ZIP codes, including:
- Historical trend analysis
- Market momentum scoring
- Risk assessment
- Investment recommendations
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .data_loader import get_date_columns, load_all_datasets


@dataclass
class TrendAnalysis:
    """Historical trend analysis results."""
    current_value: float
    value_1yr_ago: float
    value_2yr_ago: Optional[float]
    yoy_change_pct: float
    two_year_change_pct: Optional[float]
    trend_direction: str  # "up", "down", "stable"
    trend_strength: str   # "strong", "moderate", "weak"
    volatility_score: float  # 0-100
    seasonality_detected: bool
    peak_month: Optional[int]
    trough_month: Optional[int]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MomentumScore:
    """Market momentum analysis."""
    momentum_score: float  # 0-100
    momentum_grade: str    # A, B, C, D, F
    velocity_score: float
    appreciation_score: float
    demand_score: float
    trend_consistency: float
    momentum_factors: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskAssessment:
    """Investment risk assessment."""
    overall_risk_score: float  # 0-100, higher = more risk
    risk_grade: str            # Low, Medium, High, Very High
    market_risk: float
    price_risk: float
    liquidity_risk: float
    timing_risk: float
    risk_factors: List[str]
    mitigations: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class InvestmentRecommendation:
    """Investment recommendation."""
    action: str             # STRONG BUY, BUY, HOLD, AVOID
    confidence: str         # High, Medium, Low
    target_purchase_price: float
    estimated_arv: float    # After repair value
    estimated_profit: float
    profit_margin_pct: float
    recommended_hold_period: str
    exit_strategy: str
    rationale: List[str]
    key_metrics: Dict[str, float]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PropertyAnalysisReport:
    """Complete property analysis report."""
    zip_code: str
    city: str
    state: str
    metro: str
    county: str
    analysis_timestamp: str
    current_score: float
    trend_analysis: TrendAnalysis
    momentum: MomentumScore
    risk: RiskAssessment
    recommendation: InvestmentRecommendation
    market_context: Dict[str, any]
    comparable_zips: List[Dict]

    def to_dict(self) -> Dict:
        result = {
            'zip_code': self.zip_code,
            'city': self.city,
            'state': self.state,
            'metro': self.metro,
            'county': self.county,
            'analysis_timestamp': self.analysis_timestamp,
            'current_score': self.current_score,
            'trend_analysis': self.trend_analysis.to_dict(),
            'momentum': self.momentum.to_dict(),
            'risk': self.risk.to_dict(),
            'recommendation': self.recommendation.to_dict(),
            'market_context': self.market_context,
            'comparable_zips': self.comparable_zips
        }
        return result


class PropertyAnalyzer:
    """
    Comprehensive property analysis engine.
    """

    def __init__(self, datasets: Optional[Dict[str, pd.DataFrame]] = None):
        self.datasets = datasets or load_all_datasets()

    def analyze_zip(
        self,
        zip_code: str,
        scores_df: Optional[pd.DataFrame] = None
    ) -> Optional[PropertyAnalysisReport]:
        """
        Generate comprehensive analysis for a ZIP code.
        """
        # Get ZIP data from ZHVI
        zhvi_df = self.datasets['zhvi_zip']
        zip_data = zhvi_df[zhvi_df['region_name'] == zip_code]

        if len(zip_data) == 0:
            return None

        zip_row = zip_data.iloc[0]
        date_cols = get_date_columns(zhvi_df)

        # Get score data if available
        score_row = None
        if scores_df is not None:
            score_data = scores_df[scores_df['region_name'] == zip_code]
            if len(score_data) > 0:
                score_row = score_data.iloc[0]

        # Perform analyses
        trend = self._analyze_trends(zip_row, date_cols)
        momentum = self._calculate_momentum(zip_row, score_row, date_cols)
        risk = self._assess_risk(zip_row, score_row, trend, momentum)
        recommendation = self._generate_recommendation(
            zip_row, score_row, trend, momentum, risk
        )
        market_context = self._get_market_context(zip_row, score_row)
        comparables = self._find_comparables(zip_row, scores_df)

        report = PropertyAnalysisReport(
            zip_code=zip_code,
            city=str(zip_row.get('city', '')),
            state=str(zip_row.get('state', '')),
            metro=str(zip_row.get('metro', '')),
            county=str(zip_row.get('county_name', '')),
            analysis_timestamp=datetime.now().isoformat(),
            current_score=float(score_row['composite_score']) if score_row is not None else 0,
            trend_analysis=trend,
            momentum=momentum,
            risk=risk,
            recommendation=recommendation,
            market_context=market_context,
            comparable_zips=comparables
        )

        return report

    def _analyze_trends(
        self,
        zip_row: pd.Series,
        date_cols: List[str]
    ) -> TrendAnalysis:
        """Analyze historical price trends."""
        values = zip_row[date_cols].values.astype(float)
        dates = pd.to_datetime(date_cols)

        current_value = values[-1] if not np.isnan(values[-1]) else 0

        # 1 year ago (12 months)
        value_1yr = values[-13] if len(values) >= 13 and not np.isnan(values[-13]) else current_value
        yoy_change = ((current_value - value_1yr) / value_1yr * 100) if value_1yr > 0 else 0

        # 2 years ago (24 months)
        value_2yr = None
        two_year_change = None
        if len(values) >= 25:
            value_2yr = values[-25] if not np.isnan(values[-25]) else None
            if value_2yr:
                two_year_change = ((current_value - value_2yr) / value_2yr * 100)

        # Trend direction and strength
        if yoy_change > 5:
            trend_direction = "up"
            trend_strength = "strong" if yoy_change > 10 else "moderate"
        elif yoy_change < -5:
            trend_direction = "down"
            trend_strength = "strong" if yoy_change < -10 else "moderate"
        else:
            trend_direction = "stable"
            trend_strength = "weak"

        # Calculate volatility (std dev of monthly changes)
        monthly_changes = np.diff(values) / values[:-1] * 100
        monthly_changes = monthly_changes[~np.isnan(monthly_changes)]
        volatility = np.std(monthly_changes) if len(monthly_changes) > 0 else 0
        volatility_score = min(100, volatility * 10)  # Scale to 0-100

        # Check for seasonality (simplified)
        if len(values) >= 24:
            monthly_avgs = {}
            for i, date in enumerate(dates):
                month = date.month
                if month not in monthly_avgs:
                    monthly_avgs[month] = []
                if not np.isnan(values[i]):
                    monthly_avgs[month].append(values[i])

            avg_by_month = {m: np.mean(v) for m, v in monthly_avgs.items() if v}
            if avg_by_month:
                peak_month = max(avg_by_month, key=avg_by_month.get)
                trough_month = min(avg_by_month, key=avg_by_month.get)
                seasonality = max(avg_by_month.values()) / min(avg_by_month.values()) > 1.05
            else:
                peak_month = None
                trough_month = None
                seasonality = False
        else:
            peak_month = None
            trough_month = None
            seasonality = False

        return TrendAnalysis(
            current_value=current_value,
            value_1yr_ago=value_1yr,
            value_2yr_ago=value_2yr,
            yoy_change_pct=round(yoy_change, 2),
            two_year_change_pct=round(two_year_change, 2) if two_year_change else None,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            volatility_score=round(volatility_score, 1),
            seasonality_detected=seasonality,
            peak_month=peak_month,
            trough_month=trough_month
        )

    def _calculate_momentum(
        self,
        zip_row: pd.Series,
        score_row: Optional[pd.Series],
        date_cols: List[str]
    ) -> MomentumScore:
        """Calculate market momentum indicators."""
        values = zip_row[date_cols].values.astype(float)

        # Calculate short-term vs long-term momentum
        if len(values) >= 6:
            short_term = (values[-1] - values[-4]) / values[-4] * 100  # 3 months
            long_term = (values[-1] - values[-7]) / values[-7] * 100   # 6 months
        else:
            short_term = 0
            long_term = 0

        # Velocity score (from scoring if available)
        velocity_score = 50
        if score_row is not None and pd.notna(score_row.get('velocity_score')):
            velocity_score = score_row['velocity_score']

        # Appreciation score
        appreciation_score = 50
        if score_row is not None and pd.notna(score_row.get('appreciation_score')):
            appreciation_score = score_row['appreciation_score']

        # Demand score (based on days to pending and price cuts)
        demand_score = 50
        if score_row is not None:
            dtp = score_row.get('days_to_pending', 60)
            pc = score_row.get('price_cut_pct', 20)
            if pd.notna(dtp) and pd.notna(pc):
                demand_score = max(0, min(100, 100 - dtp + (25 - pc) * 2))

        # Trend consistency (positive months / total months)
        if len(values) >= 12:
            monthly_changes = np.diff(values[-12:])
            positive_months = np.sum(monthly_changes > 0)
            trend_consistency = positive_months / 11 * 100
        else:
            trend_consistency = 50

        # Overall momentum score
        momentum_score = (
            velocity_score * 0.25 +
            appreciation_score * 0.30 +
            demand_score * 0.25 +
            trend_consistency * 0.20
        )

        # Grade
        if momentum_score >= 80:
            grade = "A"
        elif momentum_score >= 65:
            grade = "B"
        elif momentum_score >= 50:
            grade = "C"
        elif momentum_score >= 35:
            grade = "D"
        else:
            grade = "F"

        # Factors
        factors = []
        if short_term > long_term:
            factors.append("Accelerating appreciation")
        elif short_term < long_term * 0.5:
            factors.append("Decelerating appreciation")
        if velocity_score > 70:
            factors.append("Fast market velocity")
        if demand_score > 70:
            factors.append("Strong buyer demand")
        if trend_consistency > 70:
            factors.append("Consistent upward trend")

        return MomentumScore(
            momentum_score=round(momentum_score, 1),
            momentum_grade=grade,
            velocity_score=round(velocity_score, 1),
            appreciation_score=round(appreciation_score, 1),
            demand_score=round(demand_score, 1),
            trend_consistency=round(trend_consistency, 1),
            momentum_factors=factors
        )

    def _assess_risk(
        self,
        zip_row: pd.Series,
        score_row: Optional[pd.Series],
        trend: TrendAnalysis,
        momentum: MomentumScore
    ) -> RiskAssessment:
        """Assess investment risk."""
        risk_factors = []
        mitigations = []

        # Market risk (based on volatility and trend)
        market_risk = trend.volatility_score
        if trend.trend_direction == "down":
            market_risk += 20
            risk_factors.append("Declining market trend")
            mitigations.append("Focus on deep value properties only")

        # Price risk (based on value level)
        current_value = trend.current_value
        if current_value > 400000:
            price_risk = 70
            risk_factors.append("High entry cost limits buyer pool")
            mitigations.append("Ensure strong comps and conservative ARV")
        elif current_value > 300000:
            price_risk = 50
        elif current_value < 100000:
            price_risk = 60
            risk_factors.append("Very low value market - limited upside")
            mitigations.append("Focus on rental potential as backup")
        else:
            price_risk = 30

        # Liquidity risk (based on days to pending)
        dtp = 60
        if score_row is not None and pd.notna(score_row.get('days_to_pending')):
            dtp = score_row['days_to_pending']

        if dtp > 60:
            liquidity_risk = 70
            risk_factors.append("Slow market - extended holding period likely")
            mitigations.append("Build in longer timeline to projections")
        elif dtp > 45:
            liquidity_risk = 50
        else:
            liquidity_risk = 25

        # Timing risk (based on momentum)
        if momentum.momentum_score < 40:
            timing_risk = 70
            risk_factors.append("Weak market momentum")
            mitigations.append("Wait for momentum improvement or seek deeper discounts")
        elif momentum.momentum_score > 80:
            timing_risk = 40
            risk_factors.append("Hot market - competition risk")
            mitigations.append("Act quickly on good deals")
        else:
            timing_risk = 35

        # Overall risk score
        overall_risk = (
            market_risk * 0.25 +
            price_risk * 0.25 +
            liquidity_risk * 0.30 +
            timing_risk * 0.20
        )

        # Risk grade
        if overall_risk < 35:
            grade = "Low"
        elif overall_risk < 50:
            grade = "Medium"
        elif overall_risk < 70:
            grade = "High"
        else:
            grade = "Very High"

        return RiskAssessment(
            overall_risk_score=round(overall_risk, 1),
            risk_grade=grade,
            market_risk=round(market_risk, 1),
            price_risk=round(price_risk, 1),
            liquidity_risk=round(liquidity_risk, 1),
            timing_risk=round(timing_risk, 1),
            risk_factors=risk_factors,
            mitigations=mitigations
        )

    def _generate_recommendation(
        self,
        zip_row: pd.Series,
        score_row: Optional[pd.Series],
        trend: TrendAnalysis,
        momentum: MomentumScore,
        risk: RiskAssessment
    ) -> InvestmentRecommendation:
        """Generate investment recommendation."""
        current_value = trend.current_value
        composite_score = score_row['composite_score'] if score_row is not None else 50

        # Determine action
        score_factor = composite_score / 100
        momentum_factor = momentum.momentum_score / 100
        risk_factor = 1 - (risk.overall_risk_score / 100)

        opportunity_score = (score_factor * 0.4 + momentum_factor * 0.35 + risk_factor * 0.25) * 100

        if opportunity_score >= 70:
            action = "STRONG BUY"
            confidence = "High"
            discount_pct = 0.15
        elif opportunity_score >= 55:
            action = "BUY"
            confidence = "Medium-High"
            discount_pct = 0.12
        elif opportunity_score >= 40:
            action = "HOLD"
            confidence = "Medium"
            discount_pct = 0.10
        else:
            action = "AVOID"
            confidence = "Low"
            discount_pct = 0.20

        # Calculate financials
        target_price = current_value * (1 - discount_pct)
        estimated_arv = current_value * 1.15  # 15% ARV premium
        estimated_profit = estimated_arv - target_price - (current_value * 0.10)  # 10% rehab
        profit_margin = (estimated_profit / target_price) * 100

        # Hold period
        dtp = 60
        if score_row is not None and pd.notna(score_row.get('days_to_pending')):
            dtp = score_row['days_to_pending']
        hold_period = f"{max(30, int(dtp) + 30)}-{max(60, int(dtp) + 60)} days"

        # Exit strategy
        if profit_margin > 25:
            exit_strategy = "Retail sale to owner-occupant"
        elif profit_margin > 15:
            exit_strategy = "Wholesale to investor or retail sale"
        else:
            exit_strategy = "Wholesale or rental hold"

        # Rationale
        rationale = []
        if composite_score >= 65:
            rationale.append(f"Strong composite score of {composite_score:.1f}")
        if momentum.momentum_grade in ['A', 'B']:
            rationale.append(f"Good market momentum (Grade {momentum.momentum_grade})")
        if risk.risk_grade == "Low":
            rationale.append("Lower than average risk profile")
        if trend.trend_direction == "up" and trend.trend_strength == "strong":
            rationale.append("Strong upward price trend")
        if not rationale:
            rationale.append("Meets basic investment criteria with standard risk profile")

        return InvestmentRecommendation(
            action=action,
            confidence=confidence,
            target_purchase_price=round(target_price, 0),
            estimated_arv=round(estimated_arv, 0),
            estimated_profit=round(estimated_profit, 0),
            profit_margin_pct=round(profit_margin, 1),
            recommended_hold_period=hold_period,
            exit_strategy=exit_strategy,
            rationale=rationale,
            key_metrics={
                'opportunity_score': round(opportunity_score, 1),
                'composite_score': round(composite_score, 1),
                'momentum_score': momentum.momentum_score,
                'risk_score': risk.overall_risk_score
            }
        )

    def _get_market_context(
        self,
        zip_row: pd.Series,
        score_row: Optional[pd.Series]
    ) -> Dict:
        """Get broader market context."""
        context = {
            'metro': str(zip_row.get('metro', 'Unknown')),
            'county': str(zip_row.get('county_name', 'Unknown')),
        }

        if score_row is not None:
            context['days_to_pending'] = float(score_row.get('days_to_pending', 0)) if pd.notna(score_row.get('days_to_pending')) else None
            context['price_cut_pct'] = float(score_row.get('price_cut_pct', 0)) if pd.notna(score_row.get('price_cut_pct')) else None
            context['sale_to_list'] = float(score_row.get('sale_to_list', 0)) if pd.notna(score_row.get('sale_to_list')) else None
            context['appreciation_pct'] = float(score_row.get('appreciation_pct', 0)) if pd.notna(score_row.get('appreciation_pct')) else None

        # Get metro-level data
        metro_name = zip_row.get('metro')
        if metro_name and 'market_heat' in self.datasets:
            heat_df = self.datasets['market_heat']
            metro_heat = heat_df[heat_df['region_name'] == metro_name]
            if len(metro_heat) > 0:
                date_cols = get_date_columns(heat_df)
                if date_cols:
                    context['market_heat'] = float(metro_heat.iloc[0][date_cols[-1]])

        return context

    def _find_comparables(
        self,
        zip_row: pd.Series,
        scores_df: Optional[pd.DataFrame],
        n_comps: int = 5
    ) -> List[Dict]:
        """Find comparable ZIPs in same metro."""
        if scores_df is None:
            return []

        metro = zip_row.get('metro')
        current_zip = zip_row.get('region_name')
        current_value = zip_row[get_date_columns(self.datasets['zhvi_zip'])[-1]]

        if pd.isna(metro):
            return []

        # Find ZIPs in same metro with similar values
        metro_zips = scores_df[
            (scores_df['metro'] == metro) &
            (scores_df['region_name'] != current_zip)
        ].copy()

        if len(metro_zips) == 0:
            return []

        # Sort by value similarity
        metro_zips['value_diff'] = abs(metro_zips['current_value'] - current_value)
        metro_zips = metro_zips.sort_values('value_diff').head(n_comps)

        comps = []
        for _, row in metro_zips.iterrows():
            comps.append({
                'zip_code': row['region_name'],
                'city': row.get('city', ''),
                'current_value': round(row['current_value'], 0),
                'composite_score': round(row['composite_score'], 1),
                'appreciation_pct': round(row.get('appreciation_pct', 0), 1)
            })

        return comps

    def get_historical_data(
        self,
        zip_code: str,
        months: int = 24
    ) -> Optional[pd.DataFrame]:
        """Get historical price data for a ZIP."""
        zhvi_df = self.datasets['zhvi_zip']
        zip_data = zhvi_df[zhvi_df['region_name'] == zip_code]

        if len(zip_data) == 0:
            return None

        date_cols = get_date_columns(zhvi_df)
        recent_cols = date_cols[-months:] if len(date_cols) >= months else date_cols

        history = []
        for col in recent_cols:
            history.append({
                'date': col,
                'value': float(zip_data.iloc[0][col])
            })

        return pd.DataFrame(history)


def analyze_property(zip_code: str, scores_df: pd.DataFrame = None) -> Optional[Dict]:
    """
    Convenience function to analyze a single property.
    Returns dict representation of the analysis report.
    """
    analyzer = PropertyAnalyzer()
    report = analyzer.analyze_zip(zip_code, scores_df)
    return report.to_dict() if report else None
