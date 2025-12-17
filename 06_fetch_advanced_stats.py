import pandas as pd
import sqlite3
import numpy as np

DB_NAME = "gridiron.db"
# PBP Data (The Stats)
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
# Roster Data (The Translator: IDs -> Full Names)
ROSTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{}.csv"

TARGET_SEASONS = [2024, 2025] 

def update_advanced_stats():
    print("--- 🚀 STARTING ADVANCED ENGINE UPGRADE (v2) ---")
    conn = sqlite3.connect(DB_NAME)
    
    all_def_stats = []
    all_player_profiles = []

    for season in TARGET_SEASONS:
        print(f"\n   -> Processing Season {season}...")
        
        # 1. Download Roster (The Rosetta Stone)
        try:
            print("      Fetching Roster for Name Translation...")
            df_roster = pd.read_csv(ROSTER_URL.format(season))
            # We need: gsis_id (link to PBP) -> full_name (link to Sleeper)
            df_roster = df_roster[['gsis_id', 'full_name']].dropna()
        except Exception as e:
            print(f"      ⚠️ Roster download failed: {e}")
            continue

        # 2. Download Play-by-Play
        try:
            print("      Fetching Play-by-Play Data...")
            df = pd.read_parquet(PBP_URL.format(season))
        except:
            print(f"      ⚠️ PBP download failed. Skipping.")
            continue
            
        # --- A. PROFILE THE DEFENSES (Same as before) ---
        print(f"      Analyzing Defensive Styles...")
        df_plays = df.dropna(subset=['epa', 'defteam'])
        
        # Deep Pass (>15 ay)
        deep_mask = (df_plays['play_type'] == 'pass') & (df_plays['air_yards'] > 15)
        df_deep = df_plays[deep_mask].groupby('defteam')['epa'].mean().reset_index().rename(columns={'epa': 'epa_allowed_deep'})
        
        # Short Pass (<=15 ay)
        short_mask = (df_plays['play_type'] == 'pass') & (df_plays['air_yards'] <= 15)
        df_short = df_plays[short_mask].groupby('defteam')['epa'].mean().reset_index().rename(columns={'epa': 'epa_allowed_short'})
        
        # Run
        rush_mask = (df_plays['play_type'] == 'run')
        df_rush = df_plays[rush_mask].groupby('defteam')['epa'].mean().reset_index().rename(columns={'epa': 'epa_allowed_run'})
        
        # Merge & Rank
        df_def = pd.merge(df_deep, df_short, on='defteam', how='outer')
        df_def = pd.merge(df_def, df_rush, on='defteam', how='outer')
        df_def['season'] = season
        
        # Ascending=True because Negative EPA is Good for defense
        df_def['rank_vs_deep'] = df_def['epa_allowed_deep'].rank(ascending=True)
        df_def['rank_vs_short'] = df_def['epa_allowed_short'].rank(ascending=True)
        df_def['rank_vs_run'] = df_def['epa_allowed_run'].rank(ascending=True)
        
        all_def_stats.append(df_def)

        # --- B. PROFILE THE PLAYERS (Fixed Name Logic) ---
        print(f"      Profiling Player Styles (aDOT)...")
        
        # Filter for passes
        pass_mask = (df_plays['play_type'] == 'pass') & (df_plays['receiver_player_id'].notnull())
        df_targets = df_plays[pass_mask].copy()
        
        # JOIN with ROSTER to get real 'full_name'
        # PBP column 'receiver_player_id' matches Roster column 'gsis_id'
        df_targets = pd.merge(df_targets, df_roster, left_on='receiver_player_id', right_on='gsis_id', how='inner')
        
        # Now group by the CLEAN 'full_name'
        df_style = df_targets.groupby(['full_name', 'posteam']).agg({
            'air_yards': 'mean',
            'epa': 'count' # Count targets
        }).reset_index()
        
        df_style.rename(columns={'air_yards': 'adot', 'epa': 'targets', 'full_name': 'receiver_player_name'}, inplace=True)
        df_style = df_style[df_style['targets'] > 10] # Filter noise
        df_style['season'] = season
        
        all_player_profiles.append(df_style)

    # --- SAVE TO DB ---
    conn = sqlite3.connect(DB_NAME)
    
    if all_def_stats:
        final_def = pd.concat(all_def_stats)
        final_def.to_sql('advanced_defensive_stats', conn, if_exists='replace', index=False)
        print("   ✅ Saved table: advanced_defensive_stats")
        
    if all_player_profiles:
        final_prof = pd.concat(all_player_profiles)
        final_prof.to_sql('player_styles', conn, if_exists='replace', index=False)
        print("   ✅ Saved table: player_styles (With corrected names)")
        
    conn.close()

if __name__ == "__main__":
    update_advanced_stats()