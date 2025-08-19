#!/usr/bin/env python3
"""
Advanced name matching system for DFS optimizer.
Analyzes actual data patterns to improve RB/WR/TE matching.
"""

import pandas as pd
import re
from difflib import SequenceMatcher, get_close_matches
from typing import Dict, List, Tuple, Optional

class AdvancedNameMatcher:
    """
    Sophisticated name matching that handles various abbreviation patterns
    and edge cases in DFS player names.
    """
    
    def __init__(self, debug=False):
        self.debug = debug
        self.match_stats = {
            'exact': 0,
            'initial_lastname': 0,
            'lastname_only': 0,
            'fuzzy': 0,
            'nickname': 0,
            'special_case': 0
        }
        
        # Common nickname mappings in NFL
        self.nicknames = {
            'DJ': ['David', 'Dennis', 'Daniel'],
            'AJ': ['Adrian', 'Aaron', 'Austin'],
            'TJ': ['Thomas', 'Tyler', 'Terrell'],
            'CJ': ['Christopher', 'Charles', 'Calvin'],
            'JK': ['Jonathan', 'James'],
            'DK': ['DeKaylin', 'Darius'],
            'CeeDee': ['Cedarian'],
            'Tee': ['Tamaurice'],
            'Deebo': ['Tyshun'],
        }
        
    def analyze_projection_patterns(self, projections_df):
        """
        Analyze the projection file to understand name patterns.
        """
        print("\n=== ANALYZING PROJECTION NAME PATTERNS ===")
        
        patterns = {
            'abbreviated': [],  # C.Patterson
            'full_name': [],    # Justin Jefferson
            'single_name': [],  # McPherson
            'special': []       # DJ Moore, AJ Brown
        }
        
        for name in projections_df['name'].unique():
            if '.' in name and name.count('.') == 1:
                # Pattern: X.Lastname
                patterns['abbreviated'].append(name)
            elif ' ' in name and '.' not in name:
                # Full name or special case
                parts = name.split()
                if len(parts[0]) <= 3 and parts[0].isupper():
                    patterns['special'].append(name)  # DJ, AJ, TJ, etc.
                else:
                    patterns['full_name'].append(name)
            else:
                patterns['single_name'].append(name)
        
        print(f"Pattern breakdown:")
        print(f"  Abbreviated (C.Patterson): {len(patterns['abbreviated'])}")
        print(f"  Full names: {len(patterns['full_name'])}")
        print(f"  Single names: {len(patterns['single_name'])}")
        print(f"  Special (DJ/AJ/etc): {len(patterns['special'])}")
        
        if self.debug and patterns['abbreviated']:
            print(f"\nSample abbreviated: {patterns['abbreviated'][:5]}")
        
        return patterns
    
    def create_dk_name_index(self, salaries_df):
        """
        Create comprehensive index of DK names with all variations.
        """
        name_index = {}
        
        for _, row in salaries_df.iterrows():
            full_name = row['name']
            pos = row['pos']
            
            # Clean up the name
            full_name_clean = full_name.strip()
            
            # Remove common suffixes
            suffixes = [' Jr.', ' Jr', ' Sr.', ' Sr', ' III', ' II', ' IV', ' V']
            name_no_suffix = full_name_clean
            for suffix in suffixes:
                if full_name_clean.endswith(suffix):
                    name_no_suffix = full_name_clean[:-len(suffix)].strip()
                    break
            
            parts = name_no_suffix.split()
            
            if len(parts) >= 2:
                first = parts[0]
                last = ' '.join(parts[1:])  # Handle multi-part last names
                
                # Key variations to index
                variations = [
                    (full_name_clean.lower(), pos),  # Full exact name
                    (name_no_suffix.lower(), pos),   # Name without suffix
                    (f"{first[0].lower()}.{last.lower()}", pos),  # C.Patterson
                    (f"{first[0].lower()}. {last.lower()}", pos),  # C. Patterson
                    (last.lower(), pos),  # Just last name
                    (f"{first.lower()} {last.lower()}", pos),  # Full name lowercase
                ]
                
                # Add special handling for hyphenated last names
                if '-' in last:
                    last_parts = last.split('-')
                    variations.append((f"{first[0].lower()}.{last_parts[0].lower()}", pos))
                    variations.append((last_parts[0].lower(), pos))
                
                # Add nickname variations
                for nick, full_names in self.nicknames.items():
                    if first in full_names:
                        variations.append((f"{nick.lower()} {last.lower()}", pos))
                        variations.append((f"{nick.lower()}.{last.lower()}", pos))
                
                # Store all variations
                for var in variations:
                    if var not in name_index:
                        name_index[var] = row
            
            # Also index by just position for last-resort matching
            last_name_only = parts[-1].lower() if parts else full_name_clean.lower()
            pos_key = (last_name_only, pos)
            if pos_key not in name_index:
                name_index[pos_key] = row
        
        return name_index
    
    def match_single_player(self, proj_name, proj_pos, dk_index, all_dk_at_position):
        """
        Try multiple strategies to match a single player.
        """
        # Strategy 1: Exact match
        key = (proj_name.lower(), proj_pos)
        if key in dk_index:
            self.match_stats['exact'] += 1
            return dk_index[key]
        
        # Strategy 2: Handle abbreviated names (C.Patterson pattern)
        if '.' in proj_name:
            parts = proj_name.split('.')
            if len(parts) == 2:
                initial = parts[0].strip().lower()
                last = parts[1].strip().lower()
                
                # Try exact abbreviation match
                abbrev_key = (f"{initial}.{last}", proj_pos)
                if abbrev_key in dk_index:
                    self.match_stats['initial_lastname'] += 1
                    return dk_index[abbrev_key]
                
                # Try fuzzy match on last name for this position
                for (name_key, pos_key), dk_row in dk_index.items():
                    if pos_key == proj_pos and name_key.startswith(initial):
                        # Check if last name matches
                        dk_last = name_key.split()[-1] if ' ' in name_key else name_key.split('.')[-1]
                        if dk_last == last or SequenceMatcher(None, dk_last, last).ratio() > 0.85:
                            self.match_stats['initial_lastname'] += 1
                            return dk_row
        
        # Strategy 3: Special cases (DJ Moore, AJ Brown, etc.)
        parts = proj_name.split()
        if len(parts) >= 2:
            first = parts[0]
            last = ' '.join(parts[1:])
            
            # Check if it's a nickname pattern
            if first.upper() in self.nicknames:
                for full_first in self.nicknames[first.upper()]:
                    test_key = (f"{full_first.lower()} {last.lower()}", proj_pos)
                    if test_key in dk_index:
                        self.match_stats['nickname'] += 1
                        return dk_index[test_key]
        
        # Strategy 4: Last name only match (for unique last names)
        last_name = proj_name.split()[-1].lower() if ' ' in proj_name else proj_name.lower()
        
        # Get all players at this position with this last name
        matches_at_position = []
        for (name_key, pos_key), dk_row in dk_index.items():
            if pos_key == proj_pos and last_name in name_key:
                matches_at_position.append((name_key, dk_row))
        
        if len(matches_at_position) == 1:
            # Unique last name at this position
            self.match_stats['lastname_only'] += 1
            return matches_at_position[0][1]
        
        # Strategy 5: Fuzzy matching with all players at position
        if all_dk_at_position is not None and len(all_dk_at_position) > 0:
            dk_names = all_dk_at_position['name'].tolist()
            
            # Try to find close matches
            close_matches = get_close_matches(proj_name, dk_names, n=1, cutoff=0.75)
            if close_matches:
                matched_name = close_matches[0]
                matched_row = all_dk_at_position[all_dk_at_position['name'] == matched_name].iloc[0]
                self.match_stats['fuzzy'] += 1
                return matched_row
        
        return None
    
    def match_all_players(self, projections_df, salaries_df):
        """
        Main matching function that processes all players.
        """
        print("\n=== ADVANCED NAME MATCHING ===")
        
        # Analyze patterns
        patterns = self.analyze_projection_patterns(projections_df)
        
        # Create DK name index
        print("\nBuilding DK name index...")
        dk_index = self.create_dk_name_index(salaries_df)
        print(f"Created index with {len(dk_index)} name variations")
        
        # Process each projection
        matched_players = []
        unmatched_by_position = {'QB': [], 'RB': [], 'WR': [], 'TE': [], 'DST': [], 'Other': []}
        
        for _, proj_row in projections_df.iterrows():
            proj_name = proj_row['name']
            proj_pos = proj_row['pos']
            
            # Get all DK players at this position for fuzzy matching
            dk_at_position = salaries_df[salaries_df['pos'] == proj_pos]
            
            # Try to match
            matched_dk = self.match_single_player(proj_name, proj_pos, dk_index, dk_at_position)
            
            if matched_dk is not None:
                matched_players.append({
                    'name': proj_name,
                    'dk_name': matched_dk['name'],
                    'pos': proj_pos,
                    'team': matched_dk['team'],
                    'opp': matched_dk.get('opp', 'UNK'),
                    'salary': matched_dk['salary'],
                    'proj_points': proj_row['proj_points']
                })
            else:
                pos_key = proj_pos if proj_pos in unmatched_by_position else 'Other'
                unmatched_by_position[pos_key].append(proj_name)
        
        # Create result dataframe
        result_df = pd.DataFrame(matched_players)
        
        # Print detailed statistics
        print(f"\n=== MATCHING RESULTS ===")
        print(f"Total projections: {len(projections_df)}")
        print(f"Successfully matched: {len(matched_players)} ({len(matched_players)*100/len(projections_df):.1f}%)")
        
        print(f"\nMatching strategies used:")
        for strategy, count in self.match_stats.items():
            if count > 0:
                print(f"  {strategy}: {count}")
        
        print(f"\nPosition breakdown (matched/total):")
        for pos in ['QB', 'RB', 'WR', 'TE', 'DST']:
            proj_count = len(projections_df[projections_df['pos'] == pos])
            matched_count = len(result_df[result_df['pos'] == pos]) if len(result_df) > 0 else 0
            unmatched = len(unmatched_by_position.get(pos, []))
            print(f"  {pos}: {matched_count}/{proj_count} matched, {unmatched} unmatched")
        
        # Show unmatched players for debugging
        if self.debug:
            print(f"\n=== UNMATCHED PLAYERS BY POSITION ===")
            for pos, players in unmatched_by_position.items():
                if players:
                    print(f"\n{pos} ({len(players)} unmatched):")
                    for player in players[:10]:  # Show first 10
                        print(f"  - {player}")
        
        return result_df

def enhanced_merge_with_analysis(projections_df, salaries_df, debug=False):
    """
    Drop-in replacement for merge_projections_and_salaries function.
    Uses advanced matching with detailed analysis.
    """
    # Standardize positions
    if 'pos' in projections_df.columns:
        projections_df['pos'] = projections_df['pos'].str.upper().str.strip()
    
    # Prepare DK dataframe with correct column names
    dk_df = salaries_df.copy()
    if 'Position' in dk_df.columns:
        dk_df['pos'] = dk_df['Position'].str.upper().str.strip()
        dk_df['pos'] = dk_df['pos'].replace({
            'DEF': 'DST', 'D': 'DST', 'D/ST': 'DST'
        })
    if 'Name' in dk_df.columns:
        dk_df['name'] = dk_df['Name']
    if 'Salary' in dk_df.columns:
        dk_df['salary'] = dk_df['Salary']
    if 'TeamAbbrev' in dk_df.columns:
        dk_df['team'] = dk_df['TeamAbbrev']
    
    # Use advanced matcher
    matcher = AdvancedNameMatcher(debug=debug)
    merged = matcher.match_all_players(projections_df, dk_df)
    
    # Clean up and validate
    if len(merged) > 0:
        merged = merged[merged['salary'].notna() & (merged['salary'] > 0)]
        merged = merged[merged['proj_points'].notna() & (merged['proj_points'] >= 0)]
        
        # Add derived columns
        merged['value'] = merged['proj_points'] / (merged['salary'] / 1000)
        merged['is_home'] = True
    
    # Final validation
    print(f"\n=== FINAL VALIDATION ===")
    if len(merged) > 0:
        print(f"Player pool: {len(merged)} players")
        print(f"Salary range: ${merged['salary'].min():.0f} - ${merged['salary'].max():.0f}")
        print(f"Average projection: {merged['proj_points'].mean():.1f} pts")
        
        # Check minimum requirements
        min_required = {'QB': 2, 'RB': 4, 'WR': 6, 'TE': 2, 'DST': 2}
        can_build = True
        
        for pos, min_count in min_required.items():
            actual = len(merged[merged['pos'] == pos])
            status = "✅" if actual >= min_count else "❌"
            print(f"  {status} {pos}: {actual} (need {min_count}+)")
            if actual < min_count:
                can_build = False
        
        if can_build:
            print("\n✅ READY: Sufficient players to build valid lineups!")
        else:
            print("\n❌ WARNING: Insufficient players at some positions")
    else:
        print("❌ ERROR: No players matched!")
    
    return merged

def diagnose_name_patterns(projections_file='projections.csv', salaries_file='data/DKSalaries.csv'):
    """
    Diagnostic function to understand why matching is failing.
    """
    print("=== DIAGNOSTIC ANALYSIS ===\n")
    
    # Load files
    proj_df = pd.read_csv(projections_file)
    dk_df = pd.read_csv(salaries_file)
    
    # Standardize DK positions
    if 'Position' in dk_df.columns:
        dk_df['pos'] = dk_df['Position'].str.upper().replace({'DEF': 'DST', 'D': 'DST', 'D/ST': 'DST'})
    
    if 'Name' in dk_df.columns:
        dk_df['name'] = dk_df['Name']
    
    # Analyze RB/WR/TE patterns specifically
    for pos in ['RB', 'WR', 'TE']:
        print(f"\n{pos} Analysis:")
        
        proj_at_pos = proj_df[proj_df['pos'] == pos]
        dk_at_pos = dk_df[dk_df['pos'] == pos]
        
        print(f"  Projections: {len(proj_at_pos)} {pos}s")
        print(f"  DraftKings: {len(dk_at_pos)} {pos}s")
        
        if len(proj_at_pos) > 0:
            # Sample projection names
            sample_proj = proj_at_pos['name'].head(10).tolist()
            print(f"  Sample projection names: {sample_proj}")
            
            # Check pattern distribution
            abbreviated = proj_at_pos['name'].str.contains(r'^[A-Z]\\.', regex=True).sum()
            full_names = proj_at_pos['name'].str.contains(' ', regex=True).sum() - abbreviated
            single = len(proj_at_pos) - abbreviated - full_names
            
            print(f"  Patterns: {abbreviated} abbreviated, {full_names} full, {single} single")
        
        if len(dk_at_pos) > 0 and len(proj_at_pos) > 0:
            # Try to find obvious matches
            proj_lastnames = set(proj_at_pos['name'].str.split().str[-1].str.lower())
            dk_lastnames = set(dk_at_pos['name'].str.split().str[-1].str.lower())
            
            common_lastnames = proj_lastnames & dk_lastnames
            print(f"  Common last names: {len(common_lastnames)}")
            
            if len(common_lastnames) > 0 and len(common_lastnames) < 20:
                print(f"    Examples: {list(common_lastnames)[:10]}")

if __name__ == "__main__":
    import sys
    
    print("Advanced Name Matcher for DFS Optimizer\n")
    print("Options:")
    print("1. Run diagnostic analysis")
    print("2. Test matching with debug output")
    print("3. Generate integration code")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        diagnose_name_patterns()
    
    elif choice == "2":
        # Test with actual files
        proj_df = pd.read_csv('projections.csv')
        dk_df = pd.read_csv('data/DKSalaries.csv')
        
        # Prepare DK dataframe
        if 'Position' in dk_df.columns:
            dk_df['pos'] = dk_df['Position']
        if 'Name' in dk_df.columns:
            dk_df['name'] = dk_df['Name']
        if 'Salary' in dk_df.columns:
            dk_df['salary'] = dk_df['Salary']
        if 'TeamAbbrev' in dk_df.columns:
            dk_df['team'] = dk_df['TeamAbbrev']
        
        result = enhanced_merge_with_analysis(proj_df, dk_df, debug=True)
        
        if len(result) > 0:
            print(f"\n=== SAMPLE MATCHES ===")
            print(result[['name', 'dk_name', 'pos', 'salary', 'proj_points']].head(20))
    
    elif choice == "3":
        print("\n=== INTEGRATION CODE ===")
        print("Add this to your optimize_lineups.py:\n")
        print("from advanced_name_matcher import enhanced_merge_with_analysis")
        print("\n# In your main() function, replace:")
        print("# player_pool = merge_projections_and_salaries(projections, salaries)")
        print("# with:")
        print("player_pool = enhanced_merge_with_analysis(projections, salaries, debug=False)")
