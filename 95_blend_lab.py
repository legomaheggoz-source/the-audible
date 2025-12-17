import sqlite3
import pandas as pd
import numpy as np

DB_NAME = "gridiron.db"

def find_golden_ratio(position='WR'):
    print(f"--- ⚖️ BLEND LAB: Finding the Golden Ratio for {position} ---")
    conn = sqlite3.connect(DB_NAME)
    
    # 1. GET DATA
    query = f"""
    SELECT p.player_id, w.week, w.rec, w.pts_ppr
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    WHERE p.position = '{position}' AND w.season = 2025
    ORDER BY p.player_id, w.week
    """
    df = pd.read_sql(query, conn)
    
    if df.empty: return

    results = []
    
    # 2. CALCULATE METRICS
    for pid, group in df.groupby('player_id'):
        group = group.sort_values('week')
        if len(group) < 5: continue
            
        for i in range(4, len(group)):
            current_row = group.iloc[i]
            actual_points = current_row['pts_ppr']
            
            # Metric A: Season Average (History)
            season_avg = group.iloc[:i]['pts_ppr'].mean()
            
            # Metric B: Recent Average (Last 3 Weeks)
            recent_avg = group.iloc[i-3:i]['pts_ppr'].mean()
            
            # Metric C: Recent Volume (Receptions)
            recent_vol = group.iloc[i-3:i]['rec'].mean()
            
            results.append({
                'actual': actual_points,
                'season_avg': season_avg,
                'recent_avg': recent_avg,
                'recent_vol': recent_vol
            })
            
    df_res = pd.DataFrame(results)
    
    print(f"   📊 Analyzed {len(df_res)} projections.")
    print("\n   🧪 TESTING BLEND RATIOS (Season vs. Recency)")
    print(f"   {'Weight (Seas/Rec)':<20} {'Correlation':<10}")
    print("-" * 35)

    best_corr = 0
    best_weight = 0

    # Test blends: 100/0, 90/10, 80/20... 0/100
    for r in range(0, 101, 10):
        recency_weight = r / 100.0
        season_weight = 1.0 - recency_weight
        
        # Calculate the Blended Projection
        df_res['blended_proj'] = (df_res['season_avg'] * season_weight) + (df_res['recent_avg'] * recency_weight)
        
        # Check Correlation
        corr = df_res['blended_proj'].corr(df_res['actual'])
        
        # Star the winner
        marker = ""
        if corr > best_corr:
            best_corr = corr
            best_weight = recency_weight
            marker = "⭐ NEW LEADER"
            
        print(f"   {int(season_weight*100)}% / {int(recency_weight*100)}%      {corr:.5f} {marker}")

    print(f"\n   🏆 THE WINNER: {int((1-best_weight)*100)}% History / {int(best_weight*100)}% Recency")
    
    # 3. VOLUME CHECK (Does Volume justify higher recency weight?)
    # Let's filter for players with HIGH recent volume (> 6 recs/game) and re-run
    print("\n   🔊 HIGH VOLUME SUB-TEST (Players with > 6 recent recs)")
    high_vol_df = df_res[df_res['recent_vol'] > 6.0].copy()
    
    if not high_vol_df.empty:
        # Quick check of 50/50 blend on high volume guys
        hv_corr_season = high_vol_df['season_avg'].corr(high_vol_df['actual'])
        hv_corr_recent = high_vol_df['recent_avg'].corr(high_vol_df['actual'])
        print(f"   - Season Avg Corr: {hv_corr_season:.4f}")
        print(f"   - Recent Avg Corr: {hv_corr_recent:.4f}")
        if hv_corr_recent > hv_corr_season:
            print("   ✅ CONCLUSION: For Target Hogs, Recency IS better.")
        else:
            print("   ❌ CONCLUSION: Even for Target Hogs, History wins.")

    conn.close()

if __name__ == "__main__":
    find_golden_ratio('WR')