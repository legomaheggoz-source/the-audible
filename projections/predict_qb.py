import pandas as pd

def predict_qb(df, conn, current_season):
    print("   🧠 Running Specialist Model: QB Alpha Logic...")
    
    # 1. GET PLAYER HISTORY
    # We need Passing vs Rushing split to identify "Alpha" types
    player_ids = tuple(df['player_id'].unique())
    if len(player_ids) == 1: id_str = f"('{player_ids[0]}')"
    else: id_str = str(player_ids)
    
    query = f"""
    SELECT 
        player_id,
        AVG(pts_ppr) as season_avg_pts,
        AVG(pass_yd) as avg_pass_yd,
        AVG(rush_yd) as avg_rush_yd,
        MAX(pts_ppr) as ceiling_score
    FROM weekly_stats
    WHERE season = {current_season} AND player_id IN {id_str}
    GROUP BY player_id
    """
    
    history_df = pd.read_sql(query, conn)
    df = pd.merge(df, history_df, on='player_id', how='left').fillna(0)
    
    # 2. THE ALGORITHM
    
    # A. The Baseline (Shift to 40% Vegas / 60% History)
    # QBs drive the score. If Vegas predicts 28 pts, the QB is usually the reason.
    vegas_implied_score = df['vegas_implied_total'] * 0.8  # Crude proxy for QB points share
    df['base_projection'] = (vegas_implied_score * 0.40) + (df['season_avg_pts'] * 0.60)
    
    # B. The "Konami Alpha" Multiplier (Ceiling Adjuster)
    # Elite runners don't just add points; they multiply the offense's efficiency.
    df['konami_multiplier'] = 1.0
    
    # Tier 1: The Gods (Lamar, Allen, Hurts)
    df.loc[df['avg_rush_yd'] > 40.0, 'konami_multiplier'] = 1.15
    
    # Tier 2: The Scramblers (Drake Maye, Kyler)
    df.loc[(df['avg_rush_yd'] > 20.0) & (df['avg_rush_yd'] <= 40.0), 'konami_multiplier'] = 1.05
    
    # Apply Multiplier
    df['base_projection'] = df['base_projection'] * df['konami_multiplier']
    
    # C. The "Shootout" Bonus (High Total)
    # If the game total is > 48, QBs throw more. Pocket passers (Baker/JJ) need this.
    # Note: We use 'vegas_implied_total' * 2 roughly to get Game Total, or rely on just team total
    df.loc[df['vegas_implied_total'] > 25.5, 'base_projection'] += 2.0
    
    # D. Matchup Tweaks (Slight Fade for Tough Defenses)
    # If opponent is Rank 1-5 (Elite Defense), cap the ceiling.
    df.loc[df['opponent_rank'] <= 5, 'base_projection'] -= 1.5

    df['projected_score'] = df['base_projection']
    
    return df