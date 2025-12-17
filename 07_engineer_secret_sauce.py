import sqlite3
import pandas as pd

# --- CONFIGURATION ---
DB_NAME = "gridiron.db"

def engineer_defense_sauce():
    print("--- 🧪 ENGINEERING SECRET SAUCE DEFENSE ---")
    conn = sqlite3.connect(DB_NAME)

    # 1. AGGREGATE STATS BY OPPONENT
    # We want to know how every NFL team performs as a DEFENSE.
    # Logic: Look at every game where 'm.opponent' was the defense.
    
    # Note: We use the "Fallback Mode" logic (p.team) to ensure we find the games.
    query = """
    SELECT 
        w.season,
        m.opponent as team,  -- The team acting as the Defense
        SUM(w.pass_yd) as total_pass_yds,
        SUM(w.rush_yd) as total_rush_yds,
        SUM(w.pass_td) as total_pass_tds,
        COUNT(w.player_id) as games_tracked
    FROM weekly_stats w
    JOIN players p ON w.player_id = p.player_id
    JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
    
    WHERE p.team IS NOT NULL
    GROUP BY w.season, m.opponent
    """
    
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("   ❌ Error: No stats found. Check your weekly_stats and matchups.")
        conn.close()
        return

    # 2. CALCULATE THE METRICS
    print(f"   📊 Analyzing {len(df)} defensive seasons...")
    
    # A. PASS FUNNEL RATE
    # Formula: Passing Yards Allowed / Total Yards Allowed
    # High % (e.g., 75%) means teams abandon the run and throw on them.
    df['total_yds'] = df['total_pass_yds'] + df['total_rush_yds']
    df['def_pass_funnel_rate'] = df['total_pass_yds'] / df['total_yds']
    
    # B. SACK RATE (Simplified Proxy)
    # Since we don't have raw 'sacks' in our simple table yet, 
    # we will use "Pass TDs Allowed per Yard" as a proxy for "Defensive Toughness"
    # or just placeholder logic if you want to add sacks later.
    # For now, let's create a "Bend Don't Break" metric:
    # Yards allowed per TD. High number = Good Defense (Make them drive the field).
    df['def_sack_rate'] = df['total_pass_yds'] / (df['total_pass_tds'] + 1) # Avoid div/0
    
    # 3. CALCULATE RANKS (1 = Best for Fantasy, 32 = Worst)
    # For Funnel: Rank 1 = Highest % (Good for WRs)
    df['rank_funnel'] = df.groupby('season')['def_pass_funnel_rate'].rank(ascending=False)
    
    # For "Sack Rate" (Toughness): Rank 1 = Lowest Yards/TD (Stingy Defense)
    df['rank_sack_rate'] = df.groupby('season')['def_sack_rate'].rank(ascending=True)
    
    # 4. SAVE TO DB
    # We only keep the columns we need for the correlation lab
    final_df = df[['season', 'team', 'def_sack_rate', 'rank_sack_rate', 
                   'def_pass_funnel_rate', 'rank_funnel']].copy()
    
    # Rename 'team' to 'opponent' so it joins easily in the Lab
    final_df = final_df.rename(columns={'team': 'opponent'})
    
    final_df.to_sql('secret_sauce_def', conn, if_exists='replace', index=False)
    
    print(f"   ✅ Secret Sauce calculated for {len(final_df)} team-seasons.")
    conn.close()

if __name__ == "__main__":
    engineer_defense_sauce()