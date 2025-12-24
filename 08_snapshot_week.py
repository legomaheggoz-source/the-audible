import sqlite3
import pandas as pd
import os
from datetime import datetime
from config import CURRENT_SEASON, CURRENT_WEEK, DB_NAME

def snapshot_week():
    print(f"📸 Snapping projections for Season {CURRENT_SEASON}, Week {CURRENT_WEEK}...")
    
    # 1. Connect to DB
    conn = sqlite3.connect(DB_NAME)
    
    # 2. Get the data
    query = f"""
    SELECT * FROM predictions_history 
    WHERE season = {CURRENT_SEASON} AND week = {CURRENT_WEEK}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print(f"⚠️ No projections found for Week {CURRENT_WEEK}. Run 05_make_projections.py first.")
        return

    # 3. Create 'snapshots' folder if it doesn't exist
    if not os.path.exists("snapshots"):
        os.makedirs("snapshots")
        
    # 4. Save to CSV with a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"snapshots/week_{CURRENT_WEEK}_final_{timestamp}.csv"
    
    df.to_csv(filename, index=False)
    
    print(f"✅ SUCCESS: Archived {len(df)} player projections.")
    print(f"📂 Saved to: {filename}")
    print("🔒 You are now safe to advance to the next week.")

if __name__ == "__main__":
    snapshot_week()