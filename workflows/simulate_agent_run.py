"""
Agent Simulation Script

Simulates 90 days of agent activity to generate realistic logs, alerts, and reports.
This creates the data needed for the dashboard's Agent Monitoring tab.
"""

import sys
from pathlib import Path
import json
import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_all_datasets
from src.scoring_engine import flip_opportunity_score, BALANCED, FAST_FLIP, VALUE_ADD_FLIP
from src.agent_workflow import (
    AgentOrchestrator, AgentState, AgentLog,
    DataRefreshAgent, ScoringAgent, OpportunityDetectionAgent,
    PropertyAnalysisAgent, AlertAgent, ReportGeneratorAgent
)
from src.alert_system import AlertManager, AlertType, AlertConfig


def simulate_score_variation(base_scores: pd.DataFrame, day: int, total_days: int) -> pd.DataFrame:
    """
    Simulate score variations over time to create realistic opportunity detection.
    """
    scores = base_scores.copy()

    # Add some random variation to scores (simulating market changes)
    np.random.seed(day)  # Reproducible randomness

    # Base variation: small random changes
    variation = np.random.normal(0, 2, len(scores))

    # Trend: some ZIPs improve, some decline
    trend_factor = np.sin(day / 30 * np.pi) * 3  # Seasonal-ish pattern

    # Apply to composite score
    scores['composite_score'] = scores['composite_score'] + variation + trend_factor * 0.1
    scores['composite_score'] = scores['composite_score'].clip(10, 95)

    # Also vary component scores
    for col in ['appreciation_score', 'velocity_score', 'distress_score']:
        if col in scores.columns:
            scores[col] = scores[col] + np.random.normal(0, 3, len(scores))
            scores[col] = scores[col].clip(0, 100)

    return scores


def generate_synthetic_opportunities(scores_df: pd.DataFrame, day: int, previous_hashes: set) -> list:
    """
    Generate synthetic new opportunities for simulation.
    """
    opportunities = []

    # On certain days, "discover" new high-scoring ZIPs
    np.random.seed(day * 7)

    # Filter to high-scoring ZIPs not yet "discovered"
    high_score_zips = scores_df[scores_df['composite_score'] >= 60].copy()

    # Randomly select some as "new discoveries" (more likely on data refresh days)
    is_refresh_day = day % 30 >= 15 and day % 30 <= 17
    discovery_rate = 0.02 if is_refresh_day else 0.005

    for _, row in high_score_zips.iterrows():
        zip_hash = f"{row['region_name']}_{row['state']}"

        if zip_hash not in previous_hashes and random.random() < discovery_rate:
            opportunities.append({
                'zip_code': row['region_name'],
                'city': row.get('city', ''),
                'state': row.get('state', ''),
                'metro': row.get('metro', ''),
                'current_score': float(row['composite_score']),
                'previous_score': None,
                'score_change': 0,
                'current_value': float(row['current_value']),
                'appreciation_pct': float(row.get('appreciation_pct', 0)),
                'days_to_pending': float(row.get('days_to_pending', 60)) if pd.notna(row.get('days_to_pending')) else 60,
                'is_new': True
            })
            previous_hashes.add(zip_hash)

    return opportunities


def run_simulation(days: int = 90, output_dir: Path = None):
    """
    Run the full simulation for the specified number of days.
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "processed" / "agent_logs"

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting {days}-day agent simulation...")
    print(f"Output directory: {output_dir}")

    # Load real data
    print("\nLoading datasets...")
    datasets = load_all_datasets()

    # Get base scores
    print("Computing base scores...")
    base_scores = flip_opportunity_score(
        datasets=datasets,
        strategy=BALANCED,
        min_home_value=50000,
        max_home_value=500000
    )
    print(f"Base scores computed for {len(base_scores):,} ZIPs")

    # Initialize orchestrator
    orchestrator = AgentOrchestrator(output_dir)

    # Initialize alert manager
    alert_manager = AlertManager(output_dir)

    # Track discovered opportunities
    discovered_hashes = set()

    # Simulation timeline
    start_date = datetime.now() - timedelta(days=days)
    simulation_log = []

    print(f"\nSimulating from {start_date.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
    print("-" * 60)

    previous_scores = None

    for day in range(days + 1):
        current_date = start_date + timedelta(days=day)

        # Skip some days (agents don't run every day in simulation)
        # Run daily checks on weekdays, weekly full runs on Sundays
        is_weekday = current_date.weekday() < 5
        is_sunday = current_date.weekday() == 6
        is_data_day = current_date.day >= 16 and current_date.day <= 18

        if not (is_weekday or is_sunday):
            continue

        # Simulate score variations
        current_scores = simulate_score_variation(base_scores, day, days)

        # Generate synthetic new opportunities
        new_opps = generate_synthetic_opportunities(current_scores, day, discovered_hashes)

        # Run the orchestrator
        context = {
            'current_date': current_date,
            'state': orchestrator.state,
            'scores_df': current_scores,
            'previous_scores_df': previous_scores
        }

        # Data refresh check
        data_result = orchestrator.data_refresh_agent.run(context)

        # Scoring
        scoring_result = orchestrator.scoring_agent.run(context)

        # Detection (use our synthetic opportunities)
        detection_result = {
            'new_opportunities': new_opps,
            'changed_opportunities': [],
            'detection_time': current_date.isoformat()
        }

        # Add some score change opportunities
        if previous_scores is not None and random.random() < 0.1:
            # Find ZIPs with significant score changes
            merged = current_scores.merge(
                previous_scores[['region_name', 'composite_score']],
                on='region_name',
                suffixes=('', '_prev')
            )
            merged['score_change'] = merged['composite_score'] - merged['composite_score_prev']
            big_changes = merged[abs(merged['score_change']) >= 5].head(5)

            for _, row in big_changes.iterrows():
                detection_result['changed_opportunities'].append({
                    'zip_code': row['region_name'],
                    'city': row.get('city', ''),
                    'state': row.get('state', ''),
                    'metro': row.get('metro', ''),
                    'current_score': float(row['composite_score']),
                    'previous_score': float(row['composite_score_prev']),
                    'score_change': float(row['score_change']),
                    'current_value': float(row['current_value']),
                    'appreciation_pct': float(row.get('appreciation_pct', 0)),
                    'days_to_pending': float(row.get('days_to_pending', 60)) if pd.notna(row.get('days_to_pending')) else 60,
                    'is_new': False
                })

        # Update orchestrator state
        orchestrator.state.total_opportunities_detected += len(new_opps)

        # Generate alerts
        context['new_opportunities'] = detection_result['new_opportunities']
        context['changed_opportunities'] = detection_result['changed_opportunities']
        alert_result = orchestrator.alert_agent.run(context)

        # Property analysis for top opportunities
        all_opps = detection_result['new_opportunities'] + detection_result['changed_opportunities']
        context['opportunities'] = all_opps[:5]  # Analyze top 5
        analysis_result = orchestrator.property_agent.run(context)

        # Report generation (Sundays only)
        context['alerts'] = orchestrator.alert_agent.load_alerts()
        report_result = orchestrator.report_agent.run(context)

        # Log this day's activity
        day_log = {
            'date': current_date.isoformat(),
            'data_refresh': data_result.get('new_data_available', False),
            'new_opportunities': len(new_opps),
            'changed_opportunities': len(detection_result['changed_opportunities']),
            'alerts_generated': len(alert_result.get('alerts', [])),
            'priority_counts': alert_result.get('priority_counts', {}),
            'reports_generated': report_result.get('reports_generated', [])
        }
        simulation_log.append(day_log)

        # Print progress
        if day % 10 == 0 or len(new_opps) > 0:
            print(f"Day {day:3d} ({current_date.strftime('%Y-%m-%d')}): "
                  f"{len(new_opps)} new, {len(detection_result['changed_opportunities'])} changed, "
                  f"{len(alert_result.get('alerts', []))} alerts")

        # Update previous scores
        previous_scores = current_scores.copy()

    # Save simulation log
    log_file = output_dir / "simulation_log.json"
    with open(log_file, 'w') as f:
        json.dump(simulation_log, f, indent=2)

    # Save agent state
    orchestrator._save_state()

    # Save all agent logs
    for agent in orchestrator.agents:
        agent.save_logs()

    # Generate summary statistics
    summary = generate_simulation_summary(simulation_log, output_dir)

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"\nDays simulated: {days}")
    print(f"Total new opportunities detected: {summary['total_new_opportunities']}")
    print(f"Total alerts generated: {summary['total_alerts']}")
    print(f"HOT alerts: {summary['hot_alerts']}")
    print(f"WARM alerts: {summary['warm_alerts']}")
    print(f"Data refreshes: {summary['data_refreshes']}")
    print(f"Reports generated: {summary['reports_generated']}")

    print(f"\nOutput files saved to: {output_dir}")
    print("  - simulation_log.json")
    print("  - agent_state.json")
    print("  - alerts.json")
    print("  - *_logs.json (per agent)")
    print("  - reports/ (weekly reports)")

    return summary


def generate_simulation_summary(simulation_log: list, output_dir: Path) -> dict:
    """Generate summary statistics from simulation."""
    summary = {
        'simulation_days': len(simulation_log),
        'total_new_opportunities': sum(d['new_opportunities'] for d in simulation_log),
        'total_changed_opportunities': sum(d['changed_opportunities'] for d in simulation_log),
        'total_alerts': sum(d['alerts_generated'] for d in simulation_log),
        'hot_alerts': sum(d['priority_counts'].get('HOT', 0) for d in simulation_log),
        'warm_alerts': sum(d['priority_counts'].get('WARM', 0) for d in simulation_log),
        'watch_alerts': sum(d['priority_counts'].get('WATCH', 0) for d in simulation_log),
        'data_refreshes': sum(1 for d in simulation_log if d['data_refresh']),
        'reports_generated': sum(len(d['reports_generated']) for d in simulation_log),
        'avg_daily_alerts': sum(d['alerts_generated'] for d in simulation_log) / len(simulation_log) if simulation_log else 0
    }

    # Save summary
    summary_file = output_dir / "simulation_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def generate_timeline_data(output_dir: Path) -> pd.DataFrame:
    """Generate timeline data for visualization."""
    log_file = output_dir / "simulation_log.json"

    if not log_file.exists():
        return pd.DataFrame()

    with open(log_file, 'r') as f:
        simulation_log = json.load(f)

    timeline = pd.DataFrame(simulation_log)
    timeline['date'] = pd.to_datetime(timeline['date'])
    timeline = timeline.sort_values('date')

    # Calculate cumulative totals
    timeline['cumulative_opportunities'] = timeline['new_opportunities'].cumsum()
    timeline['cumulative_alerts'] = timeline['alerts_generated'].cumsum()

    # Save timeline
    timeline_file = output_dir / "timeline_data.csv"
    timeline.to_csv(timeline_file, index=False)

    return timeline


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simulate agent workflow")
    parser.add_argument('--days', type=int, default=90, help='Number of days to simulate')
    parser.add_argument('--output', type=str, default=None, help='Output directory')

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None
    summary = run_simulation(days=args.days, output_dir=output_path)

    # Generate timeline data
    output_dir = output_path or Path(__file__).parent.parent / "data" / "processed" / "agent_logs"
    timeline = generate_timeline_data(output_dir)
    print(f"\nTimeline data saved with {len(timeline)} records")
