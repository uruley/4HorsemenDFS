#!/usr/bin/env python3
"""
Enhanced Name Matcher V4 - Integrates with Centralized Player Database
This version uses the centralized database for robust cross-source matching
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import logging
from centralized_player_database import CentralizedPlayerDatabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedNameMatcherV4:
    """
    Enhanced name matching system that integrates with centralized player database
    Handles multiple data sources with different identifier systems
    """
    
    def __init__(self, db_path: str = "data/player_database.db", debug: bool = False):
        self.debug = debug
        self.db = CentralizedPlayerDatabase(db_path)
        self.matching_stats = {
            'exact_matches': 0,
            'database_matches': 0,
            'fuzzy_matches': 0,
            'unmatched': 0,
            'ambiguous': 0
        }
        
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
    
    def match_players_with_database(self, dk_df: pd.DataFrame, nfl_df: pd.DataFrame,
                                   similarity_threshold: float = 0.8) -> Tuple[pd.DataFrame, Dict]:
        """
        Match players using the centralized database as the source of truth
        
        Args:
            dk_df: DraftKings dataframe with 'Name' and 'ID' columns
            nfl_df: NFL API dataframe with 'player_name' and 'player_id' columns
            similarity_threshold: Minimum similarity score for fuzzy matches
            
        Returns:
            Tuple of (matched_df, matching_stats)
        """
        logger.info(f"Starting database-enhanced matching: {len(dk_df)} DK players vs {len(nfl_df)} NFL players")
        
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
            
            # Step 1: Try to find player in centralized database
            db_player = self.db.find_player_by_name(dk_name, "draftkings")
            
            if db_player:
                # Player found in database - try to match with NFL data
                nfl_match = self._find_nfl_match_for_db_player(db_player, nfl_df)
                
                if nfl_match:
                    matches.append({
                        'dk_name': dk_name,
                        'nfl_name': nfl_match['player_name'],
                        'match_type': 'database',
                        'similarity': 1.0,
                        'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0],
                        'nfl_id': nfl_match['player_id'],
                        'canonical_name': db_player['canonical_name'],
                        'confidence': db_player.get('confidence_score', 1.0)
                    })
                    self.matching_stats['database_matches'] += 1
                    continue
            
            # Step 2: Try exact match with NFL data
            if dk_name in nfl_names:
                matches.append({
                    'dk_name': dk_name,
                    'nfl_name': dk_name,
                    'match_type': 'exact',
                    'similarity': 1.0,
                    'dk_id': dk_df[dk_df['Name'] == dk_name]['ID'].iloc[0],
                    'nfl_id': nfl_df[nfl_df['player_name'] == dk_name]['player_id'].iloc[0],
                    'canonical_name': dk_name,
                    'confidence': 1.0
                })
                self.matching_stats['exact_matches'] += 1
                continue
            
            # Step 3: Try fuzzy matching
            best_match, best_score = self._find_best_match(dk_name, nfl_names, similarity_threshold)
            
            if best_match:
                # Check if this creates ambiguity
                existing_matches = [m for m in matches if m['nfl_name'] == best_match]
                if existing_matches:
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
                        'nfl_id': nfl_df[nfl_df['player_name'] == best_match]['player_id'].iloc[0],
                        'canonical_name': f"{dk_name} (fuzzy)",
                        'confidence': best_score
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
            results_df = pd.DataFrame(columns=['dk_name', 'nfl_name', 'match_type', 'similarity', 
                                             'dk_id', 'nfl_id', 'canonical_name', 'confidence'])
        
        # Log statistics
        logger.info(f"Matching complete:")
        logger.info(f"  Database matches: {self.matching_stats['database_matches']}")
        logger.info(f"  Exact matches: {self.matching_stats['exact_matches']}")
        logger.info(f"  Fuzzy matches: {self.matching_stats['fuzzy_matches']}")
        logger.info(f"  Unmatched: {self.matching_stats['unmatched']}")
        logger.info(f"  Ambiguous: {self.matching_stats['ambiguous']}")
        
        return results_df, {
            'matches': matches,
            'unmatched': unmatched,
            'ambiguous': ambiguous,
            'stats': self.matching_stats
        }
    
    def _find_nfl_match_for_db_player(self, db_player: Dict, nfl_df: pd.DataFrame) -> Optional[Dict]:
        """Find NFL data match for a player from the database"""
        try:
            # Get all aliases for this player
            aliases = self.db.get_all_aliases(db_player['id'])
            
            # Look for NFL API aliases
            for alias in aliases:
                if alias['source_name'] == 'nfl_api':
                    nfl_match = nfl_df[nfl_df['player_name'] == alias['alias_name']]
                    if not nfl_match.empty:
                        return nfl_match.iloc[0].to_dict()
            
            # If no NFL API alias, try fuzzy matching with canonical name
            best_match, best_score = self._find_best_match(
                db_player['canonical_name'], 
                nfl_df['player_name'].unique(), 
                threshold=0.8
            )
            
            if best_match:
                return nfl_df[nfl_df['player_name'] == best_match].iloc[0].to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding NFL match for {db_player['canonical_name']}: {e}")
            return None
    
    def auto_populate_database(self, dk_df: pd.DataFrame, nfl_df: pd.DataFrame):
        """Automatically populate the database with players from both sources"""
        logger.info("Auto-populating centralized database...")
        
        # Process DraftKings players
        for _, row in dk_df.iterrows():
            dk_name = row['Name']
            dk_id = row['ID']
            position = row['Position']
            team = row['TeamAbbrev']
            
            # Check if player already exists
            existing_player = self.db.find_player_by_name(dk_name, "draftkings")
            
            if not existing_player:
                # Parse name into first/last
                name_parts = dk_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                else:
                    first_name = dk_name
                    last_name = ""
                
                # Add to database
                player_id = self.db.add_player(
                    canonical_name=dk_name,
                    first_name=first_name,
                    last_name=last_name,
                    position=position,
                    team=team
                )
                
                # Add DraftKings alias
                self.db.add_alias(player_id, dk_name, "draftkings", 1.0)
                
                # Add external ID
                self.db.add_external_id(player_id, "draftkings", str(dk_id), dk_name, 1.0)
        
        # Process NFL API players
        for _, row in nfl_df.iterrows():
            nfl_name = row['player_name']
            nfl_id = row['player_id']
            
            # Check if player already exists
            existing_player = self.db.find_player_by_name(nfl_name, "nfl_api")
            
            if not existing_player:
                # Try to find by canonical name (remove abbreviation)
                if '.' in nfl_name:
                    # This is an abbreviated name like "J.Chase"
                    # We'll need to match it manually or leave it for now
                    continue
                
                # Add to database
                player_id = self.db.add_player(
                    canonical_name=nfl_name,
                    nfl_id=nfl_id
                )
                
                # Add NFL API alias
                self.db.add_alias(player_id, nfl_name, "nfl_api", 1.0)
                
                # Add external ID
                self.db.add_external_id(player_id, "nfl_api", str(nfl_id), nfl_name, 1.0)
        
        logger.info("Database population complete")
    
    def suggest_database_updates(self, unmatched: List[Dict], nfl_names: List[str]) -> pd.DataFrame:
        """Suggest database updates for unmatched players"""
        suggestions = []
        
        for player in unmatched:
            dk_name = player['dk_name']
            best_matches = []
            
            for nfl_name in nfl_names:
                score = self._calculate_similarity(dk_name, nfl_name)
                if score >= 0.6:  # Lower threshold for suggestions
                    best_matches.append((nfl_name, score))
            
            # Sort by similarity and take top 3
            best_matches.sort(key=lambda x: x[1], reverse=True)
            
            for nfl_name, score in best_matches[:3]:
                suggestions.append({
                    'dk_name': dk_name,
                    'suggested_nfl_name': nfl_name,
                    'similarity': score,
                    'dk_id': player['dk_id'],
                    'action': 'add_alias' if score >= 0.8 else 'review_manually'
                })
        
        return pd.DataFrame(suggestions)
    
    def save_reports(self, results: Dict, output_dir: str = "reports"):
        """Save matching reports to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save matched players
        if results['matches']:
            matches_df = pd.DataFrame(results['matches'])
            matches_df.to_csv(f"{output_dir}/matched_players_v4.csv", index=False)
            logger.info(f"Saved {len(matches_df)} matches to {output_dir}/matched_players_v4.csv")
        
        # Save unmatched players
        if results['unmatched']:
            unmatched_df = pd.DataFrame(results['unmatched'])
            unmatched_df.to_csv(f"{output_dir}/unmatched_players_v4.csv", index=False)
            logger.info(f"Saved {len(unmatched_df)} unmatched to {output_dir}/unmatched_players_v4.csv")
        
        # Save ambiguous matches
        if results['ambiguous']:
            ambiguous_df = pd.DataFrame(results['ambiguous'])
            ambiguous_df.to_csv(f"{output_dir}/ambiguous_matches_v4.csv", index=False)
            logger.info(f"Saved {len(ambiguous_df)} ambiguous to {output_dir}/ambiguous_matches_v4.csv")
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()

def main():
    """Test the enhanced name matcher with centralized database"""
    print("🧪 TESTING ENHANCED NAME MATCHER V4 WITH CENTRALIZED DATABASE")
    print("=" * 70)
    
    try:
        # Load data
        print("Loading DraftKings data...")
        dk_df = pd.read_csv("data/DKSalaries.csv")
        print(f"✓ Loaded {len(dk_df)} DK players")
        
        print("Loading NFL API data...")
        from nfl_data_py import import_weekly_data
        nfl_df = import_weekly_data([2024])
        print(f"✓ Loaded {len(nfl_df)} NFL records")
        
        # Initialize matcher with database
        matcher = EnhancedNameMatcherV4(debug=True)
        
        # Auto-populate database
        print("\n🏗️  Auto-populating centralized database...")
        matcher.auto_populate_database(dk_df, nfl_df)
        
        # Export database to CSV for review
        matcher.db.export_to_csv()
        
        # Perform matching
        print("\n🔍 Performing database-enhanced name matching...")
        results_df, results = matcher.match_players_with_database(dk_df, nfl_df, similarity_threshold=0.8)
        
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
                print(f"     Canonical: {match.get('canonical_name', 'N/A')}")
        
        if results['unmatched']:
            print(f"\n❌ SAMPLE UNMATCHED:")
            for player in results['unmatched'][:5]:
                print(f"  {player['dk_name']} (ID: {player['dk_id']})")
        
        # Generate database update suggestions
        if results['unmatched']:
            print("\n💡 GENERATING DATABASE UPDATE SUGGESTIONS...")
            suggestions = matcher.suggest_database_updates(results['unmatched'], nfl_df['player_name'].unique())
            if not suggestions.empty:
                suggestions.to_csv("reports/database_update_suggestions.csv", index=False)
                print(f"✓ Saved {len(suggestions)} suggestions to reports/database_update_suggestions.csv")
                
                print("\nSample suggestions:")
                for _, row in suggestions.head(10).iterrows():
                    action_icon = "✅" if row['action'] == 'add_alias' else "🔍"
                    print(f"  {action_icon} {row['dk_name']} → {row['suggested_nfl_name']} (score: {row['similarity']:.2f}) - {row['action']}")
        
        # Show database statistics
        print("\n🗄️  DATABASE STATISTICS:")
        print(f"  Total players: {len(matcher.db.conn.execute('SELECT COUNT(*) FROM players').fetchone()[0])}")
        print(f"  Total aliases: {len(matcher.db.conn.execute('SELECT COUNT(*) FROM aliases').fetchone()[0])}")
        print(f"  Total external IDs: {len(matcher.db.conn.execute('SELECT COUNT(*) FROM external_ids').fetchone()[0])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'matcher' in locals():
            matcher.close()

if __name__ == "__main__":
    main()
