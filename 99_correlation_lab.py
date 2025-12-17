import sqlite3
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
DB_NAME = "gridiron.db"

def analyze_correlations(position='QB'):
    print(f"--- 🔬 ANALYZING CORRELATIONS FOR {position} ---")
    conn = sqlite3.connect(DB_NAME)
    
    # 1. THE QUERY (Updated to match new DB Schema)
    # We select 'pts_ppr' instead of 'fantasy_points_ppr'
    query = f"""
    SELECT 
        w.pts_ppr as points,            -- <--- THE FIX
        m.vegas_implied_total,
        m.spread,
        s.def_sack_rate,
        s.def_pass_funnel_rate
        
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    -- Fallback Join: Use p.team (Current) instead of w.team (Historical)
    JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
    LEFT JOIN secret_sauce_def s ON w.season = s.season AND m.opponent = s.opponent
    
    WHERE p.position = '{position}'
      AND w.pts_ppr > 5               -- <--- THE FIX (Filter out backups)
      AND m.vegas_implied_total IS NOT NULL
    """
    
    try:
        df = pd.read_sql(query, conn)
        
        if df.empty:
            print("   ⚠️ No data found. (Check if 'matchups' or 'weekly_stats' are empty)")
            conn.close()
            return

        # 2. THE CORRELATION MATRIX
        print(f"\n   📊 Data Points: {len(df)}")
        corr = df.corr()
        print("\n--- CORRELATION MATRIX (What matters?) ---")
        print(corr['points'].sort_values(ascending=False))
        
        # 3. VISUALIZATION (Optional - Comment out if it freezes)
        plt.figure(figsize=(10, 6))
        sns.regplot(x='vegas_implied_total', y='points', data=df, scatter_kws={'alpha':0.3})
        plt.title(f"{position}: Vegas Implied Total vs Fantasy Points")
        plt.xlabel("Team Implied Total (Vegas)")
        plt.ylabel("Fantasy Points")
        plt.grid(True, alpha=0.3)
        plt.show()

    except Exception as e:
        print(f"   ❌ Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    # You can change this to 'RB' or 'WR' to test other positions
    analyze_correlations(position='WR')