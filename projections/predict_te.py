import pandas as pd

def predict_te(df, conn, current_season):
    print("   🧠 Running Specialist Model: TE Red Zone & Matchup Logic...")
    
    # 1. GET HISTORY
    player_ids = tuple(df['player_id'].unique())
    if len(player_ids) == 1:
        id_placeholder = f"('{player_ids[0]}')"
    else:
        id_placeholder = str(player_ids)
        
    query = f"""
    SELECT 
        player_id,
        AVG(pts_ppr) as season_avg_pts
    FROM weekly_stats
    WHERE season = {current_season}
      AND player_id IN {id_placeholder}
    GROUP BY player_id
    """
    
    history_df = pd.read_sql(query, conn)
    df = pd.merge(df, history_df, on='player_id', how='left').fillna(0)
    
    # 2. THE ALGORITHM
    
    # A. The Baseline (Heavy on History)
    # Most TEs are 6-point players or 12-point players. They don't fluctuate as wildly as WRs.
    df['base_projection'] = df['season_avg_pts']
    
    # B. The "Green Zone" Bonus (Bad Defense)
    # Defenses Ranked 25-32 against TEs leak points.
    df.loc[df['opponent_rank'] > 24, 'base_projection'] += 2.0
    df.loc[df['opponent_rank'] > 30, 'base_projection'] += 1.0 # Cumulative +3.0 for worst defenses
    
    # C. The "Red Zone" Bonus (High Vegas Total)
    # TEs need TDs. High totals = High TD probability.
    # If Vegas implies 24+ points for the team...
    df.loc[df['vegas_implied_total'] > 24, 'base_projection'] += 1.5
    
    # D. The "Ghost" Penalty (Low Volume)
    # If a guy averages < 5 points, he is a blocking TE. Don't project him to break out.
    df.loc[df['season_avg_pts'] < 5.0, 'base_projection'] -= 2.0
    
    df['projected_score'] = df['base_projection']
    
    return df