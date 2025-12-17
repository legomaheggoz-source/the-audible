import requests
import sqlite3
import pandas as pd

DB_NAME = "gridiron.db"
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

def update_player_database():
    print("Fetching ALL NFL players from Sleeper (This is a 5MB download)...")
    
    # 1. Get the Raw Data
    response = requests.get(SLEEPER_PLAYERS_URL)
    data = response.json()
    
    # 2. Convert to DataFrame for easy filtering
    # The API returns a dictionary where Key = ID. We want Rows.
    df = pd.DataFrame.from_dict(data, orient='index')
    
    # 3. Filter for Relevance
    # We only want active players in skill positions
    relevant_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
    
    # Filter: Active players only AND inside our position list
    mask = (df['active'] == True) & (df['position'].isin(relevant_positions))
    df_clean = df[mask].copy()
    
    # 4. Select Columns to match our SQL Schema
    # Note: Sleeper calls it 'player_id', 'full_name', etc.
    cols_to_keep = ['player_id', 'full_name', 'position', 'team', 'age', 'depth_chart_order', 'injury_status', 'status']
    
    # Safety: Ensure columns exist (sometimes 'depth_chart_order' is missing for free agents)
    for col in cols_to_keep:
        if col not in df_clean.columns:
            df_clean[col] = None
            
    df_final = df_clean[cols_to_keep]
    
    print(f"Found {len(df_final)} active skill players.")
    
    # 5. Save to SQLite
    conn = sqlite3.connect(DB_NAME)
    
    # if_exists='replace' will refresh the roster every time we run this
    df_final.to_sql('players', conn, if_exists='replace', index=False)
    
    conn.close()
    print("✅ Players table updated successfully.")

if __name__ == "__main__":
    update_player_database()