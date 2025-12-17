import requests
import pandas as pd
import sqlite3
import time

# --- CONFIGURATION ---
DB_NAME = "gridiron.db"
TARGET_SEASONS = [2023, 2024, 2025]
WEEKS_TO_FETCH = list(range(1, 19))
BASE_URL = "https://api.sleeper.app/v1/stats/nfl/regular"

def fetch_weekly_stats(season, week):
    url = f"{BASE_URL}/{season}/{week}"
    print(f"   -> Downloading Season {season} Week {week}...", end="")
    
    try:
        response = requests.get(url)
        if response.status_code != 200: 
            print(f" ❌ Failed (Status: {response.status_code})")
            return None
        data = response.json()
        
        # Sleeper sends data like: {"4034": {"pass_yd": 200, "team": "SF"}, ...}
        df = pd.DataFrame.from_dict(data, orient='index')
        
        if df.empty:
            print(" ⚠️ Empty JSON received.")
            return None

        # Reset index to get player_id
        df = df.reset_index().rename(columns={'index': 'player_id'})
        
        df['season'] = season
        df['week'] = week
        print(" ✅ OK")
        return df
        
    except Exception as e:
        print(f" ❌ Error: {e}")
        return None

def update_history():
    print(f"--- STARTING HISTORY ETL (FIXED MAPPING) ---")
    conn = sqlite3.connect(DB_NAME)
    
    for season in TARGET_SEASONS:
        print(f"\n📅 PROCESSING SEASON {season}...")
        for week in WEEKS_TO_FETCH:
            df_week = fetch_weekly_stats(season, week)
            
            if df_week is not None and not df_week.empty:
                final_df = pd.DataFrame()
                
                # 1. CORE IDENTIFIERS
                final_df['player_id'] = df_week['player_id']
                final_df['season'] = df_week['season']
                final_df['week'] = df_week['week']
                
                # 2. TEAM (The Fix for the Missing Vegas Data)
                if 'team' in df_week.columns:
                    final_df['team'] = df_week['team']
                else:
                    final_df['team'] = None # Free agents/Inactive players
                
                # 3. STATS MAPPING (The Fix for the Error)
                # Left Side = Database Column Name (Must match 01_setup_db.py)
                # Right Side = Sleeper API Key (What comes from the JSON)
                cols_map = {
                    'pass_yd': 'pass_yd',
                    'pass_td': 'pass_td',
                    'rush_yd': 'rush_yd',
                    'rush_td': 'rush_td',
                    'rec': 'rec',
                    'rec_yd': 'rec_yd',
                    'rec_td': 'rec_td',
                    'pts_ppr': 'pts_ppr'
                }
                
                # Initialize columns with 0.0 first
                for sql_col in cols_map.keys():
                    final_df[sql_col] = 0.0

                # Fill with data where it exists
                for sql_col, sleeper_key in cols_map.items():
                    if sleeper_key in df_week.columns:
                        final_df[sql_col] = df_week[sleeper_key]
                
                # 4. OPPONENT (Placeholder - Filled in Step 4)
                final_df['opponent'] = None
                
                # 5. SAVE
                try:
                    final_df.to_sql('weekly_stats', conn, if_exists='append', index=False)
                except Exception as e:
                    print(f"\n❌ CRITICAL ERROR on {season} Week {week}: {e}")
                    print(f"   Columns attempting to save: {list(final_df.columns)}")
                    conn.close()
                    return 

            time.sleep(0.3)
            
    conn.close()
    print("--- HISTORY UPDATE COMPLETE ---")

if __name__ == "__main__":
    update_history()