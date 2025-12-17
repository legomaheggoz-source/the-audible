import pandas as pd
import sqlite3
import requests
import io

# --- CONFIGURATION ---
DB_NAME = "gridiron.db"
ODDS_SOURCE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

def fetch_vegas_odds():
    print("--- STEP 1: FETCHING VEGAS ODDS ---")
    
    # 1. DOWNLOAD
    print("   -> Downloading schedule & odds from NFLVerse...")
    try:
        s = requests.get(ODDS_SOURCE_URL).content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')))
    except Exception as e:
        print(f"❌ Error downloading odds: {e}")
        return

    # 2. FILTER & CLEAN
    target_seasons = [2023, 2024, 2025]
    df = df[df['season'].isin(target_seasons)].copy()
    
    # --- THE FIX: FLIP THE SPREAD SIGN ---
    # The raw data has Positive = Home Underdog.
    # We want Negative = Home Favorite (Standard Betting Notation).
    # This ensures Favorites get Higher Implied Totals.
    df['spread_line'] = df['spread_line'] * -1
    
    matchups = []
    for _, row in df.iterrows():
        # Home Perspective
        # Spread is now correct (e.g., KC -4.0).
        # Formula: 26.5 - (-2) = 28.5 (High Score for Favorite).
        matchups.append({
            'season': row['season'], 'week': row['week'],
            'team': row['home_team'], 'opponent': row['away_team'],
            'vegas_implied_total': (row['total_line'] / 2) - (row['spread_line'] / 2),
            'spread': row['spread_line']
        })
        
        # Away Perspective
        # If Home is -4.0, Away is +4.0.
        away_spread = row['spread_line'] * -1
        matchups.append({
            'season': row['season'], 'week': row['week'],
            'team': row['away_team'], 'opponent': row['home_team'],
            'vegas_implied_total': (row['total_line'] / 2) - (away_spread / 2),
            'spread': away_spread 
        })
        
    df_clean = pd.DataFrame(matchups)
    
    # 3. MAPPER (Standardize Team Names)
    nflverse_to_sleeper = {
        'ARZ': 'ARI', 'BLT': 'BAL', 'CLV': 'CLE', 'HST': 'HOU', 
        'SD': 'LAC', 'SL': 'STL', 'OAK': 'LV',  'LVR': 'LV',
        'JAC': 'JAX', 'WSH': 'WAS', 'LA': 'LAR'
    }
    df_clean['team'] = df_clean['team'].replace(nflverse_to_sleeper)
    df_clean['opponent'] = df_clean['opponent'].replace(nflverse_to_sleeper)

    conn = sqlite3.connect(DB_NAME)
    df_clean.to_sql('matchups', conn, if_exists='replace', index=False)
    conn.close()
    print(f"   ✅ Odds loaded and corrected for {len(df_clean)} games.")

def generate_defensive_ranks():
    print("\n--- STEP 2: GENERATING DEFENSIVE RANKINGS (FALLBACK MODE) ---")
    conn = sqlite3.connect(DB_NAME)
    
    query = """
    SELECT 
        w.season,
        m.opponent as team,
        p.position,
        AVG(w.pts_ppr) as avg_pts_allowed
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
    
    WHERE p.team IS NOT NULL
    GROUP BY w.season, m.opponent, p.position
    """
    
    try:
        df_def = pd.read_sql(query, conn)
        
        if df_def.empty:
            print("   ⚠️ WARNING: DataFrame empty.")
        else:
            df_def['def_rank'] = df_def.groupby(['season', 'position'])['avg_pts_allowed'].rank(ascending=True)
            df_def.to_sql('defensive_stats', conn, if_exists='replace', index=False)
            print(f"   ✅ Defensive rankings calculated for {len(df_def)} rows.")
            
    except Exception as e:
        print(f"   ❌ SQL Error: {e}")
        
    conn.close()

if __name__ == "__main__":
    fetch_vegas_odds()
    generate_defensive_ranks()