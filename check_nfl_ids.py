#!/usr/bin/env python3
"""
Examine NFL API player ID format in detail
"""
import pandas as pd
from nfl_data_py import import_weekly_data

def examine_nfl_ids():
    """Examine the NFL API player ID format"""
    print("🔍 EXAMINING NFL API PLAYER ID FORMAT")
    print("="*50)
    
    # Load NFL data
    nfl = import_weekly_data([2024])
    
    # Get unique player IDs and names
    unique_players = nfl[['player_id', 'player_name', 'position']].drop_duplicates()
    
    print(f"Total records: {len(nfl)}")
    print(f"Unique players: {len(unique_players)}")
    print(f"Unique player_ids: {unique_players['player_id'].nunique()}")
    
    print("\n📊 PLAYER ID FORMAT ANALYSIS:")
    print("-" * 30)
    
    # Check ID format patterns
    sample_ids = unique_players['player_id'].head(20).tolist()
    print("Sample player_ids:")
    for i, pid in enumerate(sample_ids, 1):
        print(f"  {i:2d}. {pid} (type: {type(pid)})")
    
    # Check for patterns in the IDs
    print("\n🔍 ID PATTERN ANALYSIS:")
    print("-" * 30)
    
    # Check if they're all strings
    all_strings = unique_players['player_id'].apply(lambda x: isinstance(x, str)).all()
    print(f"All IDs are strings: {all_strings}")
    
    # Check length distribution
    id_lengths = unique_players['player_id'].str.len()
    print(f"ID length distribution:")
    print(f"  Min length: {id_lengths.min()}")
    print(f"  Max length: {id_lengths.max()}")
    print(f"  Most common length: {id_lengths.mode().iloc[0]}")
    
    # Check for common prefixes/suffixes
    print(f"\nID prefix analysis:")
    prefixes = unique_players['player_id'].str[:3].value_counts().head(10)
    for prefix, count in prefixes.items():
        print(f"  {prefix}...: {count} players")
    
    # Check for specific players we know from DraftKings
    print(f"\n🔍 LOOKING FOR KNOWN PLAYERS:")
    print("-" * 30)
    
    # Look for some well-known players
    known_players = ['Patrick Mahomes', 'Christian McCaffrey', 'Tyreek Hill', 'Travis Kelce']
    
    for player in known_players:
        matches = unique_players[unique_players['player_name'].str.contains(player, case=False, na=False)]
        if not matches.empty:
            print(f"✓ {player}: {matches['player_id'].iloc[0]}")
        else:
            print(f"✗ {player}: Not found")
    
    # Check if there are any numeric IDs
    print(f"\n🔢 NUMERIC ID CHECK:")
    print("-" * 30)
    
    try:
        numeric_ids = pd.to_numeric(unique_players['player_id'], errors='coerce')
        numeric_count = numeric_ids.notna().sum()
        print(f"Convertible to numeric: {numeric_count}/{len(unique_players)} ({numeric_count/len(unique_players)*100:.1f}%)")
        
        if numeric_count > 0:
            print("Sample numeric IDs:")
            numeric_samples = unique_players[numeric_ids.notna()].head(5)
            for _, row in numeric_samples.iterrows():
                print(f"  {row['player_name']}: {row['player_id']}")
    except Exception as e:
        print(f"Error checking numeric conversion: {e}")

if __name__ == "__main__":
    examine_nfl_ids()
