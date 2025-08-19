#!/usr/bin/env python3
"""
Verify if DraftKings and NFL API use the same player identifiers.
This script will help diagnose the name matching issue.
"""
import pandas as pd
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_dk_data():
    """Load DraftKings salary data"""
    try:
        dk = pd.read_csv("data/DKSalaries.csv")
        print(f"✓ Loaded DraftKings data: {len(dk)} players")
        return dk
    except FileNotFoundError:
        print("✗ DraftKings data not found at data/DKSalaries.csv")
        return None

def load_nfl_data():
    """Load NFL API data using nfl_data_py"""
    try:
        from nfl_data_py import import_weekly_data
        # Load recent data to check current player IDs
        nfl = import_weekly_data([2024])  # Most recent season
        print(f"✓ Loaded NFL API data: {len(nfl)} records")
        return nfl
    except ImportError:
        print("✗ nfl_data_py not installed. Install with: pip install nfl_data_py")
        return None
    except Exception as e:
        print(f"✗ Error loading NFL data: {e}")
        return None

def analyze_identifiers(dk_df, nfl_df):
    """Analyze the identifier systems"""
    print("\n" + "="*60)
    print("IDENTIFIER ANALYSIS")
    print("="*60)
    
    # DraftKings structure
    print("\n📊 DRAFTKINGS STRUCTURE:")
    print(f"Columns: {list(dk_df.columns)}")
    print(f"Sample IDs: {dk_df['ID'].head().tolist()}")
    print(f"ID format: {dk_df['ID'].dtype}")
    print(f"Unique IDs: {dk_df['ID'].nunique()}")
    
    # NFL API structure
    print("\n🏈 NFL API STRUCTURE:")
    print(f"Columns: {list(nfl_df.columns)}")
    if 'player_id' in nfl_df.columns:
        print(f"Sample player_ids: {nfl_df['player_id'].head().tolist()}")
        print(f"player_id format: {nfl_df['player_id'].dtype}")
        print(f"Unique player_ids: {nfl_df['player_id'].nunique()}")
    else:
        print("✗ No 'player_id' column found in NFL data")
    
    # Check for other potential ID columns
    id_columns = [col for col in nfl_df.columns if 'id' in col.lower()]
    if id_columns:
        print(f"Other ID-like columns: {id_columns}")
        for col in id_columns:
            print(f"  {col}: {nfl_df[col].dtype}, {nfl_df[col].nunique()} unique values")

def check_name_matching(dk_df, nfl_df):
    """Check if names can be matched between the two datasets"""
    print("\n" + "="*60)
    print("NAME MATCHING ANALYSIS")
    print("="*60)
    
    # Get unique names from both datasets
    dk_names = set(dk_df['Name'].str.strip())
    if 'player_name' in nfl_df.columns:
        nfl_names = set(nfl_df['player_name'].str.strip())
    else:
        print("✗ No 'player_name' column in NFL data")
        return
    
    print(f"DraftKings unique names: {len(dk_names)}")
    print(f"NFL API unique names: {len(nfl_names)}")
    
    # Find exact matches
    exact_matches = dk_names.intersection(nfl_names)
    print(f"Exact name matches: {len(exact_matches)} ({len(exact_matches)/len(dk_names)*100:.1f}%)")
    
    # Show some examples
    if exact_matches:
        print("\nSample exact matches:")
        for name in list(exact_matches)[:10]:
            print(f"  ✓ {name}")
    
    # Find potential partial matches
    partial_matches = []
    for dk_name in list(dk_names)[:20]:  # Check first 20 for examples
        for nfl_name in nfl_names:
            if dk_name.lower() in nfl_name.lower() or nfl_name.lower() in dk_name.lower():
                partial_matches.append((dk_name, nfl_name))
                break
    
    if partial_matches:
        print(f"\nSample partial matches:")
        for dk, nfl in partial_matches[:10]:
            print(f"  DK: {dk} | NFL: {nfl}")
    
    # Check for common naming differences
    print("\n🔍 COMMON NAMING PATTERNS:")
    
    # Check for suffixes (Jr., Sr., III, etc.)
    jr_suffixes = [name for name in dk_names if any(suffix in name for suffix in [' Jr.', ' Sr.', ' III', ' IV', ' V'])]
    if jr_suffixes:
        print(f"  DraftKings names with suffixes: {len(jr_suffixes)}")
        print(f"  Examples: {jr_suffixes[:5]}")
    
    # Check for special characters
    special_chars = [name for name in dk_names if any(char in name for char in ["'", "-", ".", " "])]
    if special_chars:
        print(f"  DraftKings names with special chars: {len(special_chars)}")
        print(f"  Examples: {special_chars[:5]}")

def check_id_compatibility(dk_df, nfl_df):
    """Check if the ID systems are compatible"""
    print("\n" + "="*60)
    print("ID COMPATIBILITY CHECK")
    print("="*60)
    
    if 'player_id' not in nfl_df.columns:
        print("✗ Cannot check ID compatibility - no player_id in NFL data")
        return
    
    # Check if DraftKings IDs exist in NFL data
    dk_ids = set(dk_df['ID'].astype(str))
    nfl_ids = set(nfl_df['player_id'].astype(str))
    
    print(f"DraftKings IDs: {len(dk_ids)}")
    print(f"NFL API player_ids: {len(nfl_ids)}")
    
    # Check for ID overlap
    id_overlap = dk_ids.intersection(nfl_ids)
    print(f"ID overlap: {len(id_overlap)} ({len(id_overlap)/len(dk_ids)*100:.1f}%)")
    
    if id_overlap:
        print("\nSample matching IDs:")
        for id_val in list(id_overlap)[:10]:
            dk_player = dk_df[dk_df['ID'].astype(str) == id_val]['Name'].iloc[0]
            nfl_player = nfl_df[nfl_df['player_id'].astype(str) == id_val]['player_name'].iloc[0]
            print(f"  ID {id_val}: DK={dk_player} | NFL={nfl_player}")
    
    # Check ID format compatibility
    print(f"\nID format analysis:")
    print(f"  DraftKings ID type: {dk_df['ID'].dtype}")
    print(f"  NFL API ID type: {nfl_df['player_id'].dtype}")
    
    # Check if IDs are numeric vs string
    try:
        dk_numeric = pd.to_numeric(dk_df['ID'], errors='coerce')
        nfl_numeric = pd.to_numeric(nfl_df['player_id'], errors='coerce')
        
        dk_numeric_count = dk_numeric.notna().sum()
        nfl_numeric_count = nfl_numeric.notna().sum()
        
        print(f"  DraftKings numeric IDs: {dk_numeric_count}/{len(dk_df)} ({dk_numeric_count/len(dk_df)*100:.1f}%)")
        print(f"  NFL API numeric IDs: {nfl_numeric_count}/{len(nfl_df)} ({nfl_numeric_count/len(nfl_df)*100:.1f}%)")
        
    except Exception as e:
        print(f"  Error checking numeric conversion: {e}")

def main():
    """Main verification process"""
    print("🔍 VERIFYING DRAFTKINGS vs NFL API IDENTIFIERS")
    print("="*60)
    
    # Load data
    dk_df = load_dk_data()
    if dk_df is None:
        return
    
    nfl_df = load_nfl_data()
    if nfl_df is None:
        return
    
    # Analyze identifiers
    analyze_identifiers(dk_df, nfl_df)
    
    # Check name matching
    check_name_matching(dk_df, nfl_df)
    
    # Check ID compatibility
    check_id_compatibility(dk_df, nfl_df)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if 'player_id' in nfl_df.columns:
        print("1. ✅ NFL API has player_id column - good for matching")
        print("2. 🔍 Check if DraftKings IDs match NFL player_ids")
        print("3. 📝 If IDs don't match, use name-based matching with aliases")
    else:
        print("1. ❌ NFL API missing player_id - will need name-based matching")
        print("2. 📝 Focus on building robust name matching system")
        print("3. 🔧 Consider using other NFL data sources with consistent IDs")
    
    print("\n4. 🛠️  Use the name_aliases.csv file for manual corrections")
    print("5. 📊 Monitor unmatched_players.csv for ongoing issues")

if __name__ == "__main__":
    main()
