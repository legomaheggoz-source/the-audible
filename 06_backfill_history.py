import sqlite3
import pandas as pd
import importlib.util
import sys
import os

DB_NAME = "gridiron.db"

# --- DYNAMIC IMPORT MAGIC ---
file_path = "05_make_projections.py"
module_name = "make_projections"
if not os.path.exists(file_path): sys.exit(1)
spec = importlib.util.spec_from_file_location(module_name, file_path)
make_proj = importlib.util.module_from_spec(spec)
sys.modules[module_name] = make_proj
spec.loader.exec_module(make_proj)
# -----------------------------

def time_travel_backfill():
    print("--- ⏳ INITIATING TIME TRAVEL SEQUENCE (Active Players Only) ---")
    conn = sqlite3.connect(DB_NAME)
    
    try:
        max_week = pd.read_sql("SELECT MAX(week) FROM weekly_stats WHERE season=2025", conn).iloc[0,0]
    except:
        return

    if not max_week: return

    print(f"   📅 Found data up to Week {max_week}. Regenerating history...")

    for week in range(2, max_week + 1):
        # 1. IDENTIFY WHO PLAYED THIS WEEK
        # FIX: Removed 'w.pass_att' check to avoid column errors. 
        # Checking pts_ppr != 0 is usually sufficient to catch starters.
        query = f"""
        SELECT w.player_id, p.position 
        FROM weekly_stats w
        JOIN players p ON w.player_id = p.player_id
        WHERE w.season = 2025 AND w.week = {week} 
          AND w.pts_ppr != 0
        """
        active_df = pd.read_sql(query, conn)
        
        # Create a map: {'QB': [id1, id2], 'RB': [id3...]}
        allowed_map = {}
        for pos in ['QB', 'RB', 'WR', 'TE']:
            allowed_map[pos] = active_df[active_df['position'] == pos]['player_id'].tolist()
        
        print(f"   ⚙️ GENERATING WEEK {week} (Projections for {len(active_df)} active players)...")
        
        try:
            make_proj.run_all_projections(target_week=week, allowed_players_map=allowed_map)
        except Exception as e:
            print(f"   ⚠️ Failed Week {week}: {e}")
            import traceback
            traceback.print_exc()

    conn.close()
    print("\n   ✅ TIME TRAVEL COMPLETE.")

if __name__ == "__main__":
    time_travel_backfill()