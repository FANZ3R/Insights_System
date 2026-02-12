# import streamlit as st
# import json
# import pandas as pd
# from datetime import datetime
# from pathlib import Path
# import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots

# # Page config
# st.set_page_config(
#     page_title="Procurement AI Insights",
#     page_icon="📊",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS for better UI
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 3rem;
#         font-weight: bold;
#         background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
#         -webkit-background-clip: text;
#         -webkit-text-fill-color: transparent;
#         margin-bottom: 0.5rem;
#     }
#     .metric-card {
#         background-color: #f0f2f6;
#         padding: 1.5rem;
#         border-radius: 0.5rem;
#         border-left: 4px solid #667eea;
#     }
#     .insight-high {
#         border-left: 4px solid #ff4b4b;
#         background-color: #fff5f5;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin-bottom: 1rem;
#     }
#     .insight-medium {
#         border-left: 4px solid #ffa500;
#         background-color: #fff9f0;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin-bottom: 1rem;
#     }
#     .insight-low {
#         border-left: 4px solid #00c853;
#         background-color: #f0fff4;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin-bottom: 1rem;
#     }
#     .stTabs [data-baseweb="tab-list"] {
#         gap: 2rem;
#     }
#     .stTabs [data-baseweb="tab"] {
#         height: 3rem;
#         padding-left: 2rem;
#         padding-right: 2rem;
#     }
# </style>
# """, unsafe_allow_html=True)

# # Paths
# PROCESSED_DATA_DIR = Path("data/processed")
# RAW_DATA_DIR = Path("data/raw")

# def load_all_insights(entity_type=None):
#     """Load all processed insights from directory"""
#     if not PROCESSED_DATA_DIR.exists():
#         return []
    
#     pattern = f"{entity_type}_*_insights_*.json" if entity_type else "*_insights_*.json"
#     files = list(PROCESSED_DATA_DIR.glob(pattern))
    
#     insights = []
#     for file in files:
#         try:
#             with open(file, 'r') as f:
#                 data = json.load(f)
#                 insights.append(data)
#         except Exception as e:
#             st.error(f"Error loading {file.name}: {e}")
    
#     return insights

# def get_entity_summary(insights_list):
#     """Create summary dataframe from insights"""
#     if not insights_list:
#         return pd.DataFrame()
    
#     summaries = []
#     for insight in insights_list:
#         entity_type = insight.get('entity_type')
#         entity_id = insight.get('entity_id')
#         insights_count = insight.get('insights_count', 0)
#         high_priority = insight.get('high_priority_count', 0)
        
#         # Get data period
#         period = insight.get('data_period', {})
        
#         summaries.append({
#             'Entity Type': entity_type.capitalize(),
#             'Entity ID': entity_id,
#             'Total Insights': insights_count,
#             'High Priority': high_priority,
#             'Period Start': period.get('start', 'N/A'),
#             'Period End': period.get('end', 'N/A'),
#             'Generated At': insight.get('generated_at', 'N/A')[:10]
#         })
    
#     return pd.DataFrame(summaries)

# def display_insight_card(insight, index):
#     """Display a single insight as a styled card"""
#     priority = insight.get('priority', 'medium')
#     title = insight.get('title', 'Insight')
#     observation = insight.get('observation', 'N/A')
#     recommendation = insight.get('recommendation', 'N/A')
#     metrics = insight.get('metrics', [])
    
#     # Priority badge
#     priority_colors = {
#         'high': '🔴',
#         'medium': '🟡',
#         'low': '🟢'
#     }
    
#     badge = priority_colors.get(priority, '⚪')
    
#     with st.container():
#         st.markdown(f"""
#         <div class="insight-{priority}">
#             <h4>{badge} {title}</h4>
#         </div>
#         """, unsafe_allow_html=True)
        
#         col1, col2 = st.columns([3, 1])
        
#         with col1:
#             st.markdown("**📊 Observation:**")
#             st.write(observation)
            
#             st.markdown("**💡 Recommendation:**")
#             st.info(recommendation)
        
#         with col2:
#             st.markdown("**Priority:**")
#             st.write(priority.upper())
            
#             if metrics:
#                 st.markdown("**Metrics:**")
#                 for metric in metrics[:3]:
#                     st.caption(f"• {metric}")

# def create_insights_distribution_chart(insights_list):
#     """Create chart showing insights distribution"""
#     priority_counts = {'high': 0, 'medium': 0, 'low': 0}
    
#     for item in insights_list:
#         for insight in item.get('insights', []):
#             priority = insight.get('priority', 'medium')
#             priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
#     fig = go.Figure(data=[
#         go.Bar(
#             x=list(priority_counts.keys()),
#             y=list(priority_counts.values()),
#             marker_color=['#ff4b4b', '#ffa500', '#00c853'],
#             text=list(priority_counts.values()),
#             textposition='auto',
#         )
#     ])
    
#     fig.update_layout(
#         title="Insights Priority Distribution",
#         xaxis_title="Priority Level",
#         yaxis_title="Count",
#         showlegend=False,
#         height=300
#     )
    
#     return fig

# def create_entity_comparison_chart(summary_df, entity_type):
#     """Create comparison chart for entities"""
#     if summary_df.empty:
#         return None
    
#     fig = go.Figure()
    
#     fig.add_trace(go.Bar(
#         x=summary_df['Entity ID'],
#         y=summary_df['Total Insights'],
#         name='Total Insights',
#         marker_color='lightblue'
#     ))
    
#     fig.add_trace(go.Bar(
#         x=summary_df['Entity ID'],
#         y=summary_df['High Priority'],
#         name='High Priority',
#         marker_color='salmon'
#     ))
    
#     fig.update_layout(
#         title=f"{entity_type.capitalize()} Insights Overview",
#         xaxis_title=f"{entity_type.capitalize()} ID",
#         yaxis_title="Count",
#         barmode='group',
#         height=400
#     )
    
#     return fig

# # Main App
# def main():
#     # Header
#     st.markdown('<p class="main-header">📊 Procurement AI Insights</p>', unsafe_allow_html=True)
#     st.markdown("**AI-powered insights for buyers and sellers**")
#     st.markdown("---")
    
#     # Sidebar
#     with st.sidebar:
#         st.image("https://via.placeholder.com/150x50/667eea/FFFFFF?text=AI+Insights", use_container_width=True)
        
#         st.header("🎛️ Controls")
        
#         # Entity type selector
#         entity_type = st.radio(
#             "Select Entity Type",
#             options=['All', 'Buyer', 'Seller'],
#             horizontal=True
#         )
        
#         entity_filter = None if entity_type == 'All' else entity_type.lower()
        
#         st.markdown("---")
        
#         # Refresh button
#         if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
#             st.cache_data.clear()
#             st.rerun()
        
#         st.markdown("---")
        
#         # Info
#         st.info("💡 **Tip:** Select an entity from the table below to view detailed insights.")
        
#         st.markdown("---")
#         st.caption("Powered by Claude AI")
    
#     # Load insights
#     with st.spinner('Loading insights...'):
#         insights_list = load_all_insights(entity_filter)
    
#     if not insights_list:
#         st.warning("⚠️ No insights found. Please run the insights generation system first.")
#         st.code("""
# # Generate insights:
# cd insights_system/src
# python query_executor.py --entity buyer --id 534
# python insights_generator.py --entity buyer --id 534
#         """)
#         st.stop()
    
#     # Summary metrics
#     st.header("📈 Overview")
    
#     col1, col2, col3, col4 = st.columns(4)
    
#     total_entities = len(insights_list)
#     total_insights = sum(item.get('insights_count', 0) for item in insights_list)
#     high_priority_insights = sum(item.get('high_priority_count', 0) for item in insights_list)
#     avg_insights_per_entity = total_insights / total_entities if total_entities > 0 else 0
    
#     with col1:
#         st.metric(
#             label="Total Entities",
#             value=total_entities,
#             delta=f"{entity_type if entity_type != 'All' else 'Mixed'}"
#         )
    
#     with col2:
#         st.metric(
#             label="Total Insights",
#             value=total_insights
#         )
    
#     with col3:
#         st.metric(
#             label="High Priority",
#             value=high_priority_insights,
#             delta=f"{(high_priority_insights/total_insights*100):.1f}%" if total_insights > 0 else "0%"
#         )
    
#     with col4:
#         st.metric(
#             label="Avg Insights/Entity",
#             value=f"{avg_insights_per_entity:.1f}"
#         )
    
#     st.markdown("---")
    
#     # Charts
#     col1, col2 = st.columns(2)
    
#     with col1:
#         # Priority distribution
#         priority_chart = create_insights_distribution_chart(insights_list)
#         st.plotly_chart(priority_chart, use_container_width=True)
    
#     with col2:
#         # Entity comparison
#         summary_df = get_entity_summary(insights_list)
#         if not summary_df.empty:
#             entity_chart = create_entity_comparison_chart(
#                 summary_df, 
#                 entity_type if entity_type != 'All' else 'entity'
#             )
#             if entity_chart:
#                 st.plotly_chart(entity_chart, use_container_width=True)
    
#     st.markdown("---")
    
#     # Entity selector and details
#     st.header("🔍 Entity Details")
    
#     # Summary table
#     if not summary_df.empty:
#         # Sort by high priority count
#         summary_df_sorted = summary_df.sort_values('High Priority', ascending=False)
        
#         # Display table with selection
#         st.dataframe(
#             summary_df_sorted,
#             use_container_width=True,
#             hide_index=True
#         )
        
#         # Entity selector
#         selected_entity_id = st.selectbox(
#             "Select Entity for Detailed View",
#             options=summary_df['Entity ID'].tolist(),
#             format_func=lambda x: f"{summary_df[summary_df['Entity ID']==x]['Entity Type'].values[0]} {x} - {summary_df[summary_df['Entity ID']==x]['Total Insights'].values[0]} insights ({summary_df[summary_df['Entity ID']==x]['High Priority'].values[0]} high priority)"
#         )
        
#         # Get selected entity data
#         selected_entity = next(
#             (item for item in insights_list if item['entity_id'] == selected_entity_id),
#             None
#         )
        
#         if selected_entity:
#             st.markdown("---")
            
#             # Entity header
#             entity_type_label = selected_entity['entity_type'].capitalize()
#             st.subheader(f"{entity_type_label} {selected_entity_id}")
            
#             # Metadata
#             col1, col2, col3 = st.columns(3)
            
#             with col1:
#                 period = selected_entity.get('data_period', {})
#                 st.info(f"**Period:** {period.get('start', 'N/A')} to {period.get('end', 'N/A')}")
            
#             with col2:
#                 generated = selected_entity.get('generated_at', 'N/A')
#                 st.info(f"**Generated:** {generated[:10] if generated != 'N/A' else 'N/A'}")
            
#             with col3:
#                 queries = selected_entity.get('raw_data_summary', {})
#                 st.info(f"**Data Sources:** {len(queries)} queries")
            
#             # Data quality summary
#             with st.expander("📊 Data Quality Summary", expanded=False):
#                 queries_summary = selected_entity.get('raw_data_summary', {})
                
#                 if queries_summary:
#                     quality_df = pd.DataFrame([
#                         {
#                             'Query': name,
#                             'Description': info.get('description', 'N/A'),
#                             'Records': info.get('result_count', 0)
#                         }
#                         for name, info in queries_summary.items()
#                     ])
#                     st.dataframe(quality_df, use_container_width=True, hide_index=True)
#                 else:
#                     st.write("No query summary available")
            
#             st.markdown("---")
            
#             # Insights tabs
#             insights = selected_entity.get('insights', [])
            
#             if insights:
#                 # Sort insights by priority
#                 priority_order = {'high': 0, 'medium': 1, 'low': 2}
#                 sorted_insights = sorted(
#                     insights,
#                     key=lambda x: priority_order.get(x.get('priority', 'medium'), 1)
#                 )
                
#                 # Create tabs for different views
#                 tab1, tab2, tab3 = st.tabs(["🎯 All Insights", "🔴 High Priority", "📋 Summary"])
                
#                 with tab1:
#                     st.subheader("All AI-Generated Insights")
#                     for idx, insight in enumerate(sorted_insights, 1):
#                         display_insight_card(insight, idx)
                
#                 with tab2:
#                     st.subheader("High Priority Insights")
#                     high_priority = [i for i in sorted_insights if i.get('priority') == 'high']
                    
#                     if high_priority:
#                         for idx, insight in enumerate(high_priority, 1):
#                             display_insight_card(insight, idx)
#                     else:
#                         st.info("No high priority insights found")
                
#                 with tab3:
#                     st.subheader("Insights Summary")
                    
#                     # Create summary table
#                     summary_data = []
#                     for insight in sorted_insights:
#                         summary_data.append({
#                             'Priority': insight.get('priority', 'medium').upper(),
#                             'Title': insight.get('title', 'N/A'),
#                             'Metrics': len(insight.get('metrics', []))
#                         })
                    
#                     summary_table = pd.DataFrame(summary_data)
#                     st.dataframe(summary_table, use_container_width=True, hide_index=True)
                    
#                     # Download button
#                     json_data = json.dumps(selected_entity, indent=2)
#                     st.download_button(
#                         label="📥 Download Insights (JSON)",
#                         data=json_data,
#                         file_name=f"{entity_type_label.lower()}_{selected_entity_id}_insights.json",
#                         mime="application/json",
#                         use_container_width=True
#                     )
#             else:
#                 st.warning("No insights available for this entity")
    
#     # Footer
#     st.markdown("---")
#     st.caption(f"Dashboard last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# if __name__ == "__main__":
#     main()








































import streamlit as st
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Procurement Insights Platform",
    page_icon="chart_with_upwards_trend",
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
    .section-divider {
        border-top: 2px solid #e2e8f0;
        margin: 2rem 0;
    }
    .stDataFrame {
        border: 1px solid #cbd5e0;
    }
</style>
""", unsafe_allow_html=True)

# Paths
PROCESSED_DATA_DIR = Path("data/processed")

def load_all_insights():
    """Load all processed insights and group by entity ID"""
    if not PROCESSED_DATA_DIR.exists():
        return {}
    
    files = list(PROCESSED_DATA_DIR.glob("*_insights_*.json"))
    
    # Group insights by entity_id
    entities = {}
    
    for file in files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                
            entity_id = data.get('entity_id')
            entity_type = data.get('entity_type')
            
            if entity_id not in entities:
                entities[entity_id] = {
                    'entity_id': entity_id,
                    'buyer': None,
                    'seller': None
                }
            
            entities[entity_id][entity_type] = data
            
        except Exception as e:
            st.error(f"Error loading {file.name}: {e}")
    
    return entities

def get_entity_summary(entities):
    """Create summary dataframe from entities"""
    if not entities:
        return pd.DataFrame()
    
    summaries = []
    for entity_id, data in entities.items():
        buyer_data = data.get('buyer')
        seller_data = data.get('seller')
        
        roles = []
        total_insights = 0
        high_priority = 0
        
        if buyer_data:
            roles.append('Buyer')
            total_insights += buyer_data.get('insights_count', 0)
            high_priority += buyer_data.get('high_priority_count', 0)
        
        if seller_data:
            roles.append('Seller')
            total_insights += seller_data.get('insights_count', 0)
            high_priority += seller_data.get('high_priority_count', 0)
        
        summaries.append({
            'Entity ID': entity_id,
            'Roles': ' + '.join(roles),
            'Total Insights': total_insights,
            'High Priority': high_priority
        })
    
    return pd.DataFrame(summaries)

def display_insight(insight, entity_type):
    """Display a single insight"""
    priority = insight.get('priority', 'medium')
    title = insight.get('title', 'Insight')
    observation = insight.get('observation', 'N/A')
    recommendation = insight.get('recommendation', 'N/A')
    
    card_class = f"insight-card insight-card-{priority}"
    badge_class = f"badge-{priority}"
    
    st.markdown(f"""
    <div class="{card_class}">
        <div>
            <span class="priority-badge {badge_class}">{priority.upper()}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #2d3748; margin-left: 0.5rem;">{title}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Observation**")
        st.write(observation)
    
    with col2:
        st.markdown("**Recommendation**")
        st.info(recommendation)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

def create_simple_bar_chart(data_dict, title):
    """Create a simple bar chart"""
    fig = go.Figure(data=[
        go.Bar(
            x=list(data_dict.keys()),
            y=list(data_dict.values()),
            marker_color='#3182ce',
            text=list(data_dict.values()),
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title=title,
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
    st.markdown('<h1>Procurement Insights Platform</h1>', unsafe_allow_html=True)
    st.caption("AI-powered procurement analytics for buyers and sellers")
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Filters")
        
        entity_filter = st.selectbox(
            "View Mode",
            options=['All Entities', 'Buyers Only', 'Sellers Only']
        )
        
        st.markdown("---")
        
        if st.button("Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.caption("Select an entity from the table to view detailed insights")
    
    # Load insights
    entities = load_all_insights()
    
    # Filter entities based on selection
    filtered_entities = {}
    for entity_id, data in entities.items():
        if entity_filter == 'Buyers Only' and not data.get('buyer'):
            continue
        if entity_filter == 'Sellers Only' and not data.get('seller'):
            continue
        filtered_entities[entity_id] = data
    
    if not filtered_entities:
        st.warning("No insights found. Please generate insights first.")
        st.code("""
cd insights_system/src
python run_all.py --limit 10
        """)
        st.stop()
    
    # Summary metrics
    st.markdown("### Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_entities = len(filtered_entities)
    total_buyers = sum(1 for d in filtered_entities.values() if d.get('buyer'))
    total_sellers = sum(1 for d in filtered_entities.values() if d.get('seller'))
    
    total_insights = 0
    high_priority_insights = 0
    for data in filtered_entities.values():
        for entity_data in [data.get('buyer'), data.get('seller')]:
            if entity_data:
                total_insights += entity_data.get('insights_count', 0)
                high_priority_insights += entity_data.get('high_priority_count', 0)
    
    with col1:
        st.markdown(f'<div class="metric-container"><p class="metric-label">Total Entities</p><p class="metric-value">{total_entities}</p></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="metric-container"><p class="metric-label">Buyers / Sellers</p><p class="metric-value">{total_buyers} / {total_sellers}</p></div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'<div class="metric-container"><p class="metric-label">Total Insights</p><p class="metric-value">{total_insights}</p></div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'<div class="metric-container"><p class="metric-label">High Priority</p><p class="metric-value">{high_priority_insights}</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Priority distribution chart
    priority_counts = {'High': 0, 'Medium': 0, 'Low': 0}
    for data in filtered_entities.values():
        for entity_data in [data.get('buyer'), data.get('seller')]:
            if entity_data:
                for insight in entity_data.get('insights', []):
                    priority = insight.get('priority', 'medium').capitalize()
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
    
    if any(priority_counts.values()):
        chart = create_simple_bar_chart(priority_counts, "Insights by Priority Level")
        st.plotly_chart(chart, use_container_width=True)
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    # Entity list
    st.markdown("### Entities")
    
    summary_df = get_entity_summary(filtered_entities)
    
    if not summary_df.empty:
        summary_df_sorted = summary_df.sort_values('High Priority', ascending=False)
        
        st.dataframe(
            summary_df_sorted,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("")
        
        # Entity selector
        selected_entity_id = st.selectbox(
            "Select Entity for Detailed Analysis",
            options=summary_df['Entity ID'].tolist(),
            format_func=lambda x: f"Entity {x} ({summary_df[summary_df['Entity ID']==x]['Roles'].values[0]}) - {summary_df[summary_df['Entity ID']==x]['Total Insights'].values[0]} insights"
        )
        
        # Get selected entity data
        selected_entity = filtered_entities.get(selected_entity_id)
        
        if selected_entity:
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            
            # Entity header
            buyer_data = selected_entity.get('buyer')
            seller_data = selected_entity.get('seller')
            
            badges_html = ""
            if buyer_data:
                badges_html += '<span class="entity-badge badge-buyer">BUYER</span>'
            if seller_data:
                badges_html += '<span class="entity-badge badge-seller">SELLER</span>'
            
            st.markdown(f'<h2>Entity {selected_entity_id} {badges_html}</h2>', unsafe_allow_html=True)
            
            # Show insights for each role
            if buyer_data:
                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
                st.markdown("### Buyer Insights")
                
                period = buyer_data.get('data_period', {})
                st.caption(f"Analysis Period: {period.get('start', 'N/A')} to {period.get('end', 'N/A')}")
                
                buyer_insights = buyer_data.get('insights', [])
                
                if buyer_insights:
                    # Filter options
                    filter_priority = st.radio(
                        "Filter buyer insights by priority",
                        options=['All', 'High', 'Medium', 'Low'],
                        horizontal=True,
                        key='buyer_filter'
                    )
                    
                    st.markdown("")
                    
                    # Sort by priority
                    priority_order = {'high': 0, 'medium': 1, 'low': 2}
                    sorted_insights = sorted(
                        buyer_insights,
                        key=lambda x: priority_order.get(x.get('priority', 'medium'), 1)
                    )
                    
                    # Filter
                    if filter_priority != 'All':
                        sorted_insights = [
                            i for i in sorted_insights 
                            if i.get('priority', 'medium').capitalize() == filter_priority
                        ]
                    
                    if sorted_insights:
                        for insight in sorted_insights:
                            display_insight(insight, 'buyer')
                    else:
                        st.info(f"No {filter_priority.lower()} priority buyer insights")
                    
                    # Download button
                    json_data = json.dumps(buyer_data, indent=2)
                    st.download_button(
                        label="Download Buyer Insights (JSON)",
                        data=json_data,
                        file_name=f"buyer_{selected_entity_id}_insights.json",
                        mime="application/json"
                    )
                else:
                    st.info("No buyer insights available")
            
            if seller_data:
                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
                st.markdown("### Seller Insights")
                
                period = seller_data.get('data_period', {})
                st.caption(f"Analysis Period: {period.get('start', 'N/A')} to {period.get('end', 'N/A')}")
                
                seller_insights = seller_data.get('insights', [])
                
                if seller_insights:
                    # Filter options
                    filter_priority = st.radio(
                        "Filter seller insights by priority",
                        options=['All', 'High', 'Medium', 'Low'],
                        horizontal=True,
                        key='seller_filter'
                    )
                    
                    st.markdown("")
                    
                    # Sort by priority
                    priority_order = {'high': 0, 'medium': 1, 'low': 2}
                    sorted_insights = sorted(
                        seller_insights,
                        key=lambda x: priority_order.get(x.get('priority', 'medium'), 1)
                    )
                    
                    # Filter
                    if filter_priority != 'All':
                        sorted_insights = [
                            i for i in sorted_insights 
                            if i.get('priority', 'medium').capitalize() == filter_priority
                        ]
                    
                    if sorted_insights:
                        for insight in sorted_insights:
                            display_insight(insight, 'seller')
                    else:
                        st.info(f"No {filter_priority.lower()} priority seller insights")
                    
                    # Download button
                    json_data = json.dumps(seller_data, indent=2)
                    st.download_button(
                        label="Download Seller Insights (JSON)",
                        data=json_data,
                        file_name=f"seller_{selected_entity_id}_insights.json",
                        mime="application/json"
                    )
                else:
                    st.info("No seller insights available")
    
    # Footer
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()