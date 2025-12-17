import requests
import json

# We'll check 2023 Week 1 (Kirk Cousins' old team)
URL = "https://api.sleeper.app/v1/stats/nfl/regular/2023/1"

print(f"--- 🏥 X-RAYING SLEEPER API ({URL}) ---")

try:
    response = requests.get(URL)
    data = response.json()
    
    # Grab the first 3 players found in the data
    sample_ids = list(data.keys())[:3]
    
    print(f"\n✅ Successfully downloaded data. Found {len(data)} players.")
    print("\n--- RAW DATA SAMPLE (First 3 Players) ---")
    
    for pid in sample_ids:
        player_data = data[pid]
        print(f"\nPlayer ID: {pid}")
        # Check specifically for 'team'
        if 'team' in player_data:
            print(f"   Key 'team' found! Value: {player_data['team']}")
        else:
            print(f"   ❌ Key 'team' is MISSING in raw JSON.")
            
        # Print all keys to see what IS there
        print(f"   Available Keys: {list(player_data.keys())}")

except Exception as e:
    print(f"❌ Error: {e}")