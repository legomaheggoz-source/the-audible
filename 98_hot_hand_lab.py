import sqlite3
import pandas as pd
import numpy as np

DB_NAME = "gridiron.db"

def test_hot_hand_theory(position='WR'):
    print(f"--- 🔥 HOT HAND LAB: Testing Recency Bias for {position} ---")
    conn = sqlite3.connect(DB_NAME)
    
    # 1. GET ALL STATS
    # We need every game for every player to calculate rolling averages
    query = f"""
    SELECT 
        p.player_id,
        p.full_name,
        w.season,
        w.week,
        w.pts_ppr
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    WHERE p.position = '{position}'
      AND w.season = 2025 -- Let's look at the current season data
    ORDER BY p.player_id, w.week
    """
    
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("❌ No stats found.")
        conn.close()
        return

    print(f"   📊 Analyzing {len(df)} game performances...")

    # 2. CALCULATE METRICS (The Hard Part)
    # We need to shift data so we are comparing "Previous Stats" to "Current Week Score"
    
    results = []
    
    # Group by player so we don't mix stats between players
    for pid, group in df.groupby('player_id'):
        group = group.sort_values('week')
        
        # We need at least 4 weeks of data to test this (3 weeks history + 1 target week)
        if len(group) < 4:
            continue
            
        # Iterate through the season (simulate each week)
        # Start at 4th game (index 3) so we have 3 prior games to look at
        for i in range(3, len(group)):
            current_week_row = group.iloc[i]
            target_score = current_week_row['pts_ppr'] # The actual score we want to predict
            
            # --- METRIC A: SEASON AVERAGE (Up to last week) ---
            # All games before this week
            prior_games = group.iloc[:i] 
            season_avg = prior_games['pts_ppr'].mean()
            
            # --- METRIC B: LAST 3 WEEKS (Simple Avg) ---
            last_3 = group.iloc[i-3:i]
            last_3_avg = last_3['pts_ppr'].mean()
            
            # --- METRIC C: HOT HAND (Weighted Avg) ---
            # Week -3 (oldest) gets weight 1
            # Week -2 gets weight 2
            # Week -1 (most recent) gets weight 3
            # Total weight = 1+2+3 = 6
            weights = np.array([1, 2, 3])
            weighted_avg = np.average(last_3['pts_ppr'], weights=weights)
            
            results.append({
                'player': current_week_row['full_name'],
                'week': current_week_row['week'],
                'actual_points': target_score,
                'season_avg': season_avg,
                'last_3_avg': last_3_avg,
                'weighted_avg': weighted_avg
            })
            
    results_df = pd.DataFrame(results)
    
    # 3. THE VERDICT (Correlation)
    print("\n   🏆 CORRELATION REPORT (Which metric predicts points best?)")
    print(f"   [A] Season Average:   {results_df['season_avg'].corr(results_df['actual_points']):.4f}")
    print(f"   [B] Last 3 Avg:       {results_df['last_3_avg'].corr(results_df['actual_points']):.4f}")
    print(f"   [C] Weighted Hot Hand:{results_df['weighted_avg'].corr(results_df['actual_points']):.4f}")
    
    # 4. VISUALIZE THE DIFFERENCE (Luther Burden Check)
    print("\n   🕵️ CASE STUDY: Luther Burden Trend")
    burden = results_df[results_df['player'].str.contains("Burden")]
    if not burden.empty:
        print(burden[['week', 'actual_points', 'season_avg', 'weighted_avg']].tail(3))

    conn.close()

if __name__ == "__main__":
    test_hot_hand_theory(position='WR')