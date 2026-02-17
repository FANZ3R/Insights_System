import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go
import time

st.set_page_config(
    page_title="Vipani Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700;800&family=Barlow+Condensed:wght@400;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Barlow', sans-serif !important;
        background-color: #0a0a0a !important;
        color: #e8e0d8 !important;
    }
    .main .block-container {
        padding: 2rem 2.5rem 3rem 2.5rem !important;
        max-width: 1400px !important;
        background-color: #0a0a0a !important;
    }
    p, span, div, label, h1, h2, h3, h4, li, small {
        color: #e8e0d8 !important;
    }
    .stMarkdown p, .stMarkdown span { color: #e8e0d8 !important; }

    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background: #0f0f0f !important;
        border-right: 1px solid #1e1010 !important;
    }
    [data-testid="stSidebar"] * { color: #e8e0d8 !important; font-family: 'Barlow', sans-serif !important; }
    [data-testid="stSidebar"] .stRadio label { font-size: 0.9rem !important; font-weight: 500 !important; }

    /* RADIO */
    .stRadio > div > label {
        background: #161616 !important;
        border: 1px solid #2a1a1a !important;
        border-radius: 4px !important;
        padding: 0.4rem 0.9rem !important;
        margin-bottom: 0.3rem !important;
    }
    .stRadio > div > label:hover { border-color: #c0392b !important; }
    [data-baseweb="radio"] input:checked ~ div { background-color: #c0392b !important; }

    /* SELECTBOX */
    .stSelectbox label {
        color: #6b5b55 !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    .stSelectbox > div > div {
        background-color: #161616 !important;
        border: 1px solid #2a1a1a !important;
        color: #e8e0d8 !important;
        border-radius: 4px !important;
    }
    .stSelectbox > div > div:hover { border-color: #c0392b !important; }
    .stSelectbox > div > div > div { color: #e8e0d8 !important; }

    /* BUTTONS */
    .stButton > button {
        background: #c0392b !important;
        color: white !important;
        border: none !important;
        border-radius: 3px !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        padding: 0.55rem 1.5rem !important;
    }
    .stButton > button:hover {
        background: #e74c3c !important;
        box-shadow: 0 4px 20px rgba(192,57,43,0.4) !important;
    }
    .stButton > button p, .stButton > button span { color: white !important; }

    /* METRICS */
    div[data-testid="stMetricValue"] {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #e8e0d8 !important;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.68rem !important;
        color: #6b5b55 !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    [data-testid="stMetricContainer"] {
        background: #111111 !important;
        border: 1px solid #1e1010 !important;
        border-top: 2px solid #c0392b !important;
        border-radius: 4px !important;
        padding: 1rem 1.25rem !important;
    }

    /* HR */
    hr { border: none !important; border-top: 1px solid #1e1010 !important; margin: 1.5rem 0 !important; }

    /* ALERTS */
    .stAlert { background: #161616 !important; border: 1px solid #2a1a1a !important; border-radius: 4px !important; }
    .stAlert p, [data-testid="stInfoAlertContent"] { color: #e8e0d8 !important; }
    .stCaption, [data-testid="stCaptionContainer"] p { color: #6b5b55 !important; font-size: 0.78rem !important; }

    /* DOWNLOAD BUTTON */
    .stDownloadButton > button {
        background: transparent !important;
        color: #c0392b !important;
        border: 1px solid #c0392b !important;
        border-radius: 3px !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    .stDownloadButton > button:hover { background: #c0392b !important; color: white !important; }
    .stDownloadButton > button p { color: inherit !important; }

    /* CUSTOM COMPONENTS */
    .vp-header {
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid #1e1010;
        margin-bottom: 1.5rem;
    }
    .vp-logo {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
        color: #e8e0d8 !important;
    }
    .section-label {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.18em !important;
        text-transform: uppercase !important;
        color: #c0392b !important;
        margin-bottom: 1rem !important;
    }
    .insight-block {
        background: #111111;
        border: 1px solid #1e1010;
        border-left: 3px solid #2a1010;
        border-radius: 4px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.75rem;
    }
    .insight-high   { border-left-color: #c0392b !important; }
    .insight-medium { border-left-color: #e67e22 !important; }
    .insight-low    { border-left-color: #27ae60 !important; }
    .insight-title {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: #e8e0d8 !important;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.15rem 0.5rem;
        border-radius: 2px;
        font-size: 0.65rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-family: 'Barlow Condensed', sans-serif !important;
        margin-right: 0.35rem;
    }
    .badge-high     { background: rgba(192,57,43,0.2); color: #e74c3c !important; border: 1px solid rgba(192,57,43,0.35); }
    .badge-medium   { background: rgba(230,126,34,0.15); color: #e67e22 !important; border: 1px solid rgba(230,126,34,0.3); }
    .badge-low      { background: rgba(39,174,96,0.15); color: #27ae60 !important; border: 1px solid rgba(39,174,96,0.3); }
    .badge-self     { background: rgba(52,152,219,0.1); color: #3498db !important; border: 1px solid rgba(52,152,219,0.2); }
    .badge-benchmark { background: rgba(155,89,182,0.1); color: #9b59b6 !important; border: 1px solid rgba(155,89,182,0.2); }
    .badge-both     { background: rgba(192,57,43,0.1); color: #c0392b !important; border: 1px solid rgba(192,57,43,0.2); }
    .entity-tag {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 2px;
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
    }
    .entity-buyer  { background: rgba(192,57,43,0.15); color: #e74c3c !important; border: 1px solid rgba(192,57,43,0.3); }
    .entity-seller { background: rgba(39,174,96,0.1); color: #27ae60 !important; border: 1px solid rgba(39,174,96,0.25); }
    .db-ok {
        background: rgba(39,174,96,0.07); border: 1px solid rgba(39,174,96,0.2);
        border-radius: 4px; padding: 0.75rem 1rem; font-size: 0.8rem;
    }
    .db-err {
        background: rgba(192,57,43,0.07); border: 1px solid rgba(192,57,43,0.25);
        border-radius: 4px; padding: 0.75rem 1rem; font-size: 0.8rem; color: #e74c3c !important;
    }
    .gen-panel {
        background: #111111; border: 1px solid #1e1010;
        border-radius: 4px; padding: 1.5rem; margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

DASHBOARD_PROCESSED_DIR = Path("data/dashboard_data/processed")


def load_available_entities():
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    import duckdb, config
    entities = {'buyer': [], 'seller': []}
    if not Path(config.ANALYTICS_DB_PATH).exists():
        return entities
    try:
        conn = duckdb.connect(config.ANALYTICS_DB_PATH, read_only=True)
        for et in ['buyer', 'seller']:
            rows = conn.execute(
                "SELECT DISTINCT entity_id FROM entities WHERE entity_type=? ORDER BY entity_id", [et]
            ).fetchall()
            entities[et] = [r[0] for r in rows]
        conn.close()
    except:
        pass
    return entities


def get_db_status():
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    try:
        import duckdb, config
        if not Path(config.ANALYTICS_DB_PATH).exists():
            return None
        conn = duckdb.connect(config.ANALYTICS_DB_PATH, read_only=True)
        b = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type='buyer'").fetchone()[0]
        s = conn.execute("SELECT COUNT(*) FROM entities WHERE entity_type='seller'").fetchone()[0]
        last = conn.execute("SELECT synced_at FROM sync_log ORDER BY synced_at DESC LIMIT 1").fetchone()
        conn.close()
        return {'buyers': b, 'sellers': s, 'last_sync': str(last[0])[:16] if last else None}
    except:
        return None


def run_pipeline(entity_type, entity_id, start_date, end_date):
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from dashboard_executor import DashboardExecutor
    from insights_generator import BenchmarkingInsightsGenerator
    import config
    params = {
        'start_date': start_date, 'end_date': end_date,
        'top_n': config.DEFAULT_PARAMS[entity_type]['top_n']
    }
    try:
        executor = DashboardExecutor()
        dashboard_file = executor.process_entity(entity_type, entity_id, params)
        generator = BenchmarkingInsightsGenerator()
        insights_file = generator.generate_insights(dashboard_file)
        return insights_file, None
    except Exception as e:
        return None, str(e)


def load_latest_insight(entity_type, entity_id):
    pattern = f"{entity_type}_{entity_id}_insights_*.json"
    files = list(DASHBOARD_PROCESSED_DIR.glob(pattern))
    if not files:
        return None
    latest = max(files, key=lambda f: f.stat().st_mtime)
    with open(latest) as f:
        return json.load(f)


def load_all_insights():
    if not DASHBOARD_PROCESSED_DIR.exists():
        return []
    result = []
    for file in DASHBOARD_PROCESSED_DIR.glob("*_insights_*.json"):
        try:
            with open(file) as f:
                result.append(json.load(f))
        except:
            pass
    return result


def section_label(text):
    st.markdown(
        f'<div class="section-label">{text}</div>',
        unsafe_allow_html=True
    )


def render_insight(insight):
    priority = insight.get('priority', 'medium')
    comp_type = insight.get('comparison_type', 'self')
    title = insight.get('title', 'Insight')
    observation = insight.get('observation', '')
    recommendation = insight.get('recommendation', '')
    metrics = insight.get('metrics', [])
    comp_labels = {'self': 'vs Historical', 'benchmark': 'vs Platform', 'both': 'Combined'}
    comp_label = comp_labels.get(comp_type, comp_type)

    st.markdown(f"""
    <div class="insight-block insight-{priority}">
        <div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.6rem;">
            <span class="badge badge-{priority}">{priority}</span>
            <span class="badge badge-{comp_type}">{comp_label}</span>
        </div>
        <div class="insight-title">{title}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#3d2d2d;margin-bottom:0.3rem;">Observation</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:0.875rem;color:#9a8a80;line-height:1.6;">{observation}</p>', unsafe_allow_html=True)
    with col2:
        st.markdown('<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#3d2d2d;margin-bottom:0.3rem;">Recommendation</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:0.875rem;color:#c0392b;line-height:1.6;">{recommendation}</p>', unsafe_allow_html=True)

    if metrics:
        st.markdown(f'<p style="font-size:0.72rem;color:#2a1a1a;margin-top:0.35rem;">{"  ·  ".join(metrics)}</p>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)


def render_charts(insights):
    pc = {'High': 0, 'Medium': 0, 'Low': 0}
    cc = {'Historical': 0, 'Platform': 0, 'Combined': 0}
    for i in insights:
        p = i.get('priority', 'medium').capitalize()
        if p in pc: pc[p] += 1
        c = i.get('comparison_type', 'self')
        if c == 'self': cc['Historical'] += 1
        elif c == 'benchmark': cc['Platform'] += 1
        elif c == 'both': cc['Combined'] += 1

    layout = dict(
        height=200, margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor='#111111', paper_bgcolor='#111111',
        font=dict(family='Barlow, sans-serif', color='#6b5b55', size=11),
        title_font=dict(size=10, color='#6b5b55', family='Barlow Condensed'),
        showlegend=False,
        yaxis=dict(showgrid=True, gridcolor='#1e1010', showline=False, zeroline=False, color='#3d2d2d'),
        xaxis=dict(showgrid=False, showline=False, color='#6b5b55')
    )

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure(go.Bar(
            x=list(pc.keys()), y=list(pc.values()),
            marker_color=['#c0392b', '#e67e22', '#27ae60'],
            marker_line_width=0,
            text=list(pc.values()), textposition='outside',
            textfont=dict(color='#9a8a80', size=12, family='Barlow Condensed'),
        ))
        fig.update_layout(title='BY PRIORITY', **layout)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(
            x=list(cc.keys()), y=list(cc.values()),
            marker_color=['#3498db', '#9b59b6', '#c0392b'],
            marker_line_width=0,
            text=list(cc.values()), textposition='outside',
            textfont=dict(color='#9a8a80', size=12, family='Barlow Condensed'),
        ))
        fig2.update_layout(title='BY COMPARISON TYPE', **layout)
        st.plotly_chart(fig2, use_container_width=True)


def render_insights_section(data):
    entity_type = data.get('entity_type', '')
    entity_id = data.get('entity_id', '')
    period = data.get('dashboard_period', {})
    insights = data.get('insights', [])
    comp = data.get('comparison_types', {})

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:1.25rem;">
        <span class="entity-tag entity-{entity_type}">{entity_type}</span>
        <span style="font-family:'Barlow Condensed',sans-serif;font-size:1.5rem;font-weight:700;letter-spacing:0.05em;color:#e8e0d8;">ID {entity_id}</span>
        <span style="font-size:0.75rem;color:#2a1a1a;letter-spacing:0.04em;">{period.get('start_date','')} → {period.get('end_date','')}</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Insights", data.get('insights_count', len(insights)))
    with col2: st.metric("High Priority", data.get('high_priority_count', 0))
    with col3: st.metric("vs Historical", comp.get('self', 0))
    with col4: st.metric("vs Platform", comp.get('benchmark', 0) + comp.get('both', 0))

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    if insights:
        render_charts(insights)

    st.markdown("---")
    section_label("Insights")

    if insights:
        col1, col2 = st.columns(2)
        with col1:
            filter_p = st.radio("Priority", ['All', 'High', 'Medium', 'Low'], horizontal=True, key="fp")
        with col2:
            filter_c = st.radio("Type", ['All', 'Historical', 'Platform', 'Combined'], horizontal=True, key="fc")

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_ins = sorted(insights, key=lambda x: priority_order.get(x.get('priority', 'medium'), 1))
        type_map = {'Historical': 'self', 'Platform': 'benchmark', 'Combined': 'both'}

        if filter_p != 'All':
            sorted_ins = [i for i in sorted_ins if i.get('priority', '').capitalize() == filter_p]
        if filter_c != 'All':
            sorted_ins = [i for i in sorted_ins if i.get('comparison_type') == type_map.get(filter_c)]

        if sorted_ins:
            for ins in sorted_ins:
                render_insight(ins)
        else:
            st.markdown('<p style="color:#3d2d2d;font-size:0.875rem;">No insights match the selected filters.</p>', unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        st.download_button(
            "⬇  DOWNLOAD JSON",
            data=json.dumps(data, indent=2),
            file_name=f"{entity_type}_{entity_id}_insights.json",
            mime="application/json"
        )
    else:
        st.markdown('<p style="color:#3d2d2d;">No insights available.</p>', unsafe_allow_html=True)


def main():
    # SIDEBAR
    with st.sidebar:
        st.markdown("""
        <div style="padding:1rem 0 0.5rem 0;">
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.3rem;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#e8e0d8;">
                VIPANI<span style="color:#c0392b;">.</span>
            </div>
            <div style="font-size:0.62rem;color:#3d2d2d;letter-spacing:0.15em;text-transform:uppercase;font-weight:700;margin-top:0.15rem;">
                Insights Platform
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        mode = st.radio("", ['Generate Insights', 'Browse All'], label_visibility="collapsed")

        st.markdown("---")

        entity_filter = 'All'
        if mode == 'Browse All':
            entity_filter = st.selectbox("Filter", ['All', 'Buyers', 'Sellers'])

        st.markdown("---")

        if st.button("↺  REFRESH", use_container_width=True):
            st.rerun()

        st.markdown("---")

        status = get_db_status()
        if status:
            st.markdown(f"""
            <div class="db-ok">
                <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#27ae60;margin-bottom:0.35rem;">Analytics DB</div>
                <div style="color:#9a8a80;font-size:0.82rem;">✓ {status['buyers']} buyers · {status['sellers']} sellers</div>
                {"<div style='font-size:0.72rem;color:#3d2d2d;margin-top:0.2rem;'>Synced " + status['last_sync'] + "</div>" if status['last_sync'] else ""}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="db-err">
                <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.25rem;">DB Not Found</div>
                <div>Run sync_to_duckdb.py</div>
            </div>
            """, unsafe_allow_html=True)

    # HEADER
    st.markdown("""
    <div class="vp-header">
        <div class="vp-logo">VIPANI <span style="color:#c0392b;">INSIGHTS</span></div>
        <div style="font-size:0.72rem;color:#3d2d2d;letter-spacing:0.15em;text-transform:uppercase;font-weight:600;margin-top:0.2rem;">
            AI-Powered Procurement Analytics &amp; Benchmarking
        </div>
    </div>
    """, unsafe_allow_html=True)

    # GENERATE MODE
    if mode == 'Generate Insights':
        available = load_available_entities()

        section_label("Configure")
        st.markdown('<div class="gen-panel">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            entity_type = st.selectbox("Entity Type", ['buyer', 'seller'], format_func=str.capitalize)
        with col2:
            if available[entity_type]:
                entity_id = st.selectbox("Entity ID", available[entity_type])
            else:
                st.markdown(f'<p style="color:#c0392b;font-size:0.875rem;">No {entity_type}s found. Run sync first.</p>', unsafe_allow_html=True)
                st.stop()

        col3, col4, col5 = st.columns([1.2, 1, 1])
        with col3:
            preset = st.selectbox("Time Period", ['Last 30 Days', 'Last 90 Days', 'Last 180 Days', 'Last 365 Days', 'Custom'], index=1)

        days_map = {'Last 30 Days': 30, 'Last 90 Days': 90, 'Last 180 Days': 180, 'Last 365 Days': 365}

        if preset == 'Custom':
            with col4:
                start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=90))
            with col5:
                end_date = st.date_input("End Date", value=datetime.now())
        else:
            days = days_map[preset]
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            with col4:
                st.markdown(f'<p style="font-size:0.68rem;color:#3d2d2d;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;margin-bottom:0.2rem;">From</p><p style="color:#9a8a80;font-size:0.9rem;">{start_date.strftime("%Y-%m-%d")}</p>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<p style="font-size:0.68rem;color:#3d2d2d;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;margin-bottom:0.2rem;">To</p><p style="color:#9a8a80;font-size:0.9rem;">{end_date.strftime("%Y-%m-%d")}</p>', unsafe_allow_html=True)

        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        if st.button("GENERATE INSIGHTS →"):
            status_box = st.empty()
            status_box.markdown('<div style="background:#1a0d0d;border:1px solid #2a1010;border-radius:4px;padding:0.75rem 1rem;font-size:0.85rem;color:#9a8a80;">⏳  Step 1 / 2 — Executing dashboard queries...</div>', unsafe_allow_html=True)

            insights_file, error = run_pipeline(
                entity_type, entity_id,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if error:
                status_box.markdown(f'<div style="background:rgba(192,57,43,0.08);border:1px solid rgba(192,57,43,0.25);border-radius:4px;padding:0.75rem 1rem;color:#e74c3c;font-size:0.875rem;">✗  Error: {error}</div>', unsafe_allow_html=True)
                st.stop()

            status_box.markdown('<div style="background:rgba(39,174,96,0.08);border:1px solid rgba(39,174,96,0.2);border-radius:4px;padding:0.75rem 1rem;color:#27ae60;font-size:0.875rem;">✓  Insights generated successfully.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        latest = load_latest_insight(entity_type, entity_id)
        if latest:
            st.markdown("---")
            render_insights_section(latest)

    # BROWSE MODE
    else:
        all_insights = load_all_insights()

        if not all_insights:
            st.markdown('<p style="color:#3d2d2d;">No insights found. Generate some first.</p>', unsafe_allow_html=True)
            st.stop()

        if entity_filter == 'Buyers':
            all_insights = [i for i in all_insights if i.get('entity_type') == 'buyer']
        elif entity_filter == 'Sellers':
            all_insights = [i for i in all_insights if i.get('entity_type') == 'seller']

        if not all_insights:
            st.markdown('<p style="color:#3d2d2d;">No insights match the selected filter.</p>', unsafe_allow_html=True)
            st.stop()

        section_label("Overview")

        total = len(all_insights)
        total_ins = sum(i.get('insights_count', 0) for i in all_insights)
        high = sum(i.get('high_priority_count', 0) for i in all_insights)
        avg = total_ins / total if total else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Entities", total)
        with col2: st.metric("Total Insights", total_ins)
        with col3: st.metric("High Priority", high)
        with col4: st.metric("Avg / Entity", f"{avg:.1f}")

        st.markdown("---")
        section_label("Select Entity")

        options = [f"{i['entity_type'].upper()}  {i['entity_id']}   ·   {i['insights_count']} insights" for i in all_insights]
        selected_idx = st.selectbox("", range(len(options)), format_func=lambda i: options[i])

        st.markdown("---")
        render_insights_section(all_insights[selected_idx])

    st.markdown("---")
    st.markdown(f'<p style="font-size:0.68rem;color:#1e1010;letter-spacing:0.1em;text-transform:uppercase;">Vipani Insights  ·  {datetime.now().strftime("%d %b %Y, %H:%M")}</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()