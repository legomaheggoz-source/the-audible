import sqlite3
import pandas as pd
import numpy as np

DB_NAME = "gridiron.db"

def measure_season_performance():
    conn = sqlite3.connect(DB_NAME)
    print("--- 📊 SEASON-WIDE ACCURACY AUDIT ---")

    # 1. Get all weeks that have predictions
    weeks_query = "SELECT DISTINCT week FROM predictions_history ORDER BY week ASC"
    try:
        weeks = pd.read_sql(weeks_query, conn)['week'].tolist()
    except Exception as e:
        print(f"❌ Error reading history: {e}")
        conn.close()
        return

    if not weeks:
        print("   ⚠️ No prediction history found.")
        return

    global_stats = []

    # 2. Loop through every week
    for week in weeks:
        # Get Predictions + Actuals for this specific week
        query = f"""
        SELECT 
            ph.player_name,
            ph.position,
            ph.projected_score,
            ph.confidence_score,
            w.pts_ppr as actual_score
        FROM predictions_history ph
        JOIN weekly_stats w ON ph.player_id = w.player_id AND ph.season = w.season AND ph.week = w.week
        WHERE ph.week = {week}
        """
        df = pd.read_sql(query, conn)
        
        # Skip future weeks (Week 16) where games haven't happened
        if df.empty:
            continue

        # Calculate Errors
        df['error'] = df['projected_score'] - df['actual_score']
        df['abs_error'] = df['error'].abs()
        
        # Calculate Stats per Position for this week
        for pos in ['QB', 'RB', 'WR', 'TE']:
            pos_df = df[df['position'] == pos]
            if len(pos_df) < 5: continue
            
            corr = pos_df['projected_score'].corr(pos_df['actual_score'])
            mae = pos_df['abs_error'].mean()
            
            global_stats.append({
                'Week': week,
                'Position': pos,
                'Correlation': corr,
                'MAE': mae,
                'Count': len(pos_df)
            })

    conn.close()
    
    # 3. Present the Findings
    if not global_stats:
        print("   ⚠️ No completed games found to grade yet (Is it Week 1?).")
        return

    stats_df = pd.DataFrame(global_stats)
    
    print("\n   🏆 SEASON SUMMARY (Average Performance)")
    print(f"   {'Pos':<5} {'Avg Corr (Target > 0.5)':<25} {'Avg Error (Pts)':<15}")
    print("-" * 50)
    
    summary = stats_df.groupby('Position')[['Correlation', 'MAE']].mean()
    for pos, row in summary.iterrows():
        # Grading the Correlation
        grade = "😐"
        if row['Correlation'] > 0.6: grade = "🔥"
        elif row['Correlation'] > 0.5: grade = "✅"
        elif row['Correlation'] < 0.3: grade = "❌"
        
        print(f"   {pos:<5} {row['Correlation']:.4f} {grade:<20} {row['MAE']:.2f}")

    print("\n   📈 WEEK-BY-WEEK TRENDS (Are we improving?)")
    # Pivot table to show correlation by week
    pivot = stats_df.pivot(index='Week', columns='Position', values='Correlation')
    print(pivot.round(3).fillna('-'))
    
    print("\n   🔍 DETAILED CHECK (Week 15)")
    # Show specifics for the most recent finished week
    last_week = stats_df['Week'].max()
    print(f"   (Run 'measure_performance({last_week})' inside python to see specific misses)")

if __name__ == "__main__":
    measure_season_performance()