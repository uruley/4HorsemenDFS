#!/usr/bin/env python3
"""
Simple script to merge projections.csv with real salary data from DKSalaries.csv
"""

import pandas as pd
import os

def main():
    print("🔧 Fixing salary data in projections...")
    
    # Load the files
    projections_path = "projections.csv"
    salaries_path = "data/DKSalaries.csv"
    
    if not os.path.exists(projections_path):
        print(f"❌ {projections_path} not found")
        return
    
    if not os.path.exists(salaries_path):
        print(f"❌ {salaries_path} not found")
        return
    
    # Load data
    projections = pd.read_csv(projections_path)
    salaries = pd.read_csv(salaries_path)
    
    print(f"📊 Loaded {len(projections)} projections")
    print(f"💰 Loaded {len(salaries)} salary records")
    
    # Clean up salary data - extract team abbreviation from Game Info
    salaries['TeamAbbrev'] = salaries['TeamAbbrev'].fillna('UNK')
    
    # Create a mapping for name + position + team
    # First try exact name match
    merged = pd.merge(
        projections,
        salaries[['Name', 'Position', 'Salary', 'TeamAbbrev']],
        left_on=['name', 'pos'],
        right_on=['Name', 'Position'],
        how='left'
    )
    
    # Check how many got salaries
    got_salaries = merged['Salary'].notna().sum()
    print(f"✅ Matched {got_salaries}/{len(projections)} players with exact name+position")
    
    # For unmatched, try fuzzy matching on name only
    if got_salaries < len(projections):
        print("🔍 Attempting fuzzy name matching for remaining players...")
        
        # Get unmatched players
        unmatched = merged[merged['Salary'].isna()].copy()
        
        # Try to match by name only (case insensitive)
        unmatched['name_lower'] = unmatched['name'].str.lower()
        salaries['Name_lower'] = salaries['Name'].str.lower()
        
        fuzzy_merged = pd.merge(
            unmatched,
            salaries[['Name_lower', 'Position', 'Salary', 'TeamAbbrev']],
            left_on=['name_lower', 'pos'],
            right_on=['Name_lower', 'Position'],
            how='left'
        )
        
        # Update the original merged dataframe
        for idx, row in fuzzy_merged.iterrows():
            if pd.notna(row['Salary']):
                # Find the corresponding row in the original projections
                orig_idx = projections.index[projections['name'] == row['name']][0]
                merged.loc[merged['name'] == row['name'], 'Salary'] = row['Salary']
                merged.loc[merged['name'] == row['name'], 'TeamAbbrev'] = row['TeamAbbrev']
        
        # Clean up
        fuzzy_merged = fuzzy_merged.drop(columns=['name_lower', 'Name_lower'])
        unmatched = unmatched.drop(columns=['name_lower'])
    
    # Final cleanup
    final = pd.DataFrame({
        'name': merged['name'],
        'pos': merged['pos'],
        'team': merged['team'],
        'opp': merged['opp'],
        'salary': merged['Salary'].fillna(2500),  # Keep 2500 as fallback
        'proj_points': merged['proj_points']
    })
    
    # Show results
    final_got_salaries = (final['salary'] != 2500).sum()
    print(f"💰 Final result: {final_got_salaries}/{len(final)} players have real salaries")
    
    if final_got_salaries > 0:
        print(f"💰 Salary range: ${final['salary'].min():.0f} - ${final['salary'].max():.0f}")
    
    # Save the fixed file
    output_path = "projections_fixed.csv"
    final.to_csv(output_path, index=False)
    print(f"✅ Saved fixed projections to {output_path}")
    
    # Show some examples
    print("\n📋 Sample of fixed data:")
    sample = final.head(10)
    for _, row in sample.iterrows():
        salary_type = "REAL" if row['salary'] != 2500 else "PLACEHOLDER"
        print(f"   {row['name']} ({row['pos']}) - ${row['salary']:.0f} [{salary_type}]")

if __name__ == "__main__":
    main()
