#!/usr/bin/env python3
"""
Manual Database Updater - Interactive tool for reviewing and updating player matches
This helps you manually resolve the remaining unmatched players
"""
import pandas as pd
import sys
import os
from centralized_player_database import CentralizedPlayerDatabase

def load_unmatched_players():
    """Load unmatched players from the latest report"""
    try:
        unmatched_df = pd.read_csv("reports/unmatched_players_v5.csv")
        print(f"✓ Loaded {len(unmatched_df)} unmatched players")
        return unmatched_df
    except FileNotFoundError:
        print("❌ No unmatched players report found. Run enhanced_name_matcher_v5.py first.")
        return None

def load_nfl_players():
    """Load NFL API players for matching"""
    try:
        from nfl_data_py import import_weekly_data
        nfl_df = import_weekly_data([2024])
        # Get unique players
        nfl_unique = nfl_df.drop_duplicates(subset=['player_name', 'position', 'recent_team'])
        print(f"✓ Loaded {len(nfl_unique)} unique NFL players")
        return nfl_unique
    except Exception as e:
        print(f"❌ Error loading NFL data: {e}")
        return None

def find_potential_matches(dk_player, nfl_df, max_results=5):
    """Find potential NFL matches for a DraftKings player"""
    dk_name = dk_player['dk_name']
    dk_position = dk_player.get('dk_position', '')
    dk_team = dk_player.get('dk_team', '')
    
    # Filter by position first
    if dk_position:
        position_matches = nfl_df[nfl_df['position'] == dk_position]
    else:
        position_matches = nfl_df
    
    # Filter by team if available
    if dk_team:
        team_matches = position_matches[position_matches['recent_team'] == dk_team]
        if len(team_matches) > 0:
            position_matches = team_matches
    
    # Calculate name similarity scores
    matches = []
    for _, nfl_row in position_matches.iterrows():
        nfl_name = nfl_row['player_name']
        
        # Simple name similarity (you can enhance this)
        name_similarity = calculate_name_similarity(dk_name, nfl_name)
        
        if name_similarity > 0.3:  # Lower threshold for suggestions
            matches.append({
                'nfl_name': nfl_name,
                'nfl_id': nfl_row['player_id'],
                'position': nfl_row['position'],
                'team': nfl_row['recent_team'],
                'similarity': name_similarity
            })
    
    # Sort by similarity and return top matches
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches[:max_results]

def calculate_name_similarity(name1, name2):
    """Calculate simple name similarity"""
    from difflib import SequenceMatcher
    
    # Normalize names
    norm1 = name1.lower().replace('.', '').replace(' ', '')
    norm2 = name2.lower().replace('.', '').replace(' ', '')
    
    # Exact match
    if norm1 == norm2:
        return 1.0
    
    # Sequence matcher
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Boost for partial matches
    if norm1 in norm2 or norm2 in norm1:
        similarity += 0.2
    
    return min(similarity, 1.0)

def interactive_review(db, unmatched_df, nfl_df):
    """Interactive review of unmatched players"""
    print("\n🔍 INTERACTIVE REVIEW OF UNMATCHED PLAYERS")
    print("=" * 60)
    print("For each player, you can:")
    print("  - Press ENTER to skip")
    print("  - Type 'q' to quit")
    print("  - Type 's' to see suggestions")
    print("  - Type a number to select a match")
    print("  - Type 'n' to add as new player")
    print()
    
    for idx, (_, dk_player) in enumerate(unmatched_df.iterrows()):
        print(f"\n[{idx+1}/{len(unmatched_df)}] DraftKings: {dk_player['dk_name']}")
        print(f"    Position: {dk_player.get('dk_position', 'N/A')}")
        print(f"    Team: {dk_player.get('dk_team', 'N/A')}")
        print(f"    ID: {dk_player['dk_id']}")
        
        # Find potential matches
        potential_matches = find_potential_matches(dk_player, nfl_df)
        
        if potential_matches:
            print("\n    Potential NFL matches:")
            for i, match in enumerate(potential_matches):
                print(f"      {i+1}. {match['nfl_name']} ({match['position']} - {match['team']}) - Score: {match['similarity']:.2f}")
        
        # Get user input
        while True:
            choice = input("\n    Choice (Enter=skip, q=quit, s=suggestions, n=new, 1-5=match): ").strip()
            
            if choice == '':
                print("    ⏭️  Skipped")
                break
            elif choice.lower() == 'q':
                print("\n👋 Review complete!")
                return
            elif choice.lower() == 's':
                print(f"\n    📋 Suggestions for {dk_player['dk_name']}:")
                for i, match in enumerate(potential_matches):
                    print(f"      {i+1}. {match['nfl_name']} ({match['position']} - {match['team']}) - Score: {match['similarity']:.2f}")
                continue
            elif choice.lower() == 'n':
                # Add as new player
                add_new_player(db, dk_player)
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(potential_matches):
                # Select a match
                selected_match = potential_matches[int(choice) - 1]
                add_player_match(db, dk_player, selected_match)
                break
            else:
                print("    ❌ Invalid choice. Please try again.")
                continue

def add_new_player(db, dk_player):
    """Add a new player to the database"""
    try:
        # Parse name
        name_parts = dk_player['dk_name'].split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        else:
            first_name = dk_player['dk_name']
            last_name = ""
        
        # Add to database
        player_id = db.add_player(
            canonical_name=dk_player['dk_name'],
            first_name=first_name,
            last_name=last_name,
            position=dk_player.get('dk_position'),
            team=dk_player.get('dk_team')
        )
        
        # Add DraftKings alias
        db.add_alias(player_id, dk_player['dk_name'], "draftkings", 1.0)
        
        # Add external ID
        db.add_external_id(player_id, "draftkings", str(dk_player['dk_id']), dk_player['dk_name'], 1.0)
        
        print(f"    ✅ Added {dk_player['dk_name']} as new player (ID: {player_id})")
        
    except Exception as e:
        print(f"    ❌ Error adding player: {e}")

def add_player_match(db, dk_player, nfl_match):
    """Add a match between DraftKings and NFL player"""
    try:
        # First, add the NFL player if not exists
        existing_player = db.find_player_by_name(nfl_match['nfl_name'], "nfl_api")
        
        if existing_player:
            player_id = existing_player['id']
        else:
            # Add new NFL player
            player_id = db.add_player(
                canonical_name=nfl_match['nfl_name'],
                position=nfl_match['position'],
                team=nfl_match['team'],
                nfl_id=nfl_match['nfl_id']
            )
            
            # Add NFL API alias
            db.add_alias(player_id, nfl_match['nfl_name'], "nfl_api", 1.0)
            
            # Add external ID
            db.add_external_id(player_id, "nfl_api", str(nfl_match['nfl_id']), nfl_match['nfl_name'], 1.0)
        
        # Add DraftKings player as alias
        db.add_alias(player_id, dk_player['dk_name'], "draftkings", 1.0)
        
        # Add DraftKings external ID
        db.add_external_id(player_id, "draftkings", str(dk_player['dk_id']), dk_player['dk_name'], 1.0)
        
        print(f"    ✅ Matched {dk_player['dk_name']} → {nfl_match['nfl_name']}")
        
    except Exception as e:
        print(f"    ❌ Error adding match: {e}")

def main():
    """Main function"""
    print("🔄 MANUAL DATABASE UPDATER")
    print("=" * 40)
    
    # Load data
    print("Loading unmatched players...")
    unmatched_df = load_unmatched_players()
    if unmatched_df is None:
        return
    
    print("Loading NFL players...")
    nfl_df = load_nfl_players()
    if nfl_df is None:
        return
    
    # Initialize database
    print("Initializing database...")
    db = CentralizedPlayerDatabase()
    
    # Start interactive review
    interactive_review(db, unmatched_df, nfl_df)
    
    # Export updated database
    print("\n💾 Exporting updated database...")
    db.export_to_csv()
    
    # Show final statistics
    print("\n📊 FINAL DATABASE STATISTICS:")
    print(f"  Total players: {len(db.conn.execute('SELECT COUNT(*) FROM players').fetchone()[0])}")
    print(f"  Total aliases: {len(db.conn.execute('SELECT COUNT(*) FROM aliases').fetchone()[0])}")
    print(f"  Total external IDs: {len(db.conn.execute('SELECT COUNT(*) FROM external_ids').fetchone()[0])}")
    
    db.close()
    print("\n✅ Database update complete!")

if __name__ == "__main__":
    main()
