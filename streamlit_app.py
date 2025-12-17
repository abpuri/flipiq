"""
Flip Opportunity Dashboard

Interactive Streamlit dashboard for exploring house flip opportunities
based on Zillow data analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_all_datasets, get_date_columns
from src.scoring_engine import (
    flip_opportunity_score,
    filter_opportunities,
    summarize_by_geography,
    FAST_FLIP, VALUE_ADD_FLIP, BALANCED, FlipStrategy
)
from src.property_analyzer import PropertyAnalyzer
import json
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Flip Opportunity Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .big-number {
        font-size: 2.5em;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data():
    """Load and cache all datasets."""
    return load_all_datasets()


def load_agent_data():
    """Load agent logs and state data."""
    agent_logs_dir = Path(__file__).parent / "data" / "processed" / "agent_logs"

    data = {
        'state': None,
        'alerts': [],
        'summary': None,
        'timeline': None,
        'agent_logs': {}
    }

    if not agent_logs_dir.exists():
        return data

    # Load agent state
    state_file = agent_logs_dir / "agent_state.json"
    if state_file.exists():
        with open(state_file, 'r') as f:
            data['state'] = json.load(f)

    # Load alerts
    alerts_file = agent_logs_dir / "alerts.json"
    if alerts_file.exists():
        with open(alerts_file, 'r') as f:
            data['alerts'] = json.load(f)

    # Load simulation summary
    summary_file = agent_logs_dir / "simulation_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data['summary'] = json.load(f)

    # Load timeline data
    timeline_file = agent_logs_dir / "timeline_data.csv"
    if timeline_file.exists():
        data['timeline'] = pd.read_csv(timeline_file)
        data['timeline']['date'] = pd.to_datetime(data['timeline']['date'])

    # Load individual agent logs
    for log_file in agent_logs_dir.glob("*_logs.json"):
        agent_name = log_file.stem.replace("_logs", "")
        with open(log_file, 'r') as f:
            data['agent_logs'][agent_name] = json.load(f)

    return data


@st.cache_data(ttl=3600)
def compute_scores(_datasets, strategy_name, min_value, max_value):
    """Compute scores with caching."""
    strategy_map = {
        "Fast Flip": FAST_FLIP,
        "Value-Add Flip": VALUE_ADD_FLIP,
        "Balanced": BALANCED
    }
    strategy = strategy_map[strategy_name]

    return flip_opportunity_score(
        datasets=_datasets,
        strategy=strategy,
        min_home_value=min_value,
        max_home_value=max_value
    )


def main():
    # Header
    st.title("🏠 House Flip Opportunity Dashboard")
    st.markdown("*Identify high-potential flip opportunities using Zillow data*")

    # Load data
    with st.spinner("Loading data..."):
        datasets = load_data()

    # =====================================
    # SIDEBAR FILTERS
    # =====================================
    st.sidebar.header("🔍 Filters")

    # Strategy selector
    strategy_name = st.sidebar.selectbox(
        "Flip Strategy",
        ["Balanced", "Fast Flip", "Value-Add Flip"],
        help="Fast Flip: Prioritizes quick sales. Value-Add: Prioritizes renovation potential."
    )

    # Show strategy weights
    strategy_map = {
        "Fast Flip": FAST_FLIP,
        "Value-Add Flip": VALUE_ADD_FLIP,
        "Balanced": BALANCED
    }
    strategy = strategy_map[strategy_name]

    with st.sidebar.expander("Strategy Weights"):
        st.write(f"Appreciation: {strategy.appreciation_weight:.0%}")
        st.write(f"Velocity: {strategy.velocity_weight:.0%}")
        st.write(f"Distress: {strategy.distress_weight:.0%}")
        st.write(f"Pricing Power: {strategy.pricing_power_weight:.0%}")
        st.write(f"Value Gap: {strategy.value_gap_weight:.0%}")

    # Price range
    price_range = st.sidebar.slider(
        "Price Range ($)",
        min_value=50000,
        max_value=500000,
        value=(50000, 500000),
        step=10000,
        format="$%d"
    )

    # Minimum score
    min_score = st.sidebar.slider(
        "Minimum Score",
        min_value=30,
        max_value=80,
        value=50,
        step=5
    )

    # Top N results
    top_n = st.sidebar.slider(
        "Show Top N Results",
        min_value=10,
        max_value=200,
        value=50,
        step=10
    )

    # Compute scores
    with st.spinner("Computing opportunity scores..."):
        all_scores = compute_scores(
            datasets,
            strategy_name,
            price_range[0],
            price_range[1]
        )

    # Geographic filters (after computing scores to get options)
    states = sorted(all_scores['state'].dropna().unique().tolist())
    selected_states = st.sidebar.multiselect(
        "Filter by State",
        options=states,
        default=[]
    )

    # Get metros for selected states
    if selected_states:
        metros = sorted(all_scores[all_scores['state'].isin(selected_states)]['metro'].dropna().unique().tolist())
    else:
        metros = sorted(all_scores['metro'].dropna().unique().tolist())

    selected_metros = st.sidebar.multiselect(
        "Filter by Metro",
        options=metros,
        default=[]
    )

    # Apply filters
    filtered_scores = filter_opportunities(
        all_scores,
        min_score=min_score,
        states=selected_states if selected_states else None,
        metros=selected_metros if selected_metros else None
    )

    # Limit to top N
    display_scores = filtered_scores.head(top_n)

    # =====================================
    # KEY METRICS
    # =====================================
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Opportunities",
            f"{len(filtered_scores):,}",
            delta=f"of {len(all_scores):,} total"
        )

    with col2:
        avg_score = filtered_scores['composite_score'].mean() if len(filtered_scores) > 0 else 0
        st.metric(
            "Avg Opportunity Score",
            f"{avg_score:.1f}",
            delta=f"{avg_score - all_scores['composite_score'].mean():.1f} vs all"
        )

    with col3:
        median_value = filtered_scores['current_value'].median() if len(filtered_scores) > 0 else 0
        st.metric(
            "Median Home Value",
            f"${median_value:,.0f}"
        )

    with col4:
        avg_dtp = filtered_scores['days_to_pending'].mean() if len(filtered_scores) > 0 else 0
        st.metric(
            "Avg Days to Pending",
            f"{avg_dtp:.0f} days"
        )

    # =====================================
    # TABS
    # =====================================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Top Opportunities",
        "🗺️ Geographic View",
        "📈 Score Analysis",
        "📉 Market Trends",
        "⚖️ Compare ZIPs",
        "🤖 Agent Monitoring"
    ])

    # ----- TAB 1: TOP OPPORTUNITIES -----
    with tab1:
        st.subheader(f"Top {len(display_scores)} Flip Opportunities")

        if len(display_scores) == 0:
            st.warning("No opportunities match your filters. Try adjusting the criteria.")
        else:
            # Format for display
            display_df = display_scores.copy()
            display_df['rank'] = range(1, len(display_df) + 1)
            display_df['current_value'] = display_df['current_value'].apply(lambda x: f"${x:,.0f}")
            display_df['composite_score'] = display_df['composite_score'].round(1)
            display_df['appreciation_score'] = display_df['appreciation_score'].round(1)
            display_df['velocity_score'] = display_df['velocity_score'].round(1)
            display_df['distress_score'] = display_df['distress_score'].round(1)
            display_df['pricing_power_score'] = display_df['pricing_power_score'].round(1)
            display_df['value_gap_score'] = display_df['value_gap_score'].round(1)
            display_df['appreciation_pct'] = display_df['appreciation_pct'].apply(lambda x: f"{x:.1f}%")
            display_df['days_to_pending'] = display_df['days_to_pending'].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else "N/A"
            )
            display_df['price_cut_pct'] = display_df['price_cut_pct'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
            )

            display_cols = [
                'rank', 'region_name', 'city', 'state', 'metro',
                'current_value', 'composite_score',
                'appreciation_score', 'velocity_score', 'distress_score',
                'pricing_power_score', 'value_gap_score',
                'appreciation_pct', 'days_to_pending', 'price_cut_pct'
            ]

            # Rename for display
            col_names = {
                'rank': 'Rank',
                'region_name': 'ZIP',
                'city': 'City',
                'state': 'State',
                'metro': 'Metro',
                'current_value': 'Value',
                'composite_score': 'Score',
                'appreciation_score': 'Apprec.',
                'velocity_score': 'Velocity',
                'distress_score': 'Distress',
                'pricing_power_score': 'Pricing',
                'value_gap_score': 'Gap',
                'appreciation_pct': '12mo %',
                'days_to_pending': 'Days',
                'price_cut_pct': 'Cuts %'
            }

            st.dataframe(
                display_df[display_cols].rename(columns=col_names),
                use_container_width=True,
                height=500
            )

            # Export button
            st.markdown("---")
            csv = filtered_scores.to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Results (CSV)",
                data=csv,
                file_name="flip_opportunities.csv",
                mime="text/csv"
            )

    # ----- TAB 2: GEOGRAPHIC VIEW -----
    with tab2:
        st.subheader("Geographic Distribution of Opportunities")

        if len(filtered_scores) == 0:
            st.warning("No data to display. Adjust filters.")
        else:
            # State-level summary
            state_summary = summarize_by_geography(filtered_scores, level='state')
            state_summary = state_summary.reset_index()

            # US State choropleth
            fig_states = px.choropleth(
                state_summary,
                locations='state',
                locationmode='USA-states',
                color='avg_score',
                color_continuous_scale='RdYlGn',
                scope='usa',
                title='Average Opportunity Score by State',
                hover_data=['num_opportunities', 'median_value', 'avg_appreciation']
            )
            fig_states.update_layout(height=450)
            st.plotly_chart(fig_states, use_container_width=True)

            col1, col2 = st.columns(2)

            with col1:
                # Top states bar chart
                top_states = state_summary.sort_values('avg_score', ascending=True).tail(15)
                fig_bar = px.bar(
                    top_states,
                    x='avg_score',
                    y='state',
                    orientation='h',
                    title='Top 15 States by Avg Score',
                    color='avg_score',
                    color_continuous_scale='RdYlGn'
                )
                fig_bar.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            with col2:
                # Opportunities count by state
                top_count = state_summary.sort_values('num_opportunities', ascending=True).tail(15)
                fig_count = px.bar(
                    top_count,
                    x='num_opportunities',
                    y='state',
                    orientation='h',
                    title='Top 15 States by # of Opportunities',
                    color='num_opportunities',
                    color_continuous_scale='Blues'
                )
                fig_count.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_count, use_container_width=True)

            # Metro summary
            st.markdown("---")
            st.subheader("Metro Area Analysis")

            metro_summary = summarize_by_geography(filtered_scores, level='metro')
            metro_summary = metro_summary.reset_index()
            metro_summary = metro_summary[metro_summary['num_opportunities'] >= 3]  # Min 3 ZIPs

            # Top metros
            top_metros = metro_summary.sort_values('avg_score', ascending=False).head(20)

            fig_metro = px.bar(
                top_metros.sort_values('avg_score', ascending=True),
                x='avg_score',
                y='metro',
                orientation='h',
                title='Top 20 Metros by Avg Score (min 3 ZIPs)',
                color='avg_score',
                color_continuous_scale='RdYlGn',
                hover_data=['num_opportunities', 'median_value']
            )
            fig_metro.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_metro, use_container_width=True)

    # ----- TAB 3: SCORE ANALYSIS -----
    with tab3:
        st.subheader("Score Distribution Analysis")

        if len(filtered_scores) == 0:
            st.warning("No data to display. Adjust filters.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # Composite score histogram
                fig_hist = px.histogram(
                    filtered_scores,
                    x='composite_score',
                    nbins=30,
                    title='Composite Score Distribution',
                    color_discrete_sequence=['steelblue']
                )
                fig_hist.add_vline(
                    x=filtered_scores['composite_score'].mean(),
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Mean: {filtered_scores['composite_score'].mean():.1f}"
                )
                fig_hist.update_layout(height=350)
                st.plotly_chart(fig_hist, use_container_width=True)

            with col2:
                # Score components box plot
                score_cols = ['appreciation_score', 'velocity_score', 'distress_score',
                             'pricing_power_score', 'value_gap_score']
                score_data = filtered_scores[score_cols].melt(var_name='Component', value_name='Score')
                score_data['Component'] = score_data['Component'].str.replace('_score', '').str.title()

                fig_box = px.box(
                    score_data,
                    x='Component',
                    y='Score',
                    title='Score Components Distribution',
                    color='Component'
                )
                fig_box.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_box, use_container_width=True)

            # Correlation heatmap
            st.markdown("---")
            st.subheader("Score Component Correlations")

            corr_cols = ['composite_score', 'appreciation_score', 'velocity_score',
                        'distress_score', 'pricing_power_score', 'value_gap_score',
                        'current_value', 'appreciation_pct']
            corr_matrix = filtered_scores[corr_cols].corr()

            fig_corr = px.imshow(
                corr_matrix,
                text_auto='.2f',
                color_continuous_scale='RdBu_r',
                title='Correlation Matrix'
            )
            fig_corr.update_layout(height=500)
            st.plotly_chart(fig_corr, use_container_width=True)

            # Score vs Value scatter
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                fig_scatter = px.scatter(
                    filtered_scores.head(500),
                    x='current_value',
                    y='composite_score',
                    color='state',
                    title='Score vs Home Value',
                    hover_data=['region_name', 'city', 'metro']
                )
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)

            with col2:
                fig_scatter2 = px.scatter(
                    filtered_scores.head(500),
                    x='appreciation_pct',
                    y='composite_score',
                    color='state',
                    title='Score vs 12-Month Appreciation',
                    hover_data=['region_name', 'city', 'metro']
                )
                fig_scatter2.update_layout(height=400)
                st.plotly_chart(fig_scatter2, use_container_width=True)

    # ----- TAB 4: MARKET TRENDS -----
    with tab4:
        st.subheader("Market Trends - ZHVI Over Time")

        # Get top ZIPs for trend analysis
        top_zips = filtered_scores.head(10)['region_name'].tolist()

        if len(top_zips) == 0:
            st.warning("No ZIPs selected. Adjust filters.")
        else:
            # Select ZIPs to visualize
            selected_trend_zips = st.multiselect(
                "Select ZIPs to view trends (max 10)",
                options=top_zips,
                default=top_zips[:5] if len(top_zips) >= 5 else top_zips
            )

            if selected_trend_zips:
                # Get ZHVI data for selected ZIPs
                zhvi_df = datasets['zhvi_zip']
                date_cols = get_date_columns(zhvi_df)

                trend_data = zhvi_df[zhvi_df['region_name'].isin(selected_trend_zips)]

                # Melt to long format
                trend_long = trend_data.melt(
                    id_vars=['region_name', 'city', 'state'],
                    value_vars=date_cols,
                    var_name='date',
                    value_name='value'
                )
                trend_long['date'] = pd.to_datetime(trend_long['date'])
                trend_long['label'] = trend_long['region_name'] + ' - ' + trend_long['city'].fillna('')

                # Line chart
                fig_trend = px.line(
                    trend_long,
                    x='date',
                    y='value',
                    color='label',
                    title='Home Value Trends (ZHVI)',
                    labels={'value': 'Home Value ($)', 'date': 'Date'}
                )
                fig_trend.update_layout(height=450, legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_trend, use_container_width=True)

                # YoY change
                st.markdown("---")
                st.subheader("Year-over-Year Change")

                # Calculate YoY for each ZIP
                yoy_data = []
                for zip_code in selected_trend_zips:
                    zip_data = trend_long[trend_long['region_name'] == zip_code].sort_values('date')
                    zip_data['yoy_change'] = zip_data['value'].pct_change(periods=12) * 100
                    yoy_data.append(zip_data)

                yoy_df = pd.concat(yoy_data)

                fig_yoy = px.line(
                    yoy_df,
                    x='date',
                    y='yoy_change',
                    color='label',
                    title='Year-over-Year Appreciation (%)',
                    labels={'yoy_change': 'YoY Change (%)', 'date': 'Date'}
                )
                fig_yoy.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_yoy.update_layout(height=400, legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_yoy, use_container_width=True)

    # ----- TAB 5: COMPARE ZIPS -----
    with tab5:
        st.subheader("Compare ZIP Codes")

        # Get available ZIPs from filtered results
        available_zips = filtered_scores.head(100)['region_name'].tolist()

        if len(available_zips) < 2:
            st.warning("Need at least 2 ZIPs to compare. Adjust filters.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                zip1 = st.selectbox("Select First ZIP", available_zips, index=0)
            with col2:
                zip2 = st.selectbox("Select Second ZIP", available_zips, index=min(1, len(available_zips)-1))

            if zip1 and zip2:
                # Get data for both ZIPs
                zip1_data = filtered_scores[filtered_scores['region_name'] == zip1].iloc[0]
                zip2_data = filtered_scores[filtered_scores['region_name'] == zip2].iloc[0]

                # Comparison table
                st.markdown("---")

                comparison_metrics = [
                    ('City', 'city', ''),
                    ('State', 'state', ''),
                    ('Metro', 'metro', ''),
                    ('Current Value', 'current_value', '$,.0f'),
                    ('Composite Score', 'composite_score', '.1f'),
                    ('Appreciation Score', 'appreciation_score', '.1f'),
                    ('Velocity Score', 'velocity_score', '.1f'),
                    ('Distress Score', 'distress_score', '.1f'),
                    ('Pricing Power Score', 'pricing_power_score', '.1f'),
                    ('Value Gap Score', 'value_gap_score', '.1f'),
                    ('12-Month Appreciation', 'appreciation_pct', '.1f%'),
                    ('Days to Pending', 'days_to_pending', '.0f'),
                    ('Price Cut %', 'price_cut_pct', '.1f%'),
                ]

                col1, col2, col3 = st.columns([1, 2, 2])

                with col1:
                    st.markdown("**Metric**")
                    for label, _, _ in comparison_metrics:
                        st.write(label)

                with col2:
                    st.markdown(f"**ZIP {zip1}**")
                    for _, col, fmt in comparison_metrics:
                        val = zip1_data.get(col, 'N/A')
                        if pd.isna(val):
                            st.write("N/A")
                        elif fmt and fmt.startswith('$'):
                            st.write(f"${val:,.0f}")
                        elif fmt and fmt.endswith('%'):
                            st.write(f"{val:.1f}%")
                        elif fmt:
                            st.write(f"{val:{fmt}}")
                        else:
                            st.write(str(val))

                with col3:
                    st.markdown(f"**ZIP {zip2}**")
                    for _, col, fmt in comparison_metrics:
                        val = zip2_data.get(col, 'N/A')
                        if pd.isna(val):
                            st.write("N/A")
                        elif fmt and fmt.startswith('$'):
                            st.write(f"${val:,.0f}")
                        elif fmt and fmt.endswith('%'):
                            st.write(f"{val:.1f}%")
                        elif fmt:
                            st.write(f"{val:{fmt}}")
                        else:
                            st.write(str(val))

                # Radar chart comparison
                st.markdown("---")
                st.subheader("Score Component Comparison")

                categories = ['Appreciation', 'Velocity', 'Distress', 'Pricing Power', 'Value Gap']

                fig_radar = go.Figure()

                fig_radar.add_trace(go.Scatterpolar(
                    r=[zip1_data['appreciation_score'], zip1_data['velocity_score'],
                       zip1_data['distress_score'], zip1_data['pricing_power_score'],
                       zip1_data['value_gap_score']],
                    theta=categories,
                    fill='toself',
                    name=f'ZIP {zip1}'
                ))

                fig_radar.add_trace(go.Scatterpolar(
                    r=[zip2_data['appreciation_score'], zip2_data['velocity_score'],
                       zip2_data['distress_score'], zip2_data['pricing_power_score'],
                       zip2_data['value_gap_score']],
                    theta=categories,
                    fill='toself',
                    name=f'ZIP {zip2}'
                ))

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True,
                    height=450
                )

                st.plotly_chart(fig_radar, use_container_width=True)

                # Price trends comparison
                st.markdown("---")
                st.subheader("Price Trend Comparison")

                zhvi_df = datasets['zhvi_zip']
                date_cols = get_date_columns(zhvi_df)

                compare_zips = [zip1, zip2]
                trend_data = zhvi_df[zhvi_df['region_name'].isin(compare_zips)]

                trend_long = trend_data.melt(
                    id_vars=['region_name', 'city'],
                    value_vars=date_cols,
                    var_name='date',
                    value_name='value'
                )
                trend_long['date'] = pd.to_datetime(trend_long['date'])
                trend_long['label'] = trend_long['region_name'] + ' - ' + trend_long['city'].fillna('')

                fig_compare_trend = px.line(
                    trend_long,
                    x='date',
                    y='value',
                    color='label',
                    title='Home Value Comparison',
                    labels={'value': 'Home Value ($)', 'date': 'Date'}
                )
                fig_compare_trend.update_layout(height=350)
                st.plotly_chart(fig_compare_trend, use_container_width=True)

    # ----- TAB 6: AGENT MONITORING -----
    with tab6:
        st.subheader("Agent Monitoring Dashboard")

        # Load agent data
        agent_data = load_agent_data()

        if agent_data['state'] is None:
            st.warning("No agent data available. Run the simulation first: `python workflows/simulate_agent_run.py`")
        else:
            # ===== AGENT STATUS PANEL =====
            st.markdown("### Agent Status")

            state = agent_data['state']
            summary = agent_data['summary'] or {}

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                last_refresh = state.get('last_data_refresh', 'Never')
                if last_refresh and last_refresh != 'Never':
                    last_refresh_dt = datetime.fromisoformat(last_refresh)
                    last_refresh_str = last_refresh_dt.strftime('%Y-%m-%d %H:%M')
                else:
                    last_refresh_str = 'Never'
                st.metric("Last Data Refresh", last_refresh_str)

            with col2:
                st.metric("Total Opportunities", f"{state.get('total_opportunities_detected', 0):,}")

            with col3:
                st.metric("Total Alerts", f"{summary.get('total_alerts', 0):,}")

            with col4:
                st.metric("Data Version", state.get('data_version', 'Unknown'))

            # Agent health indicators
            st.markdown("#### Agent Health Status")
            agent_cols = st.columns(6)
            agents = [
                ("DataRefresh", "DataRefreshAgent"),
                ("Scoring", "ScoringAgent"),
                ("Detection", "OpportunityDetectionAgent"),
                ("Analysis", "PropertyAnalysisAgent"),
                ("Alert", "AlertAgent"),
                ("Report", "ReportGeneratorAgent")
            ]

            for i, (label, agent_key) in enumerate(agents):
                with agent_cols[i]:
                    logs = agent_data['agent_logs'].get(agent_key, [])
                    if logs:
                        last_log = logs[-1] if isinstance(logs, list) and len(logs) > 0 else {}
                        status = last_log.get('status', 'unknown')
                        if status == 'completed':
                            st.success(f"✅ {label}")
                        elif status == 'running':
                            st.warning(f"⏳ {label}")
                        else:
                            st.info(f"⬜ {label}")
                    else:
                        st.info(f"⬜ {label}")

            st.markdown("---")

            # ===== RECENT ALERTS SECTION =====
            st.markdown("### Recent Alerts")

            alerts = agent_data['alerts']
            if alerts:
                # Filter controls
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    priority_filter = st.selectbox(
                        "Priority",
                        ["All", "HOT", "WARM", "WATCH"],
                        index=0
                    )
                with col2:
                    num_alerts = st.slider("Show", 10, 100, 25, step=5)

                # Apply filter
                filtered_alerts = alerts
                if priority_filter != "All":
                    filtered_alerts = [a for a in alerts if a.get('priority') == priority_filter]

                # Sort by timestamp (newest first) and limit
                filtered_alerts = sorted(
                    filtered_alerts,
                    key=lambda x: x.get('timestamp', ''),
                    reverse=True
                )[:num_alerts]

                # Display alerts
                for alert in filtered_alerts:
                    priority = alert.get('priority', 'INFO')
                    priority_color = {
                        'HOT': '🔥',
                        'WARM': '🌡️',
                        'WATCH': '👀',
                        'INFO': 'ℹ️'
                    }.get(priority, '⬜')

                    timestamp = alert.get('timestamp', '')
                    if timestamp:
                        try:
                            ts_dt = datetime.fromisoformat(timestamp)
                            timestamp = ts_dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pass

                    zip_code = alert.get('zip_code', 'N/A')
                    city = alert.get('city', '')
                    state_abbr = alert.get('state', '')
                    score = alert.get('current_score', 0)
                    value = alert.get('current_value', 0)
                    reason = alert.get('trigger_reason', 'No reason provided')

                    with st.expander(f"{priority_color} [{priority}] ZIP {zip_code} - {city}, {state_abbr} (Score: {score:.1f})"):
                        st.write(f"**Timestamp:** {timestamp}")
                        st.write(f"**Value:** ${value:,.0f}")
                        st.write(f"**Reason:** {reason}")
                        st.write(f"**Action:** {alert.get('recommended_action', 'Review recommended')}")
                        if alert.get('is_new_opportunity'):
                            st.info("🆕 New Opportunity")

                # Summary stats
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    hot_count = len([a for a in alerts if a.get('priority') == 'HOT'])
                    st.metric("HOT Alerts", hot_count, delta=None)
                with col2:
                    warm_count = len([a for a in alerts if a.get('priority') == 'WARM'])
                    st.metric("WARM Alerts", warm_count, delta=None)
                with col3:
                    watch_count = len([a for a in alerts if a.get('priority') == 'WATCH'])
                    st.metric("WATCH Alerts", watch_count, delta=None)
                with col4:
                    unack = len([a for a in alerts if not a.get('acknowledged', False)])
                    st.metric("Unacknowledged", unack, delta=None)

            else:
                st.info("No alerts generated yet.")

            st.markdown("---")

            # ===== OPPORTUNITY TIMELINE =====
            st.markdown("### Opportunity Timeline")

            timeline = agent_data['timeline']
            if timeline is not None and len(timeline) > 0:
                col1, col2 = st.columns(2)

                with col1:
                    # Cumulative opportunities chart
                    fig_cum_opp = px.line(
                        timeline,
                        x='date',
                        y='cumulative_opportunities',
                        title='Cumulative Opportunities Detected',
                        labels={'cumulative_opportunities': 'Total Opportunities', 'date': 'Date'}
                    )
                    fig_cum_opp.update_layout(height=350)
                    st.plotly_chart(fig_cum_opp, use_container_width=True)

                with col2:
                    # Cumulative alerts chart
                    fig_cum_alerts = px.line(
                        timeline,
                        x='date',
                        y='cumulative_alerts',
                        title='Cumulative Alerts Generated',
                        labels={'cumulative_alerts': 'Total Alerts', 'date': 'Date'},
                        color_discrete_sequence=['orange']
                    )
                    fig_cum_alerts.update_layout(height=350)
                    st.plotly_chart(fig_cum_alerts, use_container_width=True)

                # Daily activity bar chart
                fig_daily = go.Figure()
                fig_daily.add_trace(go.Bar(
                    x=timeline['date'],
                    y=timeline['new_opportunities'],
                    name='New Opportunities',
                    marker_color='steelblue'
                ))
                fig_daily.add_trace(go.Bar(
                    x=timeline['date'],
                    y=timeline['alerts_generated'],
                    name='Alerts Generated',
                    marker_color='coral'
                ))
                fig_daily.update_layout(
                    title='Daily Agent Activity',
                    barmode='group',
                    height=350,
                    legend=dict(orientation="h", y=-0.15)
                )
                st.plotly_chart(fig_daily, use_container_width=True)

            else:
                st.info("No timeline data available.")

            st.markdown("---")

            # ===== AGENT DECISION LOG =====
            st.markdown("### Agent Decision Log")

            agent_logs = agent_data['agent_logs']
            if agent_logs:
                selected_agent = st.selectbox(
                    "Select Agent",
                    list(agent_logs.keys())
                )

                if selected_agent:
                    logs = agent_logs[selected_agent]
                    if logs and isinstance(logs, list) and len(logs) > 0:
                        # Show last N logs
                        num_logs = st.slider("Show last N entries", 5, 50, 10)
                        recent_logs = logs[-num_logs:][::-1]  # Reverse to show newest first

                        for log in recent_logs:
                            status = log.get('status', 'unknown')
                            status_icon = {'completed': '✅', 'running': '⏳', 'failed': '❌'}.get(status, '⬜')

                            timestamp = log.get('timestamp', '')
                            if timestamp:
                                try:
                                    ts_dt = datetime.fromisoformat(timestamp)
                                    timestamp = ts_dt.strftime('%Y-%m-%d %H:%M')
                                except:
                                    pass

                            action = log.get('action', 'Unknown action')
                            with st.expander(f"{status_icon} [{timestamp}] {action}"):
                                st.json(log.get('details', {}))
                    else:
                        st.info(f"No logs available for {selected_agent}")
            else:
                st.info("No agent logs available.")

            st.markdown("---")

            # ===== MANUAL CONTROLS =====
            st.markdown("### Manual Controls")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Threshold Configuration**")
                hot_threshold = st.number_input("HOT Score Threshold", 50, 100, 70)
                warm_threshold = st.number_input("WARM Score Threshold", 40, 90, 60)
                st.caption("These thresholds determine alert priority levels.")

            with col2:
                st.markdown("**Quick Actions**")
                if st.button("🔄 Refresh Agent Data"):
                    st.cache_data.clear()
                    st.rerun()

                st.caption("Click to reload agent data from disk.")

            with col3:
                st.markdown("**Export Options**")
                # Download alerts as CSV
                if alerts:
                    alerts_df = pd.DataFrame(alerts)
                    csv_alerts = alerts_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Alerts (CSV)",
                        data=csv_alerts,
                        file_name="agent_alerts.csv",
                        mime="text/csv"
                    )

                # Download timeline
                if timeline is not None and len(timeline) > 0:
                    csv_timeline = timeline.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Timeline (CSV)",
                        data=csv_timeline,
                        file_name="agent_timeline.csv",
                        mime="text/csv"
                    )

            st.markdown("---")

            # ===== PROPERTY DEEP DIVE =====
            st.markdown("### Property Deep Dive")
            st.caption("Select a ZIP code from recent HOT alerts for detailed analysis.")

            # Get HOT alert ZIP codes
            hot_zips = list(set([
                a.get('zip_code') for a in alerts
                if a.get('priority') == 'HOT' and a.get('zip_code')
            ]))[:20]

            if hot_zips:
                selected_zip = st.selectbox("Select ZIP for Deep Dive", hot_zips)

                if selected_zip and st.button("🔍 Analyze ZIP"):
                    with st.spinner(f"Analyzing ZIP {selected_zip}..."):
                        try:
                            # Initialize analyzer
                            analyzer = PropertyAnalyzer(datasets)

                            # Get analysis
                            report = analyzer.analyze_zip(selected_zip)

                            if report:
                                st.success(f"Analysis complete for {report.zip_code} ({report.city}, {report.state})")

                                col1, col2 = st.columns(2)

                                with col1:
                                    st.markdown("#### Trend Analysis")
                                    trend = report.trend_analysis
                                    st.write(f"**Current Value:** ${trend.current_value:,.0f}")
                                    st.write(f"**Trend Direction:** {trend.trend_direction.title()}")
                                    st.write(f"**Trend Strength:** {trend.trend_strength.title()}")
                                    st.write(f"**Volatility Score:** {trend.volatility_score:.1f}")
                                    st.write(f"**YoY Change:** {trend.yoy_change_pct:.1f}%")
                                    if trend.two_year_change_pct:
                                        st.write(f"**2-Year Change:** {trend.two_year_change_pct:.1f}%")
                                    st.write(f"**Seasonality Detected:** {'Yes' if trend.seasonality_detected else 'No'}")

                                with col2:
                                    st.markdown("#### Market Momentum")
                                    momentum = report.momentum
                                    st.write(f"**Momentum Score:** {momentum.momentum_score:.1f}")
                                    st.write(f"**Momentum Grade:** {momentum.momentum_grade}")
                                    st.write(f"**Velocity Score:** {momentum.velocity_score:.1f}")
                                    st.write(f"**Appreciation Score:** {momentum.appreciation_score:.1f}")
                                    st.write(f"**Demand Score:** {momentum.demand_score:.1f}")
                                    if momentum.momentum_factors:
                                        st.markdown("**Key Factors:**")
                                        for factor in momentum.momentum_factors[:3]:
                                            st.write(f"- {factor}")

                                st.markdown("---")
                                col3, col4 = st.columns(2)

                                with col3:
                                    st.markdown("#### Risk Assessment")
                                    risk = report.risk
                                    risk_colors = {'Low': 'green', 'Medium': 'orange', 'High': 'red', 'Very High': 'red'}
                                    st.markdown(f"**Risk Grade:** :{risk_colors.get(risk.risk_grade, 'gray')}[{risk.risk_grade}]")
                                    st.write(f"**Overall Risk Score:** {risk.overall_risk_score:.1f}")
                                    st.write(f"**Market Risk:** {risk.market_risk:.1f}")
                                    st.write(f"**Price Risk:** {risk.price_risk:.1f}")
                                    st.write(f"**Liquidity Risk:** {risk.liquidity_risk:.1f}")
                                    if risk.risk_factors:
                                        st.markdown("**Risk Factors:**")
                                        for rf in risk.risk_factors[:3]:
                                            st.write(f"- {rf}")

                                with col4:
                                    st.markdown("#### Investment Recommendation")
                                    rec = report.recommendation
                                    action_colors = {'STRONG BUY': 'green', 'BUY': 'blue', 'HOLD': 'orange', 'AVOID': 'red'}
                                    st.markdown(f"**Action:** :{action_colors.get(rec.action, 'gray')}[{rec.action}]")
                                    st.write(f"**Confidence:** {rec.confidence}")
                                    st.write(f"**Target Price:** ${rec.target_purchase_price:,.0f}")
                                    st.write(f"**Est. ARV:** ${rec.estimated_arv:,.0f}")
                                    st.write(f"**Est. Profit:** ${rec.estimated_profit:,.0f}")
                                    st.write(f"**Profit Margin:** {rec.profit_margin_pct:.1f}%")
                                    st.write(f"**Hold Period:** {rec.recommended_hold_period}")
                                    st.write(f"**Exit Strategy:** {rec.exit_strategy}")
                            else:
                                st.warning(f"Could not analyze ZIP {selected_zip}")
                        except Exception as e:
                            st.error(f"Analysis error: {str(e)}")
            else:
                st.info("No HOT alerts available for deep dive analysis.")

    # Footer
    st.markdown("---")
    st.markdown(
        "*Data source: Zillow Research | "
        "Dashboard built with Streamlit & Plotly*"
    )


if __name__ == "__main__":
    main()
