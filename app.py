import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import datetime
import pytz
from config import CURRENT_WEEK, CURRENT_SEASON, DB_NAME 

# Page Config
st.set_page_config(
    page_title="The Audible", 
    page_icon="🏈", 
    layout="wide",
    initial_sidebar_state="auto"
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

    /* 6. DROPDOWN GLOBAL ENFORCER */
    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: #152a45 !important;
    }
    div[data-baseweb="menu"] * {
        color: white !important;
    }
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
    
    /* 8. DESKTOP LOCK (Hide Resize Handle) */
    div[data-testid="stSidebarResizeHandle"] {
        display: none !important;
    }
    
    /* 9. ROSTER DELETE BUTTON STYLING */
    /* Makes the 'X' button small, red, and minimal */
    button[kind="secondary"] {
        padding: 0px 8px !important;
        border: 1px solid #EF553B !important;
        color: #EF553B !important;
        background-color: transparent !important;
        border-radius: 4px !important;
        font-size: 12px !important;
        height: 28px !important;
        line-height: 28px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #EF553B !important;
        color: white !important;
    }
    
    /* 10. MOBILE SPECIFIC TWEAKS */
    @media (max-width: 768px) {
        /* We removed the aggressive header hider so the menu comes back */
        section[data-testid="stSidebar"] {
            width: 85% !important; 
        }
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        background-color: #152a45;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'my_team_roster' not in st.session_state:
    st.session_state.my_team_roster = []
if 'opp_team_roster' not in st.session_state:
    st.session_state.opp_team_roster = []

# --- HELPER FUNCTIONS ---
def get_last_updated():
    try:
        timestamp = os.path.getmtime(DB_NAME)
        dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        tz_eastern = pytz.timezone('US/Eastern')
        dt_eastern = dt_utc.astimezone(tz_eastern)
        return dt_eastern.strftime("%b %d, %I:%M %p ET") 
    except:
        return "Unknown"

def get_confidence_label(row):
    score = row['confidence_score']
    proj = row['projected_score']
    
    if proj >= 15.0 and score < 45:
        return "Volatile Star 🌟"
    
    if score >= 75: return "High Confidence"
    if score >= 45: return "Medium Confidence"
    return "Low Confidence"

def load_projections(week):
    conn = sqlite3.connect(DB_NAME)
    query = f"SELECT * FROM predictions_history WHERE season = {CURRENT_SEASON} AND week = {week}"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if not df.empty:
        cols_to_clip = ['projected_score', 'range_low', 'range_high']
        for col in cols_to_clip:
            if col in df.columns:
                df[col] = df[col].clip(lower=0)
        
        df = df[df['projected_score'] > 0.0]

        if 'std_dev' in df.columns:
            df['std_dev'] = df['std_dev'].fillna(0)
            if 'range_low' not in df.columns:
                df['range_low'] = (df['projected_score'] - df['std_dev']).clip(lower=0)
            if 'range_high' not in df.columns:
                df['range_high'] = df['projected_score'] + df['std_dev']
        
        if 'range_high' in df.columns:
            zero_variance_mask = (df['range_high'] - df['range_low']) < 0.1
            df.loc[zero_variance_mask, 'confidence_score'] = 0
            df.loc[zero_variance_mask, 'risk_tier'] = "Insufficient Data"
        
        df['confidence_label'] = df.apply(get_confidence_label, axis=1)

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
    
    df = df[df['projected_score'] > 0]
    
    correlations = {}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_df = df[df['position'] == pos]
        if len(pos_df) > 10:
            corr = pos_df['projected_score'].corr(pos_df['actual_score'])
            correlations[pos] = corr
        else:
            correlations[pos] = 0.0
            
    return correlations

def sort_roster_df(df):
    pos_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4}
    df['pos_rank'] = df['position'].map(pos_order).fillna(99)
    return df.sort_values('pos_rank').drop(columns=['pos_rank'])

# --- SIDEBAR CONTENT ---
st.sidebar.image("logo.png", use_container_width=True) 

mode = st.sidebar.radio(
    "Navigation", 
    ["🔮 Live Projections", "⚔️ Matchup Sim", "📜 Projection History", "📉 Performance Audit"]
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
        min_conf = st.slider("Minimum Confidence Score", 0, 100, 0, key=f"conf_{week}")
    
    df = load_projections(week)
    
    if not df.empty:
        mask = (df['position'].isin(selected_pos)) & (df['confidence_score'] >= min_conf)
        filtered_df = df[mask].sort_values("projected_score", ascending=False)
        
        if not filtered_df.empty:
            st.dataframe(
                filtered_df[['player_name', 'position', 'projected_score', 'range_low', 'range_high', 'confidence_label', 'confidence_score']],
                use_container_width=True,
                hide_index=True, 
                column_config={
                    "player_name": "Player",
                    "position": "Pos",
                    "confidence_label": "Risk Profile",
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
                color="confidence_label", 
                hover_data=['range_low', 'range_high'],
                color_discrete_map={
                    "High Confidence": "#00A8E8", "Medium Confidence": "#B0B0B0",  
                    "Volatile Star 🌟": "#FFD700", "Low Confidence": "#EF553B", 
                    "Insufficient Data": "#444444"
                },
                title="Projected Score +/- 1 Std Dev"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#F5F7FA")
            st.plotly_chart(fig, use_container_width=True)
            st.info("ℹ️ **Note:** 'Confidence' measures **Predictability**, not Talent. A 'Volatile Star' (Low Confidence) is a great player who has had some inconsistent games recently.")
        else:
            st.warning("No players match your filters.")
    else:
        st.warning(f"No projections found for Week {week}.")

# --- PAGE 1: LIVE PROJECTIONS ---
if mode == "🔮 Live Projections":
    st.title(f"Week {CURRENT_WEEK} Projections")
    render_projections_content(CURRENT_WEEK)

# --- PAGE 2: MATCHUP SIM ---
elif mode == "⚔️ Matchup Sim":
    st.title(f"Week {CURRENT_WEEK} Matchup Sim")
    
    all_projections = load_projections(CURRENT_WEEK)
    
    if not all_projections.empty:
        player_list = sorted(all_projections['player_name'].unique().tolist())
        col1, col2 = st.columns(2)
        
        # --- LEFT COLUMN: YOUR TEAM ---
        with col1:
            st.subheader("Your Team")
            
            c_add, c_btn = st.columns([3, 1])
            new_player = c_add.selectbox("Add Player", options=["Select..."] + player_list, key="my_add", label_visibility="collapsed")
            if c_btn.button("Add", key="btn_add_my"):
                if new_player != "Select..." and new_player not in st.session_state.my_team_roster:
                    st.session_state.my_team_roster.append(new_player)
                    st.rerun()

            if st.session_state.my_team_roster:
                my_team_df = all_projections[all_projections['player_name'].isin(st.session_state.my_team_roster)].copy()
                my_team_df = sort_roster_df(my_team_df)
                
                st.markdown("---")
                for index, row in my_team_df.iterrows():
                    with st.container():
                        # CHANGED RATIO: [3, 2, 1] - Tighter stats column
                        c_name, c_stats, c_del = st.columns([3, 2, 1])
                        
                        with c_name:
                            st.write(f"**{row['player_name']}**")
                            st.caption(f"{row['position']}")
                            
                        with c_stats:
                            st.write(f"Proj: **{row['projected_score']:.1f}**")
                            st.caption(f"{row['range_low']:.0f} - {row['range_high']:.0f}")
                            
                        with c_del:
                            if st.button("✕", key=f"rem_my_{row['player_name']}"):
                                st.session_state.my_team_roster.remove(row['player_name'])
                                st.rerun()
                        
                        st.divider() 

                # TOTALS
                my_floor = my_team_df['range_low'].sum()
                my_proj = my_team_df['projected_score'].sum()
                my_ceil = my_team_df['range_high'].sum()
                
                st.markdown(f"**Total Projection: {my_proj:.1f}**")
                st.caption(f"Floor: {my_floor:.1f} | Ceiling: {my_ceil:.1f}")

            else:
                st.info("Roster is empty.")

        # --- RIGHT COLUMN: OPPONENT ---
        with col2:
            st.subheader("Opponent")
            
            c_add_opp, c_btn_opp = st.columns([3, 1])
            new_opp = c_add_opp.selectbox("Add Player", options=["Select..."] + player_list, key="opp_add", label_visibility="collapsed")
            if c_btn_opp.button("Add", key="btn_add_opp"):
                if new_opp != "Select..." and new_opp not in st.session_state.opp_team_roster:
                    st.session_state.opp_team_roster.append(new_opp)
                    st.rerun()

            if st.session_state.opp_team_roster:
                opp_team_df = all_projections[all_projections['player_name'].isin(st.session_state.opp_team_roster)].copy()
                opp_team_df = sort_roster_df(opp_team_df)
                
                st.markdown("---")
                for index, row in opp_team_df.iterrows():
                    with st.container():
                        c_name, c_stats, c_del = st.columns([3, 2, 1])
                        
                        with c_name:
                            st.write(f"**{row['player_name']}**")
                            st.caption(f"{row['position']}")
                            
                        with c_stats:
                            st.write(f"Proj: **{row['projected_score']:.1f}**")
                            st.caption(f"{row['range_low']:.0f} - {row['range_high']:.0f}")
                            
                        with c_del:
                            if st.button("✕", key=f"rem_opp_{row['player_name']}"):
                                st.session_state.opp_team_roster.remove(row['player_name'])
                                st.rerun()
                        
                        st.divider()

                opp_floor = opp_team_df['range_low'].sum()
                opp_proj = opp_team_df['projected_score'].sum()
                opp_ceil = opp_team_df['range_high'].sum()
                
                st.markdown(f"**Total Projection: {opp_proj:.1f}**")
                st.caption(f"Floor: {opp_floor:.1f} | Ceiling: {opp_ceil:.1f}")

            else:
                st.info("Roster is empty.")
        
        # --- COMPARISON CHART ---
        if st.session_state.my_team_roster and st.session_state.opp_team_roster:
            st.markdown("---")
            
            diff = my_proj - opp_proj
            if diff > 0:
                color = "#4CAF50" # Green
                msg = f"🏆 You are projected to win by {diff:.1f} points!"
            else:
                color = "#EF553B" # Red
                msg = f"⚠️ You are projected to lose by {abs(diff):.1f} points."
                
            st.markdown(f"<h3 style='text-align: center; color: {color};'>{msg}</h3>", unsafe_allow_html=True)
            
            comp_data = {
                "Team": ["You", "You", "You", "Opponent", "Opponent", "Opponent"],
                "Metric": ["Floor", "Projection", "Ceiling", "Floor", "Projection", "Ceiling"],
                "Score": [my_floor, my_proj, my_ceil, opp_floor, opp_proj, opp_ceil]
            }
            comp_df = pd.DataFrame(comp_data)
            
            fig = px.bar(
                comp_df, x="Metric", y="Score", color="Team", barmode="group",
                color_discrete_map={"You": "#00A8E8", "Opponent": "#EF553B"},
                text_auto='.1f'
            )
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#F5F7FA", height=400)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("No projections available for Matchup Sim.")

# --- PAGE 3: PROJECTION HISTORY ---
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

# --- PAGE 4: PERFORMANCE AUDIT ---
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
        df = df[df['projected_score'] > 0.0]
        
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