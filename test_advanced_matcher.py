#!/usr/bin/env python3
"""
Test script for the new AdvancedNameMatcherV2
"""

import pandas as pd
import sys
import os

# Add scripts directory to path
sys.path.append('scripts')

from advanced_name_matcher_v2 import AdvancedNameMatcherV2

def test_matcher():
    print("🧪 Testing AdvancedNameMatcherV2")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ['projections.csv', 'data/DKSalaries.csv']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please ensure you have:")
        print("- projections.csv (your player projections)")
        print("- data/DKSalaries.csv (DraftKings salary data)")
        return
    
    # Load data
    print("📊 Loading data...")
    try:
        projections = pd.read_csv('projections.csv')
        dk_salaries = pd.read_csv('data/DKSalaries.csv')
        
        print(f"✅ Loaded {len(projections)} projections")
        print(f"✅ Loaded {len(dk_salaries)} DraftKings players")
        
        # Show sample of projections
        print(f"\n📋 Sample projections:")
        print(projections[['name', 'pos', 'team', 'proj_points']].head(10))
        
        # Show sample of DK data
        print(f"\n💰 Sample DraftKings data:")
        if 'Position' in dk_salaries.columns:
            print(dk_salaries[['Name', 'Position', 'TeamAbbrev', 'Salary']].head(10))
        else:
            print(dk_salaries.head(10))
            
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Test the matcher
    print(f"\n🔍 Testing name matching...")
    try:
        matcher = AdvancedNameMatcherV2(debug=True, alias_csv="data/name_aliases.csv")
        
        # Run the merge
        matched_data = matcher.merge(projections, dk_salaries, debug=True)
        
        if not matched_data.empty:
            print(f"\n🎯 Matched data sample:")
            print(matched_data[['name', 'dk_name', 'pos', 'team', 'salary', 'proj_points', 'match_how']].head(10))
            
            # Show match quality by type
            print(f"\n📊 Match quality breakdown:")
            match_counts = matched_data['match_how'].value_counts()
            for match_type, count in match_counts.items():
                print(f"  {match_type}: {count}")
            
            # Show value distribution
            if 'value' in matched_data.columns:
                print(f"\n💎 Value distribution by position:")
                for pos in matched_data['pos'].unique():
                    pos_data = matched_data[matched_data['pos'] == pos]
                    if not pos_data.empty:
                        avg_value = pos_data['value'].mean()
                        print(f"  {pos}: {avg_value:.3f} avg value")
        else:
            print("❌ No matches found!")
            
    except Exception as e:
        print(f"❌ Error during matching: {e}")
        import traceback
        traceback.print_exc()

def test_specific_cases():
    """Test specific name matching cases"""
    print(f"\n🧪 Testing specific name matching cases...")
    
    # Create test data
    test_projections = pd.DataFrame([
        {'name': 'Pat Mahomes', 'pos': 'QB', 'team': 'KC', 'proj_points': 25.5},
        {'name': 'Josh Palmer', 'pos': 'WR', 'team': 'LAC', 'proj_points': 12.3},
        {'name': 'DJ Moore', 'pos': 'WR', 'team': 'CHI', 'proj_points': 15.7},
        {'name': 'Amon-Ra St. Brown', 'pos': 'WR', 'team': 'DET', 'proj_points': 18.2},
    ])
    
    # Create mock DK data
    test_dk = pd.DataFrame([
        {'Name': 'Patrick Mahomes', 'Position': 'QB', 'TeamAbbrev': 'KC', 'Salary': 8500},
        {'Name': 'Joshua Palmer', 'Position': 'WR', 'TeamAbbrev': 'LAC', 'Salary': 4200},
        {'Name': 'DJ Moore', 'Position': 'WR', 'TeamAbbrev': 'CHI', 'Salary': 5800},
        {'Name': 'Amon-Ra St. Brown', 'Position': 'WR', 'TeamAbbrev': 'DET', 'Salary': 7200},
    ])
    
    try:
        matcher = AdvancedNameMatcherV2(debug=True, alias_csv="data/name_aliases.csv")
        matched = matcher.merge(test_projections, test_dk, debug=True)
        
        print(f"\n✅ Test case results:")
        print(matched[['name', 'dk_name', 'match_how']])
        
    except Exception as e:
        print(f"❌ Test case error: {e}")

if __name__ == "__main__":
    print("🚀 Advanced Name Matcher V2 Test Suite")
    print("=" * 50)
    
    # Test with real data
    test_matcher()
    
    # Test with specific cases
    test_specific_cases()
    
    print(f"\n🏁 Testing complete!")
    print("Check the reports/ directory for detailed matching reports.")

