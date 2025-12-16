"""
Flip Opportunity Scoring Engine

Combines multiple market indicators to identify high-potential flip opportunities.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from dataclasses import dataclass

from .data_loader import (
    load_all_datasets,
    get_date_columns,
    get_metadata_columns,
)


@dataclass
class FlipStrategy:
    """Defines weights for different flip strategies."""
    name: str
    appreciation_weight: float  # Price growth potential
    velocity_weight: float      # How fast homes sell
    distress_weight: float      # Seller motivation (price cuts)
    pricing_power_weight: float # Buyer negotiating power
    value_gap_weight: float     # Room for value-add improvement

    def __post_init__(self):
        total = (self.appreciation_weight + self.velocity_weight +
                 self.distress_weight + self.pricing_power_weight +
                 self.value_gap_weight)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# Predefined strategies
FAST_FLIP = FlipStrategy(
    name="Fast Flip",
    appreciation_weight=0.15,   # Less important - quick turnaround
    velocity_weight=0.35,       # Critical - need fast sales
    distress_weight=0.25,       # Important - find motivated sellers
    pricing_power_weight=0.20,  # Important - buy below market
    value_gap_weight=0.05       # Less important - minimal renovation
)

VALUE_ADD_FLIP = FlipStrategy(
    name="Value-Add Flip",
    appreciation_weight=0.25,   # Important - market momentum
    velocity_weight=0.15,       # Less critical - longer hold OK
    distress_weight=0.20,       # Moderate - find deals
    pricing_power_weight=0.15,  # Moderate - negotiate on condition
    value_gap_weight=0.25       # Critical - room for improvement
)

BALANCED = FlipStrategy(
    name="Balanced",
    appreciation_weight=0.20,
    velocity_weight=0.20,
    distress_weight=0.20,
    pricing_power_weight=0.20,
    value_gap_weight=0.20
)


def normalize_to_score(
    values: pd.Series,
    higher_is_better: bool = True,
    clip_percentile: float = 5.0
) -> pd.Series:
    """
    Normalize values to 0-100 scale using percentile-based normalization.

    Args:
        values: Series of values to normalize
        higher_is_better: If True, higher values get higher scores
        clip_percentile: Clip extreme values at this percentile

    Returns:
        Series with scores 0-100
    """
    # Handle missing values
    valid_mask = values.notna()
    if valid_mask.sum() == 0:
        return pd.Series(np.nan, index=values.index)

    # Clip extreme values
    lower = np.nanpercentile(values, clip_percentile)
    upper = np.nanpercentile(values, 100 - clip_percentile)
    clipped = values.clip(lower=lower, upper=upper)

    # Min-max normalization
    min_val = clipped.min()
    max_val = clipped.max()

    if max_val == min_val:
        return pd.Series(50.0, index=values.index)

    normalized = (clipped - min_val) / (max_val - min_val) * 100

    # Invert if lower is better
    if not higher_is_better:
        normalized = 100 - normalized

    return normalized


def calculate_price_appreciation(
    df_zhvi: pd.DataFrame,
    lookback_months: int = 12
) -> pd.DataFrame:
    """
    Calculate price appreciation metrics at ZIP level.

    Returns DataFrame with:
    - current_value: Latest home value
    - appreciation_pct: % change over lookback period
    - appreciation_score: Normalized 0-100 score
    """
    date_cols = get_date_columns(df_zhvi)
    meta_cols = get_metadata_columns(df_zhvi)

    if len(date_cols) < lookback_months + 1:
        lookback_months = len(date_cols) - 1

    # Get latest and lookback values
    latest_col = date_cols[-1]
    lookback_col = date_cols[-(lookback_months + 1)]

    result = df_zhvi[meta_cols].copy()
    result['current_value'] = df_zhvi[latest_col]
    result['previous_value'] = df_zhvi[lookback_col]

    # Calculate appreciation
    result['appreciation_pct'] = (
        (result['current_value'] - result['previous_value']) /
        result['previous_value'] * 100
    )

    # Normalize to score (higher appreciation = better)
    result['appreciation_score'] = normalize_to_score(
        result['appreciation_pct'],
        higher_is_better=True
    )

    return result


def get_metro_metrics(
    datasets: Dict[str, pd.DataFrame],
    lookback_months: int = 6
) -> pd.DataFrame:
    """
    Extract latest metro-level market metrics.

    Returns DataFrame indexed by metro name with:
    - days_to_pending: Average days to go under contract
    - price_cut_pct: Percentage of listings with price cuts
    - sale_to_list: Sale price / list price ratio
    - market_heat: Market heat index
    """
    result_dfs = []

    # Days to Pending (lower is better for flippers - faster sales)
    df = datasets['days_to_pending']
    date_cols = get_date_columns(df)
    recent_cols = date_cols[-lookback_months:] if len(date_cols) >= lookback_months else date_cols

    dtp = df[['region_name']].copy()
    dtp['days_to_pending'] = df[recent_cols].mean(axis=1)
    dtp = dtp.rename(columns={'region_name': 'metro'})
    result_dfs.append(dtp)

    # Price Cuts (higher = more distress = better for buyers)
    df = datasets['price_cuts']
    date_cols = get_date_columns(df)
    recent_cols = date_cols[-lookback_months:] if len(date_cols) >= lookback_months else date_cols

    pc = df[['region_name']].copy()
    pc['price_cut_pct'] = df[recent_cols].mean(axis=1) * 100  # Convert to percentage
    pc = pc.rename(columns={'region_name': 'metro'})
    result_dfs.append(pc)

    # Sale to List (lower = better for buyers)
    df = datasets['sale_to_list']
    date_cols = get_date_columns(df)
    # Sale to list is weekly, so use more recent data
    recent_cols = date_cols[-lookback_months*4:] if len(date_cols) >= lookback_months*4 else date_cols

    stl = df[['region_name']].copy()
    stl['sale_to_list'] = df[recent_cols].mean(axis=1)
    stl = stl.rename(columns={'region_name': 'metro'})
    result_dfs.append(stl)

    # Market Heat (moderate is best - too hot = expensive, too cold = slow)
    df = datasets['market_heat']
    date_cols = get_date_columns(df)
    recent_cols = date_cols[-lookback_months:] if len(date_cols) >= lookback_months else date_cols

    mh = df[['region_name']].copy()
    mh['market_heat'] = df[recent_cols].mean(axis=1)
    mh = mh.rename(columns={'region_name': 'metro'})
    result_dfs.append(mh)

    # Merge all metrics
    result = result_dfs[0]
    for df in result_dfs[1:]:
        result = result.merge(df, on='metro', how='outer')

    return result


def calculate_value_tier_gap(
    df_zhvi: pd.DataFrame,
    df_bottom_tier: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate the gap between all-home values and bottom-tier values.

    Larger gap = more room for value-add improvement.
    Uses county-level comparison since bottom tier is at county level.
    """
    date_cols_zhvi = get_date_columns(df_zhvi)
    date_cols_bt = get_date_columns(df_bottom_tier)

    # Get latest values
    latest_zhvi = date_cols_zhvi[-1]
    latest_bt = date_cols_bt[-1]

    # Aggregate ZHVI to county level
    county_zhvi = df_zhvi.groupby('county_name')[latest_zhvi].median().reset_index()
    county_zhvi.columns = ['county_name', 'median_all_homes']

    # Get bottom tier by county
    bottom_tier = df_bottom_tier[['region_name', latest_bt]].copy()
    bottom_tier.columns = ['county_name', 'bottom_tier_value']
    # Clean county name format (remove " County" suffix for matching)

    # Merge
    gap_df = county_zhvi.merge(bottom_tier, on='county_name', how='left')

    # Calculate gap
    gap_df['value_gap_pct'] = (
        (gap_df['median_all_homes'] - gap_df['bottom_tier_value']) /
        gap_df['bottom_tier_value'] * 100
    )

    return gap_df[['county_name', 'value_gap_pct']]


def score_metros(metro_metrics: pd.DataFrame) -> pd.DataFrame:
    """
    Score metros on each metric.
    """
    result = metro_metrics.copy()

    # Velocity score (lower days = higher score)
    result['velocity_score'] = normalize_to_score(
        result['days_to_pending'],
        higher_is_better=False
    )

    # Distress score (higher price cuts = higher score for buyers)
    result['distress_score'] = normalize_to_score(
        result['price_cut_pct'],
        higher_is_better=True
    )

    # Pricing power score (lower sale-to-list = higher score for buyers)
    result['pricing_power_score'] = normalize_to_score(
        result['sale_to_list'],
        higher_is_better=False
    )

    return result


def flip_opportunity_score(
    datasets: Optional[Dict[str, pd.DataFrame]] = None,
    strategy: FlipStrategy = BALANCED,
    appreciation_lookback: int = 12,
    metro_lookback: int = 6,
    min_home_value: float = 50000,
    max_home_value: float = 500000
) -> pd.DataFrame:
    """
    Calculate flip opportunity scores for all ZIPs.

    Args:
        datasets: Dict of loaded datasets (loads if None)
        strategy: FlipStrategy defining weights
        appreciation_lookback: Months to look back for appreciation
        metro_lookback: Months to look back for metro metrics
        min_home_value: Filter out ZIPs below this value
        max_home_value: Filter out ZIPs above this value

    Returns:
        DataFrame with columns:
        - ZIP metadata (region_id, region_name, state, city, metro, county_name)
        - current_value: Latest home value
        - appreciation_score: 0-100
        - velocity_score: 0-100
        - distress_score: 0-100
        - pricing_power_score: 0-100
        - value_gap_score: 0-100
        - composite_score: Weighted average 0-100
        - strategy: Strategy name used
    """
    if datasets is None:
        datasets = load_all_datasets()

    # 1. Calculate ZIP-level appreciation
    appreciation = calculate_price_appreciation(
        datasets['zhvi_zip'],
        lookback_months=appreciation_lookback
    )

    # 2. Get metro-level metrics and scores
    metro_metrics = get_metro_metrics(datasets, lookback_months=metro_lookback)
    metro_scores = score_metros(metro_metrics)

    # 3. Calculate value tier gap by county
    value_gap = calculate_value_tier_gap(
        datasets['zhvi_zip'],
        datasets['zhvi_bottom_tier']
    )

    # 4. Build result dataframe starting with appreciation
    result = appreciation.copy()

    # 5. Join metro scores
    result = result.merge(
        metro_scores[['metro', 'velocity_score', 'distress_score', 'pricing_power_score',
                     'days_to_pending', 'price_cut_pct', 'sale_to_list']],
        on='metro',
        how='left'
    )

    # 6. Join value gap
    result = result.merge(
        value_gap,
        on='county_name',
        how='left'
    )

    # 7. Normalize value gap to score
    result['value_gap_score'] = normalize_to_score(
        result['value_gap_pct'],
        higher_is_better=True
    )

    # 8. Apply value filter
    mask = (
        (result['current_value'] >= min_home_value) &
        (result['current_value'] <= max_home_value) &
        (result['current_value'].notna())
    )
    result = result[mask].copy()

    # 9. Calculate composite score
    result['composite_score'] = (
        result['appreciation_score'] * strategy.appreciation_weight +
        result['velocity_score'].fillna(50) * strategy.velocity_weight +
        result['distress_score'].fillna(50) * strategy.distress_weight +
        result['pricing_power_score'].fillna(50) * strategy.pricing_power_weight +
        result['value_gap_score'].fillna(50) * strategy.value_gap_weight
    )

    # 10. Add strategy info
    result['strategy'] = strategy.name

    # 11. Remove duplicates (can occur from merge)
    result = result.drop_duplicates(subset=['region_id'], keep='first')

    # 12. Sort by composite score
    result = result.sort_values('composite_score', ascending=False)

    # 13. Clean up columns
    output_cols = [
        'region_id', 'region_name', 'state', 'city', 'metro', 'county_name',
        'current_value', 'appreciation_pct',
        'appreciation_score', 'velocity_score', 'distress_score',
        'pricing_power_score', 'value_gap_score', 'composite_score',
        'days_to_pending', 'price_cut_pct', 'sale_to_list', 'value_gap_pct',
        'strategy'
    ]

    # Only include columns that exist
    output_cols = [c for c in output_cols if c in result.columns]

    return result[output_cols].reset_index(drop=True)


def get_score_breakdown(score_df: pd.DataFrame, zip_code: str) -> Dict:
    """
    Get detailed score breakdown for a specific ZIP.
    """
    row = score_df[score_df['region_name'] == zip_code]
    if len(row) == 0:
        return {"error": f"ZIP {zip_code} not found"}

    row = row.iloc[0]

    return {
        'zip_code': zip_code,
        'city': row.get('city', 'N/A'),
        'state': row.get('state', 'N/A'),
        'metro': row.get('metro', 'N/A'),
        'current_value': row.get('current_value', np.nan),
        'composite_score': row.get('composite_score', np.nan),
        'components': {
            'appreciation': {
                'score': row.get('appreciation_score', np.nan),
                'value': f"{row.get('appreciation_pct', np.nan):.1f}%"
            },
            'velocity': {
                'score': row.get('velocity_score', np.nan),
                'value': f"{row.get('days_to_pending', np.nan):.0f} days"
            },
            'distress': {
                'score': row.get('distress_score', np.nan),
                'value': f"{row.get('price_cut_pct', np.nan):.1f}%"
            },
            'pricing_power': {
                'score': row.get('pricing_power_score', np.nan),
                'value': f"{row.get('sale_to_list', np.nan):.3f}"
            },
            'value_gap': {
                'score': row.get('value_gap_score', np.nan),
                'value': f"{row.get('value_gap_pct', np.nan):.1f}%"
            }
        }
    }


def filter_opportunities(
    score_df: pd.DataFrame,
    min_score: float = 60,
    states: Optional[List[str]] = None,
    metros: Optional[List[str]] = None,
    min_appreciation: float = None,
    max_days_to_pending: float = None,
    min_price_cuts: float = None
) -> pd.DataFrame:
    """
    Filter opportunities based on criteria.
    """
    result = score_df.copy()

    # Score filter
    result = result[result['composite_score'] >= min_score]

    # Geographic filters
    if states:
        result = result[result['state'].isin(states)]
    if metros:
        result = result[result['metro'].isin(metros)]

    # Metric filters
    if min_appreciation is not None:
        result = result[result['appreciation_pct'] >= min_appreciation]
    if max_days_to_pending is not None:
        result = result[result['days_to_pending'] <= max_days_to_pending]
    if min_price_cuts is not None:
        result = result[result['price_cut_pct'] >= min_price_cuts]

    return result


def summarize_by_geography(
    score_df: pd.DataFrame,
    level: str = 'state'
) -> pd.DataFrame:
    """
    Summarize opportunities by geographic level.

    Args:
        score_df: Scored opportunities DataFrame
        level: 'state', 'metro', or 'county'

    Returns:
        Summary DataFrame with counts and average scores by geography
    """
    group_col = {
        'state': 'state',
        'metro': 'metro',
        'county': 'county_name'
    }.get(level, 'state')

    summary = score_df.groupby(group_col).agg({
        'composite_score': ['count', 'mean', 'max'],
        'current_value': 'median',
        'appreciation_pct': 'mean'
    }).round(2)

    summary.columns = ['num_opportunities', 'avg_score', 'max_score',
                       'median_value', 'avg_appreciation']

    return summary.sort_values('avg_score', ascending=False)


if __name__ == "__main__":
    print("Loading datasets and calculating scores...")
    scores = flip_opportunity_score(strategy=BALANCED)

    print(f"\nTotal opportunities scored: {len(scores):,}")
    print(f"\nTop 10 opportunities:")
    print(scores.head(10)[['region_name', 'city', 'state', 'current_value',
                           'composite_score']].to_string())
