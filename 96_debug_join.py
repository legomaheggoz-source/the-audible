import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

print("--- 🕵️ DEBUGGING THE EMPTY DEFENSE WARNING ---")

# 1. CHECK THE RAW STATS (Is Step 3 working?)
print("\n1. CHECKING WEEKLY STATS:")
try:
    df_stats = pd.read_sql("SELECT * FROM weekly_stats LIMIT 5", conn)
    if df_stats.empty:
        print("   ❌ CRITICAL FAILURE: 'weekly_stats' table is EMPTY.")
        print("      Fix: Step 3 (fetch_history) did not save any data.")
    else:
        print(f"   ✅ Found data. Sample row:\n{df_stats.iloc[0]}")
        
        # 2. CHECK THE TEAMS (Are they NULL?)
        print("\n2. CHECKING TEAM COLUMN:")
        null_count = pd.read_sql("SELECT COUNT(*) FROM weekly_stats WHERE team IS NULL", conn).iloc[0,0]
        total_count = pd.read_sql("SELECT COUNT(*) FROM weekly_stats", conn).iloc[0,0]
        print(f"   -> Total Rows: {total_count}")
        print(f"   -> Rows with NULL Team: {null_count}")
        
        if null_count == total_count:
            print("   ❌ CRITICAL FAILURE: Every single player has a NULL team.")
            print("      Fix: The logic in Step 3 is not finding the 'team' field in the Sleeper API.")

except Exception as e:
    print(f"   ❌ Error reading weekly_stats: {e}")

# 3. CHECK THE MATCHUPS (Is Step 4 Part A working?)
print("\n3. CHECKING MATCHUPS (SCHEDULE):")
try:
    df_match = pd.read_sql("SELECT * FROM matchups LIMIT 5", conn)
    if df_match.empty:
        print("   ❌ CRITICAL FAILURE: 'matchups' table is EMPTY.")
    else:
        print(f"   ✅ Found schedule data. Sample:\n{df_match[['season', 'week', 'team', 'opponent']].head(1)}")
except:
    print("   ❌ Error reading matchups.")

conn.close()