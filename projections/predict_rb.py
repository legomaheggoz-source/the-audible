import pandas as pd

def predict_rb(df, conn, current_season):
    print("   🧠 Running Specialist Model: RB Game Script Logic...")
    
    # 1. GET PLAYER HISTORY (Volume is King for RBs)
    player_ids = tuple(df['player_id'].unique())
    
    if len(player_ids) == 1:
        id_placeholder = f"('{player_ids[0]}')"
    else:
        id_placeholder = str(player_ids)
        
    query = f"""
    SELECT 
        player_id,
        AVG(pts_ppr) as season_avg_pts,
        AVG(rush_yd) as season_avg_rush_yds,
        AVG(rec) as season_avg_receptions
    FROM weekly_stats
    WHERE season = {current_season}
      AND player_id IN {id_placeholder}
    GROUP BY player_id
    """
    
    history_df = pd.read_sql(query, conn)
    df = pd.merge(df, history_df, on='player_id', how='left').fillna(0)
    
    # 2. THE ALGORITHM
    
    # A. The Baseline (Heavier on History than QBs)
    # RBs depend less on "Team Scoring" and more on "Does Coach give me the ball?"
    vegas_proxy = df['vegas_implied_total'] * 0.7 
    df['base_projection'] = (vegas_proxy * 0.3) + (df['season_avg_pts'] * 0.7)
    
    # B. The "Game Script" Adjustment (Spread)
    # Theory: Favorites Run. Underdogs Pass.
    # If Spread is -7.0 (Favorite), we ADD points.
    # If Spread is +7.0 (Underdog), we SUBTRACT points.
    # Formula: Spread * -0.2 (e.g., -7 * -0.2 = +1.4 point boost)
    df['script_bonus'] = df['spread'] * -0.15
    
    # C. The "Anti-Funnel" Rule (Pass Funnel Rate)
    # If rank_funnel is High (1-10), it means the defense forces passing. Bad for RBs.
    # We check if the columns exist first (to avoid crashes if Secret Sauce failed)
    if 'rank_funnel' in df.columns:
        # Rank 1 = Highest Pass Funnel (Worst for RBs)
        df.loc[df['rank_funnel'] < 10, 'base_projection'] -= 1.5
        # Rank 25-32 = Run Funnel (Great for RBs)
        df.loc[df['rank_funnel'] > 25, 'base_projection'] += 1.5

    # D. The "Bellcow" Bonus (Volume Safety)
    # If a guy catches 4+ passes a game, he is immune to bad game scripts.
    df.loc[df['season_avg_receptions'] > 3.5, 'base_projection'] += 2.0
    
    # 3. FINAL SCORE
    df['projected_score'] = df['base_projection'] + df['script_bonus']
    
    return df