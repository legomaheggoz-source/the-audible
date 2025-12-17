import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

print("--- 🏥 DATABASE VITALS CHECK ---")

# 1. CHECK PULSE (Row Counts)
stats_count = pd.read_sql("SELECT COUNT(*) FROM weekly_stats", conn).iloc[0,0]
matchups_count = pd.read_sql("SELECT COUNT(*) FROM matchups", conn).iloc[0,0]

print(f"\n1. ROW COUNTS:")
print(f"   weekly_stats: {stats_count} (Should be > 10,000)")
print(f"   matchups:     {matchups_count} (Should be ~1,684)")

# 2. CHECK BLOOD PRESSURE (The 'team' column)
if stats_count > 0:
    print(f"\n2. CHECKING TEAM COLUMN IN STATS:")
    # Check for NULLs
    null_teams = pd.read_sql("SELECT COUNT(*) FROM weekly_stats WHERE team IS NULL", conn).iloc[0,0]
    print(f"   Rows with NULL team: {null_teams}")
    
    # Check actual values (Are they 'SF' or 'San Francisco'?)
    sample_teams = pd.read_sql("SELECT DISTINCT team FROM weekly_stats LIMIT 10", conn)
    print(f"   Sample Team Names: {sample_teams['team'].tolist()}")
else:
    print("\n2. ❌ weekly_stats IS EMPTY. Step 3 (History) failed to save.")

# 3. CHECK THE MATCH (Do they speak the same language?)
if matchups_count > 0:
    print(f"\n3. CHECKING TEAM COLUMN IN MATCHUPS:")
    sample_matchup_teams = pd.read_sql("SELECT DISTINCT team FROM matchups LIMIT 10", conn)
    print(f"   Sample Matchup Teams: {sample_matchup_teams['team'].tolist()}")

conn.close()