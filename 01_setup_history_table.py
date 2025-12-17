import sqlite3

def setup_history_table():
    conn = sqlite3.connect("gridiron.db")
    cursor = conn.cursor()
    
    print("--- 🏛️ SETTING UP PREDICTION VAULT ---")
    
    # Create the table if it doesn't exist
    # We include 'timestamp' to track exactly when the prediction was made
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT,
        player_name TEXT,
        position TEXT,
        season INTEGER,
        week INTEGER,
        projected_score REAL,
        risk_tier TEXT,
        confidence_score REAL,
        std_dev REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        -- Constraint: Don't allow duplicate entries for the same player/week/run
        UNIQUE(player_id, season, week)
    )
    """)
    
    conn.commit()
    conn.close()
    print("   ✅ Table 'predictions_history' is ready.")

if __name__ == "__main__":
    setup_history_table()