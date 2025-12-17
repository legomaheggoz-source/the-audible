import sqlite3
import pandas as pd

DB_NAME = "gridiron.db"

def check_player_status(player_name):
    print(f"--- 🕵️ STATUS CHECK: {player_name} ---")
    conn = sqlite3.connect(DB_NAME)
    
    # 1. Check the 'players' table (Reference Data)
    query = f"""
    SELECT player_id, full_name, team, position, status, depth_chart_order
    FROM players
    WHERE full_name LIKE '%{player_name}%'
    """
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("❌ Player not found in 'players' table.")
    else:
        print("Found in Players Table:")
        print(df.to_string(index=False))
        
        # 2. Check the 'weekly_stats' (Do we have recent data?)
        pid = df.iloc[0]['player_id']
        stats_query = f"""
        SELECT season, week, team, rec, rec_yd, pts_ppr
        FROM weekly_stats
        WHERE player_id = '{pid}' AND season = 2025
        ORDER BY week DESC
        LIMIT 3
        """
        stats_df = pd.read_sql(stats_query, conn)
        print("\nRecent Stats (Last 3 Weeks):")
        if stats_df.empty:
            print("   (No stats found)")
        else:
            print(stats_df.to_string(index=False))

    conn.close()

if __name__ == "__main__":
    check_player_status("Cedric Tillman")
    check_player_status("Luther Burden") # Let's check him too