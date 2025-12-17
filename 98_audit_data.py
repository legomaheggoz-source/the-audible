import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

print("--- 🕵️ DATA INTEGRITY AUDIT ---")

# Check 1: Do we have Vegas Totals?
print("\n1. SAMPLE MATCHUPS (Vegas Data):")
df_m = pd.read_sql("SELECT * FROM matchups LIMIT 5", conn)
print(df_m[['season', 'week', 'team', 'vegas_implied_total']])

# Check 2: The Critical Join (Where it usually breaks)
print("\n2. TESTING THE JOIN (Player + Vegas):")
query = """
SELECT 
    p.full_name,
    p.team as player_team,
    m.team as matchup_team,
    w.fantasy_points_ppr,
    m.vegas_implied_total
FROM weekly_stats w
JOIN players p ON w.player_id = p.player_id
-- LEFT JOIN ensures we see rows even if the match fails
LEFT JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
WHERE w.season = 2025 AND w.week = 15
LIMIT 10
"""
df_join = pd.read_sql(query, conn)
print(df_join)

# Check 3: Count how many "Misses" we have
print("\n3. COUNTING FAILED JOINS:")
missed_query = """
SELECT COUNT(*) as missing_vegas_count
FROM weekly_stats w
JOIN players p ON w.player_id = p.player_id
LEFT JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
WHERE m.vegas_implied_total IS NULL
"""
print(pd.read_sql(missed_query, conn))

conn.close()