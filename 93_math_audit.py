import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

print("--- 🕵️ MATH AUDIT: KC vs DET (2023 Week 1) ---")

query = """
SELECT 
    season, 
    week, 
    team, 
    opponent, 
    spread, 
    vegas_implied_total
FROM matchups 
WHERE season = 2023 
  AND week = 1 
  AND (team = 'KC' OR team = 'DET')
"""

df = pd.read_sql(query, conn)
print(df)
conn.close()