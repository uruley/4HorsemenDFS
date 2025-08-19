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
    
    # Show sample data to debug
    print("\n📋 Sample projections:")
    print(projections[['name', 'pos', 'team']].head())
    
    print("\n📋 Sample salaries:")
    print(salaries[['Name', 'Position', 'Salary', 'TeamAbbrev']].head())
    
    # Create a simple mapping dictionary
    salary_map = {}
    for _, row in salaries.iterrows():
        key = (row['Name'].lower(), row['Position'])
        salary_map[key] = row['Salary']
    
    print(f"\n🔑 Created salary map with {len(salary_map)} entries")
    
    # Apply salaries to projections
    matched_count = 0
    for idx, row in projections.iterrows():
        key = (row['name'].lower(), row['pos'])
        if key in salary_map:
            projections.loc[idx, 'salary'] = salary_map[key]
            matched_count += 1
    
    print(f"✅ Matched {matched_count}/{len(projections)} players with real salaries")
    
    # Show results
    final_got_salaries = (projections['salary'] != 2500).sum()
    print(f"💰 Final result: {final_got_salaries}/{len(projections)} players have real salaries")
    
    if final_got_salaries > 0:
        print(f"💰 Salary range: ${projections['salary'].min():.0f} - ${projections['salary'].max():.0f}")
    
    # Save the fixed file
    output_path = "projections_fixed.csv"
    projections.to_csv(output_path, index=False)
    print(f"✅ Saved fixed projections to {output_path}")
    
    # Show some examples
    print("\n📋 Sample of fixed data:")
    sample = projections.head(10)
    for _, row in sample.iterrows():
        salary_type = "REAL" if row['salary'] != 2500 else "PLACEHOLDER"
        print(f"   {row['name']} ({row['pos']}) - ${row['salary']:.0f} [{salary_type}]")

if __name__ == "__main__":
    main()

