import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
import subprocess
import time

# Page config
st.set_page_config(
    page_title="Procurement Insights Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean Blue/White Theme CSS
st.markdown("""
<style>
    .main {
        background-color: #ffffff;
    }
    .stApp {
        max-width: 1600px;
        margin: 0 auto;
    }
    h1 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-weight: 600;
        color: #1a365d;
        border-bottom: 3px solid #3182ce;
        padding-bottom: 0.8rem;
        margin-bottom: 1rem;
    }
    h2 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-weight: 500;
        color: #2c5282;
    }
    h3 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        font-weight: 500;
        color: #2d3748;
    }
    .insight-card {
        border-left: 4px solid #3182ce;
        background-color: #f7fafc;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .insight-card-high {
        border-left-color: #e53e3e;
    }
    .insight-card-medium {
        border-left-color: #dd6b20;
    }
    .insight-card-low {
        border-left-color: #38a169;
    }
    .metric-container {
        background-color: #edf2f7;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #cbd5e0;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #4a5568;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2rem;
        color: #1a365d;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    .entity-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 500;
        margin-right: 0.5rem;
    }
    .badge-buyer {
        background-color: #bee3f8;
        color: #1a365d;
    }
    .badge-seller {
        background-color: #c6f6d5;
        color: #22543d;
    }
    .priority-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-high {
        background-color: #fed7d7;
        color: #742a2a;
    }
    .badge-medium {
        background-color: #feebc8;
        color: #7c2d12;
    }
    .badge-low {
        background-color: #c6f6d5;
        color: #22543d;
    }
    .comparison-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 3px;
        font-size: 0.7rem;
        font-weight: 500;
        margin-left: 0.5rem;
        background-color: #e6fffa;
        color: #234e52;
    }
    .section-divider {
        border-top: 2px solid #e2e8f0;
        margin: 2rem 0;
    }
    .stDataFrame {
        border: 1px solid #cbd5e0;
    }
    .generate-section {
        background-color: #edf2f7;
        padding: 2rem;
        border-radius: 8px;
        border: 1px solid #cbd5e0;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Paths
DASHBOARD_PROCESSED_DIR = Path("data/dashboard_data/processed")
TOTAL_DATA_DIR = Path("data/total_data")

def load_available_entities():
    """Load available entities from total_data files"""
    entities = {'buyer': [], 'seller': []}
    
    for entity_type in ['buyer', 'seller']:
        filepath = TOTAL_DATA_DIR / f"{entity_type}s_total.json"
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
                entities[entity_type] = sorted([int(eid) for eid in data['entities'].keys()])
    
    return entities

def run_pipeline(entity_type, entity_id, start_date, end_date):
    """Run the complete pipeline for an entity"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    from dashboard_executor import DashboardExecutor
    from insights_generator import BenchmarkingInsightsGenerator
    import config
    
    # Build parameters
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'top_n': config.DEFAULT_PARAMS[entity_type]['top_n']
    }
    
    try:
        # Step 1: Execute dashboard queries
        executor = DashboardExecutor()
        dashboard_file = executor.process_entity(entity_type, entity_id, params)
        
        # Step 2: Generate insights
        generator = BenchmarkingInsightsGenerator()
        insights_file = generator.generate_insights(dashboard_file)
        
        return insights_file, None
    
    except Exception as e:
        return None, str(e)

def load_latest_insight(entity_type, entity_id):
    """Load the most recent insight file for an entity"""
    pattern = f"{entity_type}_{entity_id}_insights_*.json"
    files = list(DASHBOARD_PROCESSED_DIR.glob(pattern))
    
    if not files:
        return None
    
    # Get most recent
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        return json.load(f)

def load_all_insights():
    """Load all processed insights"""
    if not DASHBOARD_PROCESSED_DIR.exists():
        return []
    
    files = list(DASHBOARD_PROCESSED_DIR.glob("*_insights_*.json"))
    insights = []
    
    for file in files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                insights.append(data)
        except Exception as e:
            st.error(f"Error loading {file.name}: {e}")
    
    return insights

def display_insight(insight):
    """Display a single insight"""
    priority = insight.get('priority', 'medium')
    title = insight.get('title', 'Insight')
    observation = insight.get('observation', 'N/A')
    recommendation = insight.get('recommendation', 'N/A')
    comparison_type = insight.get('comparison_type', 'N/A')
    
    card_class = f"insight-card insight-card-{priority}"
    badge_class = f"badge-{priority}"
    
    # Comparison type label
    comparison_labels = {
        'self': 'vs Historical',
        'benchmark': 'vs Platform',
        'both': 'Combined Analysis'
    }
    comparison_label = comparison_labels.get(comparison_type, comparison_type)
    
    st.markdown(f"""
    <div class="{card_class}">
        <div>
            <span class="priority-badge {badge_class}">{priority.upper()}</span>
            <span class="comparison-badge">{comparison_label}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #2d3748; margin-left: 0.5rem;">{title}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**📊 Observation**")
        st.write(observation)
    
    with col2:
        st.markdown("**💡 Recommendation**")
        st.info(recommendation)
    
    # Show metrics if available
    metrics = insight.get('metrics', [])
    if metrics:
        st.caption(f"**Related Metrics:** {', '.join(metrics)}")
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

def create_comparison_chart(insights):
    """Create chart showing comparison types"""
    comparison_counts = {'Self': 0, 'Benchmark': 0, 'Both': 0}
    
    for insight in insights:
        comp_type = insight.get('comparison_type', 'self')
        if comp_type == 'self':
            comparison_counts['Self'] += 1
        elif comp_type == 'benchmark':
            comparison_counts['Benchmark'] += 1
        elif comp_type == 'both':
            comparison_counts['Both'] += 1
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(comparison_counts.keys()),
            y=list(comparison_counts.values()),
            marker_color=['#3182ce', '#805ad5', '#38a169'],
            text=list(comparison_counts.values()),
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Insights by Comparison Type",
        xaxis_title="",
        yaxis_title="Count",
        showlegend=False,
        height=280,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Inter, Segoe UI, sans-serif", color="#2d3748"),
        title_font=dict(size=16, color="#1a365d")
    )
    
    fig.update_xaxes(showgrid=False, showline=True, linecolor='#cbd5e0')
    fig.update_yaxes(showgrid=True, gridcolor='#e2e8f0', showline=True, linecolor='#cbd5e0')
    
    return fig

# Main App
def main():
    # Header
    st.markdown('<h1>📊 Procurement Insights Platform</h1>', unsafe_allow_html=True)
    st.caption("AI-powered procurement analytics with benchmarking")
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 Navigation")
        
        mode = st.radio(
            "Select Mode",
            options=['Generate New Insights', 'View Existing Insights'],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if mode == 'View Existing Insights':
            entity_filter = st.selectbox(
                "Filter by Type",
                options=['All', 'Buyers Only', 'Sellers Only']
            )
        
        st.markdown("---")
        
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        st.caption("**Tip:** Generate insights for specific entities or browse all existing insights")
    
    # Mode 1: Generate New Insights
    if mode == 'Generate New Insights':
        st.markdown('<div class="generate-section">', unsafe_allow_html=True)
        st.markdown("### 🚀 Generate New Insights")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Load available entities
        available_entities = load_available_entities()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            entity_type = st.selectbox(
                "Entity Type",
                options=['buyer', 'seller'],
                format_func=lambda x: x.capitalize()
            )
        
        with col2:
            if available_entities[entity_type]:
                entity_id = st.selectbox(
                    "Entity ID",
                    options=available_entities[entity_type]
                )
            else:
                st.warning(f"No {entity_type}s available in total_data. Run populate_total_data.py first.")
                st.stop()
        
        st.markdown("#### Date Range")
        
        col3, col4, col5 = st.columns([1, 1, 1])
        
        with col3:
            preset = st.selectbox(
                "Quick Select",
                options=['Last 30 Days', 'Last 90 Days', 'Last 180 Days', 'Last 365 Days', 'Custom'],
                index=1  # Default to 90 days
            )
        
        if preset == 'Custom':
            with col4:
                start_date = st.date_input(
                    "Start Date",
                    value=datetime.now() - timedelta(days=90)
                )
            with col5:
                end_date = st.date_input(
                    "End Date",
                    value=datetime.now()
                )
        else:
            days_map = {
                'Last 30 Days': 30,
                'Last 90 Days': 90,
                'Last 180 Days': 180,
                'Last 365 Days': 365
            }
            days = days_map[preset]
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            
            with col4:
                st.info(f"**From:** {start_date.strftime('%Y-%m-%d')}")
            with col5:
                st.info(f"**To:** {end_date.strftime('%Y-%m-%d')}")
        
        st.markdown("")
        
        # Generate button
        if st.button("🎯 Generate Insights", type="primary", use_container_width=True):
            with st.spinner(f"Generating insights for {entity_type} {entity_id}..."):
                
                # Progress indicator
                progress_text = st.empty()
                
                progress_text.info("⏳ Step 1/2: Executing dashboard queries...")
                time.sleep(0.5)
                
                # Run pipeline
                insights_file, error = run_pipeline(
                    entity_type,
                    entity_id,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if error:
                    progress_text.empty()
                    st.error(f"❌ Error: {error}")
                    
                    if "402" in error or "credits" in error.lower():
                        st.warning("**OpenRouter Credits Issue:** Please add credits at https://openrouter.ai/settings/credits")
                    
                    st.stop()
                
                progress_text.success("✅ Step 1/2: Dashboard queries completed")
                time.sleep(0.5)
                
                progress_text.info("⏳ Step 2/2: Generating AI insights...")
                time.sleep(0.5)
                
                progress_text.success("✅ Step 2/2: Insights generated successfully!")
                time.sleep(1)
                
                progress_text.empty()
                
                st.success(f"✅ **Insights generated successfully for {entity_type} {entity_id}!**")
                
                # Auto-switch to view mode
                st.info("📊 **Scroll down to view the insights**")
        
        # Show latest insights if available
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        latest_insight = load_latest_insight(entity_type, entity_id)
        
        if latest_insight:
            st.markdown(f"### 📈 Latest Insights: {entity_type.capitalize()} {entity_id}")
            
            # Display insights
            display_insights_section(latest_insight)
    
    # Mode 2: View Existing Insights
    else:
        st.markdown("### 📚 All Generated Insights")
        
        all_insights = load_all_insights()
        
        if not all_insights:
            st.warning("No insights found. Generate some insights first!")
            st.stop()
        
        # Filter by entity type
        if entity_filter == 'Buyers Only':
            all_insights = [i for i in all_insights if i.get('entity_type') == 'buyer']
        elif entity_filter == 'Sellers Only':
            all_insights = [i for i in all_insights if i.get('entity_type') == 'seller']
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_entities = len(all_insights)
        total_insights_count = sum(i.get('insights_count', 0) for i in all_insights)
        high_priority_count = sum(i.get('high_priority_count', 0) for i in all_insights)
        avg_insights = total_insights_count / total_entities if total_entities > 0 else 0
        
        with col1:
            st.markdown(f'<div class="metric-container"><p class="metric-label">Total Entities</p><p class="metric-value">{total_entities}</p></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="metric-container"><p class="metric-label">Total Insights</p><p class="metric-value">{total_insights_count}</p></div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="metric-container"><p class="metric-label">High Priority</p><p class="metric-value">{high_priority_count}</p></div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown(f'<div class="metric-container"><p class="metric-label">Avg per Entity</p><p class="metric-value">{avg_insights:.1f}</p></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Entity selector
        entities_list = [f"{i['entity_type'].capitalize()} {i['entity_id']} ({i['insights_count']} insights)" 
                        for i in all_insights]
        
        selected_index = st.selectbox(
            "Select Entity",
            range(len(entities_list)),
            format_func=lambda i: entities_list[i]
        )
        
        selected_insight_data = all_insights[selected_index]
        
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        
        # Display selected insights
        display_insights_section(selected_insight_data)
    
    # Footer
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def display_insights_section(data):
    """Display insights section with metrics and insights"""
    entity_type = data.get('entity_type', 'unknown')
    entity_id = data.get('entity_id', 'N/A')
    
    # Header
    badge_class = 'badge-buyer' if entity_type == 'buyer' else 'badge-seller'
    st.markdown(f'<h2><span class="entity-badge {badge_class}">{entity_type.upper()}</span> Entity {entity_id}</h2>', unsafe_allow_html=True)
    
    # Period info
    period = data.get('dashboard_period', {})
    st.caption(f"**Dashboard Period:** {period.get('start_date', 'N/A')} to {period.get('end_date', 'N/A')}")
    
    baseline = data.get('baseline_period') or data.get('total_data_version', 'N/A')
    if baseline:
        st.caption(f"**Baseline Data:** {baseline}")
    
    st.markdown("")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    insights = data.get('insights', [])
    insights_count = data.get('insights_count', len(insights))
    high_count = data.get('high_priority_count', 0)
    comparison_types = data.get('comparison_types', {})
    
    with col1:
        st.metric("Total Insights", insights_count)
    
    with col2:
        st.metric("High Priority", high_count)
    
    with col3:
        self_count = comparison_types.get('self', 0)
        st.metric("Self-Comparison", self_count)
    
    with col4:
        benchmark_count = comparison_types.get('benchmark', 0) + comparison_types.get('both', 0)
        st.metric("With Benchmark", benchmark_count)
    
    st.markdown("")
    
    # Comparison chart
    if insights:
        chart = create_comparison_chart(insights)
        st.plotly_chart(chart, use_container_width=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Insights
    if insights:
        # Filter
        filter_priority = st.radio(
            "Filter by priority",
            options=['All', 'High', 'Medium', 'Low'],
            horizontal=True
        )
        
        filter_comparison = st.radio(
            "Filter by comparison type",
            options=['All', 'Self', 'Benchmark', 'Both'],
            horizontal=True
        )
        
        st.markdown("")
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_insights = sorted(
            insights,
            key=lambda x: priority_order.get(x.get('priority', 'medium'), 1)
        )
        
        # Apply filters
        if filter_priority != 'All':
            sorted_insights = [
                i for i in sorted_insights 
                if i.get('priority', 'medium').capitalize() == filter_priority
            ]
        
        if filter_comparison != 'All':
            sorted_insights = [
                i for i in sorted_insights 
                if i.get('comparison_type', 'self').capitalize() == filter_comparison.lower()
            ]
        
        if sorted_insights:
            for insight in sorted_insights:
                display_insight(insight)
        else:
            st.info("No insights match the selected filters")
        
        # Download button
        json_data = json.dumps(data, indent=2)
        st.download_button(
            label="📥 Download Insights (JSON)",
            data=json_data,
            file_name=f"{entity_type}_{entity_id}_insights.json",
            mime="application/json"
        )
    else:
        st.info("No insights available for this entity")

if __name__ == "__main__":
    main()