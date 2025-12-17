import sqlite3

def setup_database():
    conn = sqlite3.connect("gridiron.db")
    cursor = conn.cursor()
    
    # 1. PLAYERS TABLE
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        full_name TEXT,
        position TEXT,
        team TEXT,
        age INTEGER,
        depth_chart_order INTEGER,
        injury_status TEXT,
        status TEXT
    )
    ''')
    
    # 2. WEEKLY STATS TABLE (Updated with 'team' column)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weekly_stats (
        player_id TEXT,
        season INTEGER,
        week INTEGER,
        team TEXT,          -- NEW COLUMN (Fixes the 04 error)
        opponent TEXT,
        pass_yd REAL,
        pass_td REAL,
        rush_yd REAL,
        rush_td REAL,
        rec REAL,
        rec_yd REAL,
        rec_td REAL,
        pts_ppr REAL,
        PRIMARY KEY (player_id, season, week)
    )
    ''')
    
    # 3. MATCHUPS TABLE
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matchups (
        season INTEGER,
        week INTEGER,
        team TEXT,
        opponent TEXT,
        vegas_implied_total REAL,
        spread REAL,
        PRIMARY KEY (season, week, team)
    )
    ''')
    
    # 4. DEFENSIVE STATS TABLE
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS defensive_stats (
        season INTEGER,
        team TEXT,
        position TEXT,
        avg_pts_allowed REAL,
        def_rank INTEGER
    )
    ''')

    # 5. ADVANCED DEFENSIVE STATS (For Step 6)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS advanced_defensive_stats (
        season INTEGER,
        opponent TEXT,
        epa_allowed_deep REAL,
        epa_allowed_short REAL,
        epa_allowed_run REAL,
        rank_vs_deep INTEGER,
        rank_vs_short INTEGER,
        rank_vs_run INTEGER
    )
    ''')
    
    # 6. PLAYER STYLES (For Step 6)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_styles (
        receiver_player_name TEXT,
        season INTEGER,
        adot REAL,
        targets INTEGER
    )
    ''')
    
    # 7. SECRET SAUCE DEFENSE (For Step 7)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS secret_sauce_def (
        season INTEGER,
        opponent TEXT,
        def_sack_rate REAL,
        rank_sack_rate INTEGER,
        def_pass_funnel_rate REAL,
        rank_funnel INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database schema initialized (v2 - with 'team' column).")

if __name__ == "__main__":
    setup_database()