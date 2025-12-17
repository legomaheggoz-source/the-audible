import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

print("--- 🕵️ DIAGNOSING THE 7,702 MISSING RECORDS ---")

# 1. The "Left Join" that exposes the failures
# We grab every stat line and try to attach Vegas data.
query = """
SELECT 
    w.season,
    w.week,
    p.team as sleeper_team,  -- The Team Name we rely on
    m.team as vegas_team,    -- The Team Name in the Odds file (will be NULL if join fails)
    m.vegas_implied_total
FROM weekly_stats w
JOIN players p ON w.player_id = p.player_id
LEFT JOIN matchups m ON w.season = m.season AND w.week = m.week AND p.team = m.team
WHERE w.season >= 2023
"""
df = pd.read_sql(query, conn)

# 2. Filter for the Failures
missing = df[df['vegas_implied_total'].isnull()]

print(f"\nTOTAL ROWS ANALYZED: {len(df)}")
print(f"TOTAL MISSING VEGAS: {len(missing)}")

if len(missing) > 0:
    print("\n--- ❌ BREAKDOWN OF MISSING DATA ---")
    
    # Check by Season (Did we forget to load 2023?)
    print("\n1. MISSING BY SEASON:")
    print(missing.groupby('season').size())
    
    # Check by Team (Are 'JAX' or 'WAS' the problem?)
    print("\n2. MISSING BY TEAM (Top 10 Culprits):")
    print(missing.groupby('sleeper_team').size().sort_values(ascending=False).head(10))
    
    # Check a sample week to see what the Vegas table actually has
    print("\n3. SAMPLE MATCHUPS DATA (To compare names):")
    print(pd.read_sql("SELECT DISTINCT team FROM matchups WHERE season=2024 LIMIT 10", conn))

conn.close()