import pandas as pd

def predict_wr(df, conn, current_season, current_week): # <--- Added current_week
    print("   🧠 Running Specialist Model: WR 80/20 Split & Target Logic...")
    
    # 1. GET PLAYER HISTORY (Season vs Recent)
    player_ids = tuple(df['player_id'].unique())
    
    if len(player_ids) == 1:
        id_placeholder = f"('{player_ids[0]}')"
    else:
        id_placeholder = str(player_ids)
        
    # SQL Magic: Calculate Season Avg AND Recent Avg (Last 3 Weeks) in one go
    query = f"""
    SELECT 
        player_id,
        AVG(pts_ppr) as season_avg_pts,
        AVG(CASE WHEN week >= {current_week - 3} THEN pts_ppr ELSE NULL END) as recent_avg_pts,
        AVG(rec) as season_avg_rec,
        AVG(rec_yd) as season_avg_yd
    FROM weekly_stats
    WHERE season = {current_season}
      AND player_id IN {id_placeholder}
    GROUP BY player_id
    """
    
    history_df = pd.read_sql(query, conn)
    
    # Merge history back into the main projections dataframe
    df = pd.merge(df, history_df, on='player_id', how='left')
    
    # Fill NaN: If no recent games, fallback to season average
    df['recent_avg_pts'] = df['recent_avg_pts'].fillna(df['season_avg_pts'])
    df = df.fillna(0)
    
    # 2. THE ALGORITHM: "The Golden Ratio" (80/20)
    
    # A. The Baseline
    # We replace the raw Season Avg with our new Weighted Average
    # Lab Result: 0.4833 correlation (vs 0.4795)
    df['weighted_avg'] = (df['season_avg_pts'] * 0.80) + (df['recent_avg_pts'] * 0.20)
    
    # Mix with Vegas (20% Vegas / 80% Player Talent)
    vegas_proxy = df['vegas_implied_total'] * 0.5 
    df['base_projection'] = (vegas_proxy * 0.2) + (df['weighted_avg'] * 0.8)
    
    # B. The "Target Hog" Bonus (Volume)
    # If they catch 5+ balls a game, they are elite.
    df.loc[df['season_avg_rec'] > 5.0, 'base_projection'] += 2.5
    df.loc[df['season_avg_rec'] > 6.5, 'base_projection'] += 1.5
    
    # C. The "Shootout" Bonus
    df['shootout_bonus'] = 0.0
    df.loc[df['vegas_implied_total'] > 24, 'shootout_bonus'] += 1.5
    
    # D. The "Funnel" Tie-Breaker
    if 'rank_funnel' in df.columns:
        df.loc[df['rank_funnel'] < 10, 'base_projection'] += 1.0
        df.loc[df['rank_funnel'] > 25, 'base_projection'] -= 1.0

    # 3. FINAL SCORE
    df['projected_score'] = df['base_projection'] + df['shootout_bonus']
    
    return df