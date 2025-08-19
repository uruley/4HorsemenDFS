#!/usr/bin/env python3
"""
Enhanced Name Matcher V3 - Handles DraftKings vs NFL API identifier mismatch
This version focuses on robust name-based matching since IDs are incompatible.
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedNameMatcherV3:
    """
    Enhanced name matching system for DraftKings vs NFL API
    Handles the fact that IDs are completely incompatible between systems
    """
    
    def __init__(self, debug: bool = False, alias_csv: Optional[str] = "data/name_aliases.csv"):
        self.debug = debug
        self.alias_csv = alias_csv
        self.name_aliases = self._load_aliases()
        self.matching_stats = {
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'alias_matches': 0,
            'unmatched': 0,
            'ambiguous': 0
        }
        
    def _load_aliases(self) -> Dict[str, str]:
        """Load name aliases from CSV"""
        try:
            if self.alias_csv and pd.io.common.file_exists(self.alias_csv):
                aliases_df = pd.read_csv(self.alias_csv)
                if 'dk_name' in aliases_df.columns and 'nfl_name' in aliases_df.columns:
                    return dict(zip(aliases_df['dk_name'], aliases_df['nfl_name']))
            return {}
        except Exception as e:
            logger.warning(f"Could not load aliases: {e}")
            return {}
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        if pd.isna(name):
            return ""
        
        # Convert to string and strip
        name = str(name).strip()
        
        # Remove common suffixes that cause issues
        suffixes_to_remove = [
            r'\s+Jr\.?$', r'\s+Sr\.?$', r'\s+I{2,4}$', r'\s+V+$',  # Jr., Sr., III, IV, V
            r'\s+II$', r'\s+IV$', r'\s+VI$', r'\s+VII$', r'\s+VIII$', r'\s+IX$'
        ]
        
        for suffix in suffixes_to_remove:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        
        # Remove extra spaces and convert to lowercase
        name = re.sub(r'\s+', ' ', name).lower()
        
        # Remove special characters but keep spaces
        name = re.sub(r'[^\w\s]', '', name)
        
        return name.strip()
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two normalized names"""
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # Use sequence matcher for fuzzy matching
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost similarity for partial matches
        if norm1 in norm2 or norm2 in norm1:
            similarity += 0.1
        
        return min(similarity, 1.0)
    
    def _find_best_match(self, dk_name: str, nfl_names: List[str], 
                         threshold: float = 0.8) -> Tuple[Optional[str], float]:
        """Find the best matching NFL name for a DraftKings name"""
        best_match = None
        best_score = 0.0
        
        for nfl_name in nfl_names:
            score = self._calculate_similarity(dk_name, nfl_name)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = nfl_name
        
        return best_match, best_score
    
    def _check_aliases(self, dk_name: str) -> Optional[str]:
        """Check if there's a direct alias for this name"""
        return self.name_aliases.get(dk_name)
    
    def match_players(self, dk_df: pd.DataFrame, nfl_df: pd.DataFrame, 
                     similarity_threshold: float = 0.8) -> Tuple[pd.DataFrame, Dict]:
        """
        Match DraftKings players to NFL API players
        
        Args:
            dk_df: DraftKings dataframe with 'Name' column
            nfl_df: NFL API dataframe with 'player_name' column
            similarity_threshold: Minimum similarity score for fuzzy matches
            
        Returns:
            Tuple of (matched_df, matching_stats)
        """
        logger.info(f"Starting name matching: {len(dk_df)} DK players vs {len(nfl_df)} NFL players")
        
        # Get unique names
        dk_names = dk_df['Name'].unique()
        nfl_names = nfl_df['player_name'].unique()
        
        # Initialize results
        matches = []
        unmatched = []
        ambiguous = []
        
        for dk_name in dk_names:
            if self.debug:
                logger.info(f"Processing DK player: {dk_name}")
            
            # Check aliases first
            alias_match = self._check_aliases(dk_name)
            if alias_match and alias_match in nfl_names:
                matches.append({
                    'dk_name': dk_name,
                    'nfl_name': alias_match,
                    'match_type': 'alias',
                    'similarity': 1.0,
                    'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0],
                    'nfl_id': nfl_df[nfl_df['player_name'] == alias_match]['player_id'].iloc[0]
                })
                self.matching_stats['alias_matches'] += 1
                continue
            
            # Try exact match
            if dk_name in nfl_names:
                matches.append({
                    'dk_name': dk_name,
                    'nfl_name': dk_name,
                    'match_type': 'exact',
                    'similarity': 1.0,
                    'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0],
                    'nfl_id': nfl_df[nfl_df['player_name'] == dk_name]['player_id'].iloc[0]
                })
                self.matching_stats['exact_matches'] += 1
                continue
            
            # Try fuzzy matching
            best_match, best_score = self._find_best_match(dk_name, nfl_names, similarity_threshold)
            
            if best_match:
                # Check if this creates ambiguity (multiple DK names matching same NFL name)
                existing_matches = [m for m in matches if m['nfl_name'] == best_match]
                if existing_matches:
                    # This is ambiguous - both DK names can't match the same NFL player
                    ambiguous.append({
                        'dk_name': dk_name,
                        'nfl_name': best_match,
                        'similarity': best_score,
                        'conflict_with': existing_matches[0]['dk_name']
                    })
                    self.matching_stats['ambiguous'] += 1
                else:
                    matches.append({
                        'dk_name': dk_name,
                        'nfl_name': best_match,
                        'match_type': 'fuzzy',
                        'similarity': best_score,
                        'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0],
                        'nfl_id': nfl_df[nfl_df['player_name'] == best_match]['player_id'].iloc[0]
                    })
                    self.matching_stats['fuzzy_matches'] += 1
            else:
                unmatched.append({
                    'dk_name': dk_name,
                    'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0]
                })
                self.matching_stats['unmatched'] += 1
        
        # Create results dataframe
        if matches:
            results_df = pd.DataFrame(matches)
        else:
            results_df = pd.DataFrame(columns=['dk_name', 'nfl_name', 'match_type', 'similarity', 'dk_id', 'nfl_id'])
        
        # Log statistics
        logger.info(f"Matching complete:")
        logger.info(f"  Exact matches: {self.matching_stats['exact_matches']}")
        logger.info(f"  Fuzzy matches: {self.matching_stats['fuzzy_matches']}")
        logger.info(f"  Alias matches: {self.matching_stats['alias_matches']}")
        logger.info(f"  Unmatched: {self.matching_stats['unmatched']}")
        logger.info(f"  Ambiguous: {self.matching_stats['ambiguous']}")
        
        return results_df, {
            'matches': matches,
            'unmatched': unmatched,
            'ambiguous': ambiguous,
            'stats': self.matching_stats
        }
    
    def save_reports(self, results: Dict, output_dir: str = "reports"):
        """Save matching reports to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save matched players
        if results['matches']:
            matches_df = pd.DataFrame(results['matches'])
            matches_df.to_csv(f"{output_dir}/matched_players.csv", index=False)
            logger.info(f"Saved {len(matches_df)} matches to {output_dir}/matched_players.csv")
        
        # Save unmatched players
        if results['unmatched']:
            unmatched_df = pd.DataFrame(results['unmatched'])
            unmatched_df.to_csv(f"{output_dir}/unmatched_players.csv", index=False)
            logger.info(f"Saved {len(unmatched_df)} unmatched to {output_dir}/unmatched_players.csv")
        
        # Save ambiguous matches
        if results['ambiguous']:
            ambiguous_df = pd.DataFrame(results['ambiguous'])
            ambiguous_df.to_csv(f"{output_dir}/ambiguous_matches.csv", index=False)
            logger.info(f"Saved {len(ambiguous_df)} ambiguous to {output_dir}/ambiguous_matches.csv")
    
    def suggest_aliases(self, unmatched: List[Dict], nfl_names: List[str], 
                       min_similarity: float = 0.6) -> pd.DataFrame:
        """Suggest potential aliases for unmatched players"""
        suggestions = []
        
        for player in unmatched:
            dk_name = player['dk_name']
            best_matches = []
            
            for nfl_name in nfl_names:
                score = self._calculate_similarity(dk_name, nfl_name)
                if score >= min_similarity:
                    best_matches.append((nfl_name, score))
            
            # Sort by similarity and take top 3
            best_matches.sort(key=lambda x: x[1], reverse=True)
            
            for nfl_name, score in best_matches[:3]:
                suggestions.append({
                    'dk_name': dk_name,
                    'suggested_nfl_name': nfl_name,
                    'similarity': score,
                    'dk_id': player['dk_id']
                })
        
        return pd.DataFrame(suggestions)

def main():
    """Test the enhanced name matcher"""
    print("🧪 TESTING ENHANCED NAME MATCHER V3")
    print("=" * 50)
    
    try:
        # Load data
        print("Loading DraftKings data...")
        dk_df = pd.read_csv("data/DKSalaries.csv")
        print(f"✓ Loaded {len(dk_df)} DK players")
        
        print("Loading NFL API data...")
        from nfl_data_py import import_weekly_data
        nfl_df = import_weekly_data([2024])
        print(f"✓ Loaded {len(nfl_df)} NFL records")
        
        # Initialize matcher
        matcher = EnhancedNameMatcherV3(debug=True)
        
        # Perform matching
        print("\n🔍 Performing name matching...")
        results_df, results = matcher.match_players(dk_df, nfl_df, similarity_threshold=0.8)
        
        # Save reports
        print("\n💾 Saving reports...")
        matcher.save_reports(results)
        
        # Show summary
        print("\n📊 MATCHING SUMMARY:")
        print(f"Total DK players: {len(dk_df)}")
        print(f"Successfully matched: {len(results['matches'])}")
        print(f"Unmatched: {len(results['unmatched'])}")
        print(f"Ambiguous: {len(results['ambiguous'])}")
        
        # Show some examples
        if results['matches']:
            print("\n✅ SAMPLE MATCHES:")
            for match in results['matches'][:5]:
                print(f"  DK: {match['dk_name']} → NFL: {match['nfl_name']} ({match['match_type']}, {match['similarity']:.2f})")
        
        if results['unmatched']:
            print(f"\n❌ SAMPLE UNMATCHED:")
            for player in results['unmatched'][:5]:
                print(f"  {player['dk_name']} (ID: {player['dk_id']})")
        
        # Generate alias suggestions
        if results['unmatched']:
            print("\n💡 GENERATING ALIAS SUGGESTIONS...")
            suggestions = matcher.suggest_aliases(results['unmatched'], nfl_df['player_name'].unique())
            if not suggestions.empty:
                suggestions.to_csv("reports/alias_suggestions.csv", index=False)
                print(f"✓ Saved {len(suggestions)} alias suggestions to reports/alias_suggestions.csv")
                
                print("\nSample suggestions:")
                for _, row in suggestions.head(10).iterrows():
                    print(f"  {row['dk_name']} → {row['suggested_nfl_name']} (score: {row['similarity']:.2f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
