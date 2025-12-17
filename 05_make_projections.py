import sqlite3
import pandas as pd
import os
import numpy as np
from projections.predict_qb import predict_qb
from projections.predict_rb import predict_rb
from projections.predict_wr import predict_wr
from projections.predict_te import predict_te
from config import CURRENT_WEEK, CURRENT_SEASON, DB_NAME # <--- NEW IMPORT

OUTPUT_FOLDER = "output"

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# --- CONFIG: RISK THRESHOLDS ---
RISK_CFG = {
    'QB': {'safe': 7.0, 'boom_bust': 12.0, 'default_std': 6.0},
    'RB': {'safe': 5.5, 'boom_bust': 10.0, 'default_std': 7.0},
    'WR': {'safe': 5.5, 'boom_bust': 10.0, 'default_std': 8.0},
    'TE': {'safe': 4.0, 'boom_bust': 8.0,  'default_std': 5.0}
}

def get_risk_label(row):
    pos = row['position']
    std = row['std_dev']
    cfg = RISK_CFG.get(pos, RISK_CFG['RB'])
    if std <= cfg['safe']: return "Safe"
    elif std >= cfg['boom_bust']: return "Boom/Bust"
    else: return "Volatile"

def get_confidence_label(score):
    if score >= 75: return "High Confidence"
    if score >= 45: return "Medium Confidence"
    return "Low Confidence"

def save_projections_to_db(all_projections_dict, conn, season, week):
    # print(f"   📸 SNAPSHOTTING WEEK {week} TO DATABASE...") 
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM predictions_history WHERE season = {season} AND week = {week}")
    
    count = 0
    for pos, df in all_projections_dict.items():
        if df.empty: continue
        
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                row['player_id'],
                row['full_name'],
                row['position'],
                season,
                week,
                row['projected_score'],
                row['risk_tier'],
                row['confidence_score'],
                row.get('std_dev', 0)
            ))
            
        cursor.executemany("""
        INSERT OR REPLACE INTO predictions_history 
        (player_id, player_name, position, season, week, projected_score, risk_tier, confidence_score, std_dev)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)
        count += len(data_to_insert)
        
    conn.commit()
    # print(f"   ✅ Saved {count} projections to the Vault.")

def get_projections_for_position(position, conn, target_week, allowed_player_ids=None):
    # 1. DEPTH CHART FILTER
    # If we are backfilling (allowed_player_ids exists), we IGNORE depth chart logic
    # and trust the list of who actually played.
    if allowed_player_ids is not None:
        if len(allowed_player_ids) == 0: return pd.DataFrame()
        
        if len(allowed_player_ids) == 1: id_str = f"('{allowed_player_ids[0]}')"
        else: id_str = str(tuple(allowed_player_ids))
        
        depth_filter = f"AND p.player_id IN {id_str}"
    else:
        # Standard Logic for Live Projections
        if position == 'QB': depth_filter = "AND p.depth_chart_order = 1"
        elif position == 'RB': depth_filter = "AND p.depth_chart_order <= 3"
        elif position == 'WR': depth_filter = "AND p.depth_chart_order <= 5"
        else: depth_filter = "AND p.depth_chart_order <= 3"

    # 2. QUERY
    query = f"""
    SELECT 
        p.player_id, p.full_name, p.team, p.position,
        m.opponent, m.vegas_implied_total, m.spread,
        d.def_rank as opponent_rank,
        s.rank_sack_rate as defense_toughness_rank, s.rank_funnel
    FROM players p
    JOIN matchups m ON m.season = {CURRENT_SEASON} AND m.week = {target_week} AND p.team = m.team
    LEFT JOIN defensive_stats d ON d.season = {CURRENT_SEASON} AND d.team = m.opponent AND d.position = '{position}'
    LEFT JOIN secret_sauce_def s ON s.season = {CURRENT_SEASON} AND s.opponent = m.opponent
    WHERE p.position = '{position}' 
      AND p.status = 'Active' 
      {depth_filter} 
      AND m.vegas_implied_total IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    if df.empty: return pd.DataFrame()

    # --- 3. RISK & RANGE CALCULATION ---
    pids = tuple(df['player_id'].unique())
    if len(pids) == 1: pid_str = f"('{pids[0]}')"
    else: pid_str = str(pids)
    
    # Calculate History (Strictly BEFORE target_week)
    var_query = f"""
    SELECT player_id, 
           COUNT(week) as games_played,
           MAX(pts_ppr) - MIN(pts_ppr) as raw_volatility
    FROM weekly_stats 
    WHERE season = {CURRENT_SEASON} AND player_id IN {pid_str} AND week < {target_week}
    GROUP BY player_id
    """
    risk_df = pd.read_sql(var_query, conn)
    
    stats_query = f"""
    SELECT player_id, pts_ppr
    FROM weekly_stats 
    WHERE season = {CURRENT_SEASON} AND player_id IN {pid_str} AND week < {target_week}
    """
    stats_df = pd.read_sql(stats_query, conn)
    
    if not stats_df.empty:
        real_stats = stats_df.groupby('player_id')['pts_ppr'].agg(['std', 'min', 'max']).reset_index()
        real_stats.rename(columns={'std': 'std_dev', 'min': 'floor', 'max': 'ceiling'}, inplace=True)
        df = pd.merge(df, real_stats, on='player_id', how='left')
        df = pd.merge(df, risk_df, on='player_id', how='left').fillna(0)
    else:
        df['std_dev'] = 0
        df['games_played'] = 0

    # FILL NAN STD DEV 
    cfg = RISK_CFG.get(position, RISK_CFG['RB'])
    df['std_dev'] = np.where(df['games_played'] < 4, cfg['default_std'], df['std_dev'])
    
    # 4. ROUTE TO SPECIALIST
    if position == 'QB': df = predict_qb(df, conn, CURRENT_SEASON)
    elif position == 'RB': df = predict_rb(df, conn, CURRENT_SEASON)
    elif position == 'WR': df = predict_wr(df, conn, CURRENT_SEASON, target_week)
    elif position == 'TE': df = predict_te(df, conn, CURRENT_SEASON)
    else: df['projected_score'] = df['vegas_implied_total']

    # --- 5. CALCULATE RANGES & CONFIDENCE ---
    df['range_low'] = (df['projected_score'] - df['std_dev']).clip(lower=0)
    df['range_high'] = df['projected_score'] + df['std_dev']
    
    safe_mean = df['projected_score'].replace(0, 1) 
    df['confidence_score'] = 100 - ((df['std_dev'] / safe_mean) * 100)
    df['confidence_score'] = df['confidence_score'].clip(0, 100)

    df['risk_tier'] = df.apply(get_risk_label, axis=1)
    df['confidence_label'] = df['confidence_score'].apply(get_confidence_label)

    # 6. CLEANUP
    cols = ['player_id', 'full_name', 'position', 'team', 'opponent', 'projected_score', 
            'range_low', 'range_high', 'confidence_label', 'confidence_score', 'risk_tier', 
            'std_dev', 'floor', 'ceiling', 'vegas_implied_total']
            
    extras = ['season_avg_pts', 'season_avg_rec', 'spread', 'rank_funnel']
    for c in extras:
        if c in df.columns: cols.append(c)

    return df[cols].sort_values('projected_score', ascending=False)

def run_all_projections(target_week=CURRENT_WEEK, allowed_players_map=None):
    # allowed_players_map: {'QB': [id1, id2], 'RB': [...]}
    
    # print(f"--- 🚀 STARTING BATCH PROJECTIONS (Week {target_week}) ---")
    conn = sqlite3.connect(DB_NAME)
    all_projections = {}
    
    for pos in ['QB', 'RB', 'WR', 'TE']:
        # If we have a whitelist map, get the list for this position
        whitelist = None
        if allowed_players_map:
            whitelist = allowed_players_map.get(pos, [])
            
        df = get_projections_for_position(pos, conn, target_week, allowed_player_ids=whitelist)
        if not df.empty:
            all_projections[pos] = df

    # SAVE TO DB
    save_projections_to_db(all_projections, conn, CURRENT_SEASON, target_week)
    conn.close()

if __name__ == "__main__":
    run_all_projections(CURRENT_WEEK)