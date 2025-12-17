import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import datetime
import pytz  # <--- New library for Timezone
from config import CURRENT_WEEK, CURRENT_SEASON, DB_NAME 

# Page Config
st.set_page_config(
    page_title="The Audible", 
    page_icon="🏈", 
    layout="wide",
    initial_sidebar_state="auto"  # <--- CHANGED: "auto" collapses sidebar on mobile
)

# --- THEME OVERRIDE (CSS INJECTION) ---
st.markdown("""
<style>
    /* 1. FORCE MAIN BACKGROUND TO MIDNIGHT NAVY */
    .stApp {
        background-color: #0B1E33;
    }
    
    /* 2. FORCE SIDEBAR TO WHITE */
    [data-testid="stSidebar"] {
        background-color: #F5F7FA;
    }
    
    /* 3. SHIFT SIDEBAR CONTENT UP */
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }
    [data-testid="stSidebarUserContent"] {
        padding-top: 0rem;
        margin-top: -2rem; 
    }
    [data-testid="stSidebarNav"] {
        padding-top: 0rem;
    }
    
    /* 4. SIDEBAR TEXT STYLING (Dark Navy) */
    [data-testid="stSidebar"] * {
        color: #0B1E33 !important;
    }
    
    /* 5. MAIN AREA TEXT STYLING (White) */
    .main .block-container, .main h1, .main h2, .main h3, .main p, .main span, .main div {
        color: #F5F7FA !important;
    }

    /* 6. DROPDOWN GLOBAL ENFORCER (Mobile & Desktop) */
    /* Forces the popup menu background to Dark Navy */
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: #152a45 !important;
    }
    
    /* Forces ALL text inside the popup menu to be White */
    /* This catches list items, "No Results" text, and loading states */
    div[data-baseweb="menu"] * {
        color: white !important;
    }
    
    /* The Closed Box container */
    div[data-baseweb="select"] > div {
        background-color: #152a45 !important;
        border-color: #444 !important;
        color: white !important;
    }
    div[data-baseweb="select"] span {
        color: white !important;
    }
    div[data-baseweb="select"] svg {
        fill: white !important;
    }
    
    /* Hover State for Menu Items */
    ul[data-testid="stSelectboxVirtualDropdown"] li:hover {
        background-color: #26466D !important;
    }
    
    /* 7. SLIDER STYLING */
    div.stSlider > div[data-baseweb="slider"] > div > div {
        background-color: #EF553B !important; 
    }
    div.stSlider > div[data-baseweb="slider"] > div > div > div {
        background-color: #FFFFFF !important;
        border-color: #EF553B !important;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        background-color: #152a45;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_last_updated():
    """Gets the last modification time of the database and converts to ET"""
    try:
        timestamp = os.path.getmtime(DB_NAME)
        # 1. Get the time in UTC (Universal Time)
        dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        
        # 2. Convert to US/Eastern Time
        tz_eastern = pytz.timezone('US/Eastern')
        dt_eastern = dt_utc.astimezone(tz_eastern)
        
        return dt_eastern.strftime("%b %d, %I:%M %p ET") 
    except:
        return "Unknown"

def get_confidence_label(score):
    if score >= 75: return "High Confidence"
    if score >= 45: return "Medium Confidence"
    return "Low Confidence"

def load_projections(week):
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT * FROM predictions_history WHERE season = {CURRENT_SEASON} AND week = {week}"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if not df.empty:
        if 'confidence_label' not in df.columns:
            df['confidence_label'] = df['confidence_score'].apply(get_confidence_label)
        if 'std_dev' in df.columns:
            df['range_low'] = (df['projected_score'] - df['std_dev']).clip(lower=0)
            df['range_high'] = df['projected_score'] + df['std_dev']
        else:
            df['range_low'] = df['projected_score']
            df['range_high'] = df['projected_score']
    return df

def load_actuals(week):
    conn = sqlite3.connect(DB_NAME)
    query = f"""
    SELECT 
        ph.player_name, ph.position, p.team,
        ph.projected_score, ph.confidence_score, ph.risk_tier,
        w.pts_ppr as actual_score
    FROM predictions_history ph
    JOIN weekly_stats w ON ph.player_id = w.player_id AND ph.season = w.season AND ph.week = w.week
    LEFT JOIN players p ON ph.player_id = p.player_id 
    WHERE ph.week = {week}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_season_correlations():
    conn = sqlite3.connect(DB_NAME)
    query = f"""
    SELECT ph.position, ph.projected_score, w.pts_ppr as actual_score
    FROM predictions_history ph
    JOIN weekly_stats w ON ph.player_id = w.player_id AND ph.season = w.season AND ph.week = w.week
    WHERE ph.season = {CURRENT_SEASON}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty: return {}
    
    correlations = {}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_df = df[df['position'] == pos]
        if len(pos_df) > 10:
            corr = pos_df['projected_score'].corr(pos_df['actual_score'])
            correlations[pos] = corr
        else:
            correlations[pos] = 0.0
            
    return correlations

# --- SIDEBAR CONTENT ---
st.sidebar.image("logo.png", use_container_width=True) 

mode = st.sidebar.radio(
    "Navigation", 
    ["🔮 Live Projections", "📜 Projection History", "📉 Performance Audit"]
)

# --- REUSABLE PROJECTION CONTENT ---
def render_projections_content(week):
    
    if week == CURRENT_WEEK:
        last_updated = get_last_updated()
        st.caption(f"🕒 Last Updated: {last_updated}")
        
    col1, col2 = st.columns(2)
    with col1:
        selected_pos = st.multiselect("Position", ["QB", "RB", "WR", "TE"], default=["QB", "RB", "WR", "TE"], key=f"pos_{week}")
    with col2:
        min_conf = st.slider("Minimum Confidence Score", 0, 100, 50, key=f"conf_{week}")
    
    df = load_projections(week)
    
    if not df.empty:
        mask = (df['position'].isin(selected_pos)) & (df['confidence_score'] >= min_conf)
        filtered_df = df[mask].sort_values("projected_score", ascending=False)
        
        if not filtered_df.empty:
            st.dataframe(
                filtered_df[['player_name', 'position', 'projected_score', 'range_low', 'range_high', 'risk_tier', 'confidence_score']],
                use_container_width=True,
                hide_index=True, 
                column_config={
                    "player_name": "Player",
                    "position": "Pos",
                    "risk_tier": "Risk Profile",
                    "projected_score": st.column_config.ProgressColumn("Projection", format="%.1f", min_value=0, max_value=30),
                    "confidence_score": st.column_config.NumberColumn("Conf", format="%.0f %%"),
                    "range_low": st.column_config.NumberColumn("Floor", format="%.1f"),
                    "range_high": st.column_config.NumberColumn("Ceiling", format="%.1f"),
                }
            )
            
            st.subheader(f"📊 Range of Outcomes (Top 20)")
            top_20 = filtered_df.head(20)
            
            fig = px.scatter(
                top_20, x="projected_score", y="player_name", 
                error_x="std_dev", error_x_minus="std_dev",
                color="risk_tier",
                hover_data=['range_low', 'range_high'],
                color_discrete_map={
                    "Safe": "#00A8E8",      # Cyan
                    "Volatile": "#B0B0B0",  # Silver
                    "Boom/Bust": "#EF553B"  # Red
                },
                title="Projected Score +/- 1 Std Dev"
            )
            fig.update_layout(
                yaxis={'categoryorder':'total ascending'}, 
                height=600,
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="#F5F7FA"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No players match your filters.")
    else:
        st.warning(f"No projections found for Week {week}.")

# --- PAGE 1: LIVE PROJECTIONS ---
if mode == "🔮 Live Projections":
    st.title(f"Week {CURRENT_WEEK} Projections")
    render_projections_content(CURRENT_WEEK)

# --- PAGE 2: PROJECTION HISTORY ---
elif mode == "📜 Projection History":
    c1, c2 = st.columns([3, 1]) 
    with c1:
        st.title("Historical Projections")
    with c2:
        history_weeks = list(range(2, CURRENT_WEEK))
        selected_hist_week = st.selectbox("Select Week", history_weeks[::-1])
    
    st.divider() 
    if selected_hist_week:
        render_projections_content(selected_hist_week)

# --- PAGE 3: PERFORMANCE AUDIT ---
elif mode == "📉 Performance Audit":
    c1, c2 = st.columns([3, 1]) 
    with c1:
        st.title("🎯 Accuracy Report")
    with c2:
        audit_weeks_list = list(range(2, CURRENT_WEEK))
        audit_weeks_desc = audit_weeks_list[::-1] 
        audit_week = st.selectbox("Select Week to Audit", audit_weeks_desc, index=0)

    selected_audit_pos = st.multiselect(
        "Filter by Position", 
        ["QB", "RB", "WR", "TE"], 
        default=["QB", "RB", "WR", "TE"]
    )
    
    st.divider() 
    
    df = load_actuals(audit_week)
    
    if not df.empty:
        df = df[df['position'].isin(selected_audit_pos)]
        
        if not df.empty:
            df['error'] = df['projected_score'] - df['actual_score']
            
            st.markdown(f"### Week {audit_week} Report Card")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Samples", len(df))
            c2.metric("Correlation (R)", f"{df['projected_score'].corr(df['actual_score']):.3f}")
            c3.metric("Avg Error", f"{df['error'].abs().mean():.1f} pts")
            c4.metric("Bias", f"{df['error'].mean():.1f} pts")

            fig = px.scatter(
                df, x="projected_score", y="actual_score", 
                color="position", hover_data=['player_name', 'error'],
                title=f"Week {audit_week}: Predicted vs Actual",
                color_discrete_sequence=["#00A8E8", "#EF553B", "#B0B0B0", "#FFFFFF"] 
            )
            fig.add_shape(type="line", x0=0, y0=0, x1=40, y1=40, line=dict(color="#B0B0B0", dash="dash"))
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#F5F7FA")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📉 The 'Whiff' List (Biggest Misses)")
            df['abs_error'] = df['error'].abs()
            misses = df.sort_values("abs_error", ascending=False).head(10)
            
            st.dataframe(
                misses[['player_name', 'position', 'projected_score', 'actual_score', 'error', 'confidence_score']],
                hide_index=True,
                use_container_width=True
            )
            
            st.divider()
            st.markdown("### 🏆 The Audible vs. The World (Season Long)")
            
            my_stats = get_season_correlations()
            
            benchmark_data = [
                {"Position": "QB", "My Model": my_stats.get('QB', 0), "Standard (ESPN/Yahoo)": 0.50, "Pro (Vegas/4for4)": 0.60, "God Tier": 0.65},
                {"Position": "RB", "My Model": my_stats.get('RB', 0), "Standard (ESPN/Yahoo)": 0.50, "Pro (Vegas/4for4)": 0.60, "God Tier": 0.65},
                {"Position": "WR", "My Model": my_stats.get('WR', 0), "Standard (ESPN/Yahoo)": 0.45, "Pro (Vegas/4for4)": 0.55, "God Tier": 0.65},
                {"Position": "TE", "My Model": my_stats.get('TE', 0), "Standard (ESPN/Yahoo)": 0.45, "Pro (Vegas/4for4)": 0.55, "God Tier": 0.65},
            ]
            
            bench_df = pd.DataFrame(benchmark_data)
            
            st.dataframe(
                bench_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "My Model": st.column_config.NumberColumn("The Audible (Real-Time)", format="%.3f"),
                    "Standard (ESPN/Yahoo)": st.column_config.NumberColumn("Standard Baseline", format="%.2f"),
                    "Pro (Vegas/4for4)": st.column_config.NumberColumn("Professional Grade", format="%.2f"),
                    "God Tier": st.column_config.NumberColumn("God Tier (Unsustainable)", format="%.2f"),
                }
            )
            
            st.markdown("""
            **Benchmark Key:**
            * **Standard Baseline:** Default projections provided by major platforms like ESPN and Yahoo. Rely on simple averages.
            * **Professional Grade:** Sophisticated models from paid subscription services (e.g., 4for4, Establish The Run) and Vegas player prop implied totals.
            * **God Tier (>0.65):** Widely considered statistically impossible to sustain over multiple seasons due to injury variance and randomness.
            
            *Sources: Benchmarks derived from historical accuracy audits by Fantasy Football Analytics (FFA), Subvertadown, and RotoViz.*
            """)
            
        else:
            st.warning("No players found for the selected position(s).")
    else:
        st.error(f"No data found for Week {audit_week}. Run '06_backfill_history.py'?")