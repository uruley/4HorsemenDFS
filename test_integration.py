#!/usr/bin/env python3
"""
Integration test showing how to use AdvancedNameMatcherV2 in your DFS workflow
"""

import pandas as pd
import sys
import os

# Add scripts directory to path
sys.path.append('scripts')

from advanced_name_matcher_v2 import AdvancedNameMatcherV2

def integrate_with_workflow():
    """Show how to integrate the new matcher into your existing workflow"""
    
    print("🔗 Integration Test: AdvancedNameMatcherV2 in DFS Workflow")
    print("=" * 60)
    
    # Step 1: Load your data
    print("1️⃣ Loading data...")
    
    if not os.path.exists('projections.csv'):
        print("❌ projections.csv not found. Creating sample data...")
        # Create sample projections for testing
        sample_projections = pd.DataFrame([
            {'name': 'Pat Mahomes', 'pos': 'QB', 'team': 'KC', 'proj_points': 25.5},
            {'name': 'Josh Palmer', 'pos': 'WR', 'team': 'LAC', 'proj_points': 12.3},
            {'name': 'DJ Moore', 'pos': 'WR', 'team': 'CHI', 'proj_points': 15.7},
            {'name': 'Amon-Ra St. Brown', 'pos': 'WR', 'team': 'DET', 'proj_points': 18.2},
            {'name': 'Christian McCaffrey', 'pos': 'RB', 'team': 'SF', 'proj_points': 22.1},
            {'name': 'Travis Kelce', 'pos': 'TE', 'team': 'KC', 'proj_points': 18.5},
            {'name': 'Buffalo Bills', 'pos': 'DST', 'team': 'BUF', 'proj_points': 8.2},
        ])
        sample_projections.to_csv('projections.csv', index=False)
        print("✅ Created sample projections.csv")
        projections = sample_projections
    else:
        projections = pd.read_csv('projections.csv')
        print(f"✅ Loaded {len(projections)} projections from projections.csv")
    
    if not os.path.exists('data/DKSalaries.csv'):
        print("❌ data/DKSalaries.csv not found. Creating sample data...")
        # Create sample DK data for testing
        os.makedirs('data', exist_ok=True)
        sample_dk = pd.DataFrame([
            {'Name': 'Patrick Mahomes', 'Position': 'QB', 'TeamAbbrev': 'KC', 'Salary': 8500},
            {'Name': 'Joshua Palmer', 'Position': 'WR', 'TeamAbbrev': 'LAC', 'Salary': 4200},
            {'Name': 'DJ Moore', 'Position': 'WR', 'TeamAbbrev': 'CHI', 'Salary': 5800},
            {'Name': 'Amon-Ra St. Brown', 'Position': 'WR', 'TeamAbbrev': 'DET', 'Salary': 7200},
            {'Name': 'Christian McCaffrey', 'Position': 'RB', 'TeamAbbrev': 'SF', 'Salary': 9500},
            {'Name': 'Travis Kelce', 'Position': 'TE', 'TeamAbbrev': 'KC', 'Salary': 7800},
            {'Name': 'Buffalo Bills', 'Position': 'DST', 'TeamAbbrev': 'BUF', 'Salary': 3200},
        ])
        sample_dk.to_csv('data/DKSalaries.csv', index=False)
        print("✅ Created sample data/DKSalaries.csv")
        dk_salaries = sample_dk
    else:
        dk_salaries = pd.read_csv('data/DKSalaries.csv')
        print(f"✅ Loaded {len(dk_salaries)} players from data/DKSalaries.csv")
    
    # Step 2: Initialize the matcher
    print("\n2️⃣ Initializing AdvancedNameMatcherV2...")
    matcher = AdvancedNameMatcherV2(
        debug=True, 
        alias_csv="data/name_aliases.csv"
    )
    print("✅ Matcher initialized with manual aliases")
    
    # Step 3: Run the merge
    print("\n3️⃣ Running name matching...")
    try:
        matched_data = matcher.merge(projections, dk_salaries, debug=True)
        
        if not matched_data.empty:
            print(f"\n🎯 Successfully matched {len(matched_data)} players!")
            
            # Show the results
            print("\n📊 Matched Players:")
            print(matched_data[['name', 'dk_name', 'pos', 'team', 'salary', 'proj_points', 'match_how']].to_string(index=False))
            
            # Calculate some basic stats
            print(f"\n📈 Summary Stats:")
            print(f"Total matched: {len(matched_data)}")
            print(f"Total salary: ${matched_data['salary'].sum():,}")
            print(f"Total projected points: {matched_data['proj_points'].sum():.1f}")
            
            # Show match quality
            print(f"\n🔍 Match Quality:")
            match_quality = matched_data['match_how'].value_counts()
            for method, count in match_quality.items():
                print(f"  {method}: {count} players")
            
            # Show value by position
            if 'value' in matched_data.columns:
                print(f"\n💎 Value by Position:")
                for pos in matched_data['pos'].unique():
                    pos_data = matched_data[matched_data['pos'] == pos]
                    if not pos_data.empty:
                        avg_value = pos_data['value'].mean()
                        best_value = pos_data['value'].max()
                        print(f"  {pos}: {avg_value:.3f} avg, {best_value:.3f} best")
            
            # Save the matched data
            output_file = 'matched_players.csv'
            matched_data.to_csv(output_file, index=False)
            print(f"\n💾 Saved matched data to {output_file}")
            
        else:
            print("❌ No matches found!")
            
    except Exception as e:
        print(f"❌ Error during matching: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Check reports
    print("\n4️⃣ Checking generated reports...")
    reports_dir = "reports"
    if os.path.exists(reports_dir):
        report_files = [f for f in os.listdir(reports_dir) if f.endswith('.csv')]
        if report_files:
            print(f"📁 Generated reports:")
            for report in report_files:
                print(f"  - {reports_dir}/{report}")
        else:
            print("📁 No report files generated")
    else:
        print("📁 Reports directory not created (no unmatched/ambiguous players)")
    
    print(f"\n🏁 Integration test complete!")
    print("You can now use this matcher in your lineup optimization scripts!")

if __name__ == "__main__":
    integrate_with_workflow()

