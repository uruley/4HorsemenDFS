#!/usr/bin/env python3
"""
Debug the merge process to see what data is being passed to the optimizer
"""
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.optimize_lineups_v3 import CentralizedPlayerMatcher, load_projections, load_dk_salaries

def debug_merge():
    """Debug the merge process"""
    
    print("🔍 Debugging merge process...")
    
    # Load data
    print("\n1️⃣ Loading projections...")
    projections = load_projections("projections.csv")
    print(f"Projections loaded: {len(projections)} rows")
    print(f"Columns: {list(projections.columns)}")
    
    print("\n2️⃣ Loading salaries...")
    salaries = load_dk_salaries("data/DKSalaries.csv")
    print(f"Salaries loaded: {len(salaries)} rows")
    print(f"Columns: {list(salaries.columns)}")
    
    print("\n3️⃣ Initializing matcher...")
    matcher = CentralizedPlayerMatcher()
    
    print("\n4️⃣ Running merge...")
    merged = matcher.merge_projections_and_salaries(projections, salaries)
    
    if merged.empty:
        print("❌ Merge failed - no data returned")
        return
    
    print(f"\n✅ Merge successful!")
    print(f"Merged data: {len(merged)} rows")
    print(f"Columns: {list(merged.columns)}")
    
    # Check position distribution
    if 'pos' in merged.columns:
        print(f"\n🎯 Position distribution in merged data:")
        pos_counts = merged['pos'].value_counts()
        print(pos_counts)
        
        # Check if we have enough players for each position
        required = {
            'QB': 1,
            'RB': 2, 
            'WR': 3,
            'TE': 1,
            'DST': 1
        }
        
        print(f"\n🔍 Position requirements check:")
        for pos, count in required.items():
            available = pos_counts.get(pos, 0)
            status = "✅" if available >= count else "❌"
            print(f"{status} {pos}: Need {count}, Have {available}")
        
        # Check salary distribution
        if 'salary' in merged.columns:
            print(f"\n💰 Salary analysis:")
            print(f"Salary range: ${merged['salary'].min():.0f} - ${merged['salary'].max():.0f}")
            
            # Check if we can afford a basic lineup
            min_lineup_cost = 0
            for pos, count in required.items():
                pos_players = merged[merged['pos'] == pos]
                if len(pos_players) > 0:
                    min_lineup_cost += pos_players['salary'].min() * count
            
            print(f"Minimum lineup cost: ${min_lineup_cost:,}")
            print(f"Salary cap: $50,000")
            print(f"Can afford basic lineup: {'✅' if min_lineup_cost <= 50000 else '❌'}")
        
        # Check projections
        if 'proj_points' in merged.columns:
            print(f"\n📈 Projection analysis:")
            print(f"Projection range: {merged['proj_points'].min():.1f} - {merged['proj_points'].max():.1f}")
            
            # Check for any players with 0 or negative projections
            zero_proj = merged[merged['proj_points'] <= 0]
            if len(zero_proj) > 0:
                print(f"⚠️ Players with ≤0 projections: {len(zero_proj)}")
                print(zero_proj[['name', 'pos', 'proj_points']].head())
    
    # Close database connection
    matcher.close()

if __name__ == "__main__":
    debug_merge()
