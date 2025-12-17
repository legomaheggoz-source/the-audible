import sqlite3
import pandas as pd

conn = sqlite3.connect("gridiron.db")

# Check what weeks we actually have for 2025
query = "SELECT season, week, count(*) as game_count FROM matchups WHERE season = 2025 GROUP BY season, week"
df = pd.read_sql(query, conn)

print("--- MATCHUPS DATA IN DB ---")
print(df)
conn.close()