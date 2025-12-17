import sqlite3
import pandas as pd
import numpy as np

DB_NAME = "gridiron.db"

def test_combo_logic(position='WR'):
    print(f"--- 🧬 COMBO LAB: Testing Volume-Validated Hot Hand ({position}) ---")
    conn = sqlite3.connect(DB_NAME)
    
    query = f"""
    SELECT p.player_id, p.full_name, w.season, w.week, w.rec, w.pts_ppr
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    WHERE p.position = '{position}' AND w.season = 2025
    ORDER BY p.player_id, w.week
    """
    df = pd.read_sql(query, conn)
    
    if df.empty: return

    results = []
    
    for pid, group in df.groupby('player_id'):
        group = group.sort_values('week')
        if len(group) < 4: continue
            
        for i in range(3, len(group)):
            current_row = group.iloc[i]
            target_score = current_row['pts_ppr']
            
            # --- INPUTS ---
            # 1. Season Baseline
            season_pts_avg = group.iloc[:i]['pts_ppr'].mean()
            season_rec_avg = group.iloc[:i]['rec'].mean()
            
            # 2. Recent Trends (Last 3 Weeks)
            last_3_pts_avg = group.iloc[i-3:i]['pts_ppr'].mean()
            last_3_rec_avg = group.iloc[i-3:i]['rec'].mean()
            
            # --- THE COMBO LOGIC (The "Smart" Prediction) ---
            # We calculate a 'Volume Ratio'. 1.0 = Normal. >1.0 = Heating Up.
            # Avoid division by zero by using a small epsilon or max(avg, 0.1)
            safe_season_rec = max(season_rec_avg, 0.5)
            vol_ratio = last_3_rec_avg / safe_season_rec
            
            # THE ALGORITHM:
            # If Volume is trending up (> 110% of usual), we trust the Hot Hand (Recent Points).
            # Otherwise, we trust the Season Average (Regression to Mean).
            if vol_ratio > 1.1:
                smart_prediction = last_3_pts_avg # Trust the heat!
            else:
                smart_prediction = season_pts_avg # Trust the history.
                
            results.append({
                'actual_points': target_score,
                'season_avg': season_pts_avg,
                'recent_vol': last_3_rec_avg,
                'smart_prediction': smart_prediction
            })
            
    res_df = pd.DataFrame(results)
    
    print("\n   🏆 CORRELATION REPORT")
    print(f"   [A] Season Average (Baseline):      {res_df['season_avg'].corr(res_df['actual_points']):.4f}")
    print(f"   [B] Recent Volume (The Signal):     {res_df['recent_vol'].corr(res_df['actual_points']):.4f}")
    print(f"   [D] Smart Hot Hand (The Combo):     {res_df['smart_prediction'].corr(res_df['actual_points']):.4f}")
    
    conn.close()

if __name__ == "__main__":
    test_combo_logic('WR')