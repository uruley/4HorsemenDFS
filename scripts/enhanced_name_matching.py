#!/usr/bin/env python3
"""
Enhanced name matching utility for DFS optimizer.
Handles various abbreviation patterns between projection sources and DraftKings.
"""

import pandas as pd
import re
from difflib import SequenceMatcher

def create_name_variations(name):
    """
    Generate possible name variations for matching.
    Handles: First.Last, F.Last, First Last Jr., nicknames, etc.
    """
    variations = set()
    name_clean = name.strip()
    variations.add(name_clean.lower())
    
    # Remove suffixes like Jr., Sr., III, etc.
    suffixes = [' Jr.', ' Jr', ' Sr.', ' Sr', ' III', ' II', ' IV']
    name_no_suffix = name_clean
    for suffix in suffixes:
        if name_clean.endswith(suffix):
            name_no_suffix = name_clean[:-len(suffix)].strip()
            variations.add(name_no_suffix.lower())
            break
    
    # Split name into parts
    parts = name_no_suffix.split()
    
    if len(parts) >= 2:
        first = parts[0]
        last = ' '.join(parts[1:])  # Handle multi-part last names
        
        # Add variations
        variations.add(f"{first.lower()} {last.lower()}")  # full name
        variations.add(f"{first[0].lower()}.{last.lower()}")  # F.Last
        variations.add(f"{first[0].lower()}. {last.lower()}")  # F. Last
        
        # Handle hyphenated last names
        if '-' in last:
            # Add version with just the first part of hyphenated name
            last_parts = last.split('-')
            variations.add(f"{first.lower()} {last_parts[0].lower()}")
            variations.add(f"{first[0].lower()}.{last_parts[0].lower()}")
    
    return variations

def enhanced_name_matching(projections_df, salaries_df):
    """
    Enhanced matching that handles abbreviated names better.
    Returns merged dataframe with matched players.
    """
    print("\n=== ENHANCED NAME MATCHING ===")
    
    # Create lookup dictionaries for both datasets
    proj_lookup = {}
    for _, row in projections_df.iterrows():
        key = (row['name'].lower(), row['pos'])
        proj_lookup[key] = row
        
        # Also store variations
        for variation in create_name_variations(row['name']):
            proj_lookup[(variation, row['pos'])] = row
    
    dk_lookup = {}
    for _, row in salaries_df.iterrows():
        # Create all possible variations of DK names
        for variation in create_name_variations(row['name']):
            key = (variation, row['pos'])
            dk_lookup[key] = row
    
    # Track matches
    matched_players = []
    unmatched_projections = []
    match_details = {'exact': 0, 'variation': 0, 'fuzzy': 0}
    
    # Process each projection
    for _, proj_row in projections_df.iterrows():
        proj_name = proj_row['name']
        proj_pos = proj_row['pos']
        matched = False
        
        # Try exact match first
        key = (proj_name.lower(), proj_pos)
        if key in dk_lookup:
            dk_row = dk_lookup[key]
            matched_players.append({
                'name': proj_name,  # Keep original projection name
                'dk_name': dk_row['name'],  # Store DK name for reference
                'pos': proj_pos,
                'team': dk_row['team'],
                'opp': dk_row.get('opp', 'UNK'),
                'salary': dk_row['salary'],
                'proj_points': proj_row['proj_points']
            })
            matched = True
            match_details['exact'] += 1
        
        # Try variations if no exact match
        if not matched:
            for variation in create_name_variations(proj_name):
                key = (variation, proj_pos)
                if key in dk_lookup:
                    dk_row = dk_lookup[key]
                    matched_players.append({
                        'name': proj_name,
                        'dk_name': dk_row['name'],
                        'pos': proj_pos,
                        'team': dk_row['team'],
                        'opp': dk_row.get('opp', 'UNK'),
                        'salary': dk_row['salary'],
                        'proj_points': proj_row['proj_points']
                    })
                    matched = True
                    match_details['variation'] += 1
                    break
        
        # If still not matched, try fuzzy matching
        if not matched:
            # Get all DK players at this position
            dk_at_position = salaries_df[salaries_df['pos'] == proj_pos]
            
            if len(dk_at_position) > 0:
                best_match = None
                best_score = 0
                
                # For abbreviated names like "C.Patterson"
                if '.' in proj_name:
                    parts = proj_name.split('.')
                    if len(parts) == 2:
                        initial = parts[0].strip().lower()
                        last_name = parts[1].strip().lower()
                        
                        for _, dk_row in dk_at_position.iterrows():
                            dk_name_lower = dk_row['name'].lower()
                            
                            # Check if DK name starts with initial and contains last name
                            if dk_name_lower.startswith(initial) and last_name in dk_name_lower:
                                # Calculate similarity score
                                dk_last = dk_name_lower.split()[-1]
                                score = SequenceMatcher(None, last_name, dk_last).ratio()
                                
                                if score > best_score and score > 0.8:  # 80% similarity threshold
                                    best_score = score
                                    best_match = dk_row
                else:
                    # For non-abbreviated names, use last name matching
                    proj_last = proj_name.split()[-1].lower()
                    
                    for _, dk_row in dk_at_position.iterrows():
                        dk_last = dk_row['name'].split()[-1].lower()
                        
                        # Check if last names match or are very similar
                        score = SequenceMatcher(None, proj_last, dk_last).ratio()
                        
                        if score > best_score and score > 0.85:  # 85% similarity for full names
                            best_score = score
                            best_match = dk_row
                
                if best_match is not None:
                    matched_players.append({
                        'name': proj_name,
                        'dk_name': best_match['name'],
                        'pos': proj_pos,
                        'team': best_match['team'],
                        'opp': best_match.get('opp', 'UNK'),
                        'salary': best_match['salary'],
                        'proj_points': proj_row['proj_points']
                    })
                    matched = True
                    match_details['fuzzy'] += 1
        
        if not matched:
            unmatched_projections.append(proj_name)
    
    # Create merged dataframe
    merged_df = pd.DataFrame(matched_players)
    
    # Print matching statistics
    print(f"Matching Results:")
    print(f"  Total projections: {len(projections_df)}")
    print(f"  Successfully matched: {len(matched_players)}")
    print(f"    - Exact matches: {match_details['exact']}")
    print(f"    - Variation matches: {match_details['variation']}")
    print(f"    - Fuzzy matches: {match_details['fuzzy']}")
    print(f"  Unmatched: {len(unmatched_projections)}")
    
    if len(matched_players) > 0:
        print(f"\nPosition breakdown of matched players:")
        for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
            count = len(merged_df[merged_df['pos'] == pos])
            print(f"    {pos}: {count}")
    
    if unmatched_projections and len(unmatched_projections) <= 10:
        print(f"\nUnmatched players: {unmatched_projections}")
    elif unmatched_projections:
        print(f"\nShowing first 10 unmatched: {unmatched_projections[:10]}")
    
    return merged_df

def test_name_matching():
    """
    Test the enhanced name matching with sample data
    """
    # Sample projection data with abbreviated names
    projections = pd.DataFrame({
        'name': ['C.Patterson', 'A.Thielen', 'J.Jefferson', 'D.Cook', 'T.Hill', 
                 'P.Mahomes', 'J.Allen', 'A.Kamara', 'C.McCaffrey', 'D.Adams'],
        'pos': ['RB', 'WR', 'WR', 'RB', 'WR', 'QB', 'QB', 'RB', 'RB', 'WR'],
        'proj_points': [12.5, 14.2, 18.5, 16.3, 17.8, 24.5, 23.2, 15.6, 19.8, 16.9]
    })
    
    # Sample DK data with full names
    dk_salaries = pd.DataFrame({
        'name': ['Cordarrelle Patterson', 'Adam Thielen', 'Justin Jefferson', 
                 'Dalvin Cook', 'Tyreek Hill', 'Patrick Mahomes', 'Josh Allen',
                 'Alvin Kamara', 'Christian McCaffrey', 'Davante Adams'],
        'pos': ['RB', 'WR', 'WR', 'RB', 'WR', 'QB', 'QB', 'RB', 'RB', 'WR'],
        'team': ['ATL', 'MIN', 'MIN', 'MIN', 'MIA', 'KC', 'BUF', 'NO', 'SF', 'LV'],
        'salary': [5200, 6400, 8200, 7100, 8500, 8000, 7800, 7500, 9000, 7600]
    })
    
    # Test the matching
    result = enhanced_name_matching(projections, dk_salaries)
    
    print("\n=== TEST RESULTS ===")
    print(f"Matched {len(result)} out of {len(projections)} players")
    if len(result) > 0:
        print("\nSample matches:")
        print(result[['name', 'dk_name', 'pos', 'salary', 'proj_points']].head())
    
    return result

# Integration function for the optimizer
def merge_projections_and_salaries_enhanced(projections_df, salaries_df):
    """
    Drop-in replacement for the merge function in optimize_lineups.py
    Uses enhanced name matching to handle abbreviations.
    """
    print("\nMerging projections with salaries using ENHANCED matching...")
    
    # Standardize position names in both dataframes
    if 'pos' in projections_df.columns:
        projections_df['pos'] = projections_df['pos'].str.upper().str.strip()
    
    if 'pos' in salaries_df.columns:
        salaries_df['pos'] = salaries_df['pos'].str.upper().str.strip()
        # Handle DK position naming
        salaries_df['pos'] = salaries_df['pos'].replace({
            'DEF': 'DST',
            'D': 'DST',
            'D/ST': 'DST'
        })
    
    # Use enhanced matching
    merged = enhanced_name_matching(projections_df, salaries_df)
    
    # Ensure all required columns exist
    required_cols = ['name', 'pos', 'team', 'opp', 'salary', 'proj_points']
    for col in required_cols:
        if col not in merged.columns:
            if col == 'opp':
                merged['opp'] = 'UNK'
            elif col == 'team':
                merged['team'] = 'UNK'
    
    # Clean up
    merged = merged[merged['salary'].notna() & (merged['salary'] > 0)]
    merged = merged[merged['proj_points'].notna() & (merged['proj_points'] >= 0)]
    
    # Add derived columns
    merged['value'] = merged['proj_points'] / (merged['salary'] / 1000)
    merged['is_home'] = True  # Placeholder
    
    # Final validation
    print(f"\nFinal player pool: {len(merged)} players")
    print(f"Average salary: ${merged['salary'].mean():.0f}")
    print(f"Average projection: {merged['proj_points'].mean():.1f} pts")
    
    # Check if we have enough players for each position
    min_required = {'QB': 2, 'RB': 4, 'WR': 6, 'TE': 2, 'DST': 2}
    position_check = True
    
    for pos, min_count in min_required.items():
        actual_count = len(merged[merged['pos'] == pos])
        if actual_count < min_count:
            print(f"⚠️  Warning: Only {actual_count} {pos} available (need at least {min_count})")
            position_check = False
    
    if position_check:
        print("✅ Sufficient players at all positions for lineup generation")
    else:
        print("❌ Insufficient players at some positions - may not generate valid lineups")
    
    return merged

if __name__ == "__main__":
    # Run test
    print("Running enhanced name matching test...")
    test_result = test_name_matching()
    
    print("\n" + "="*50)
    print("To use this in your optimizer:")
    print("1. Import this module in optimize_lineups.py")
    print("2. Replace merge_projections_and_salaries with merge_projections_and_salaries_enhanced")
    print("3. Run your optimizer as normal")
