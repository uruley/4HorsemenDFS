#!/usr/bin/env python3
"""
Test position constraints to see why no feasible solution is found
"""
import pandas as pd

def test_constraints():
    """Test the position constraints"""
    
    # Load the merged data from the optimizer
    try:
        # Try to load the output file if it exists
        df = pd.read_csv("optimal_lineup_v3.csv")
        print("✓ Loaded merged data from optimizer output")
    except FileNotFoundError:
        print("❌ No optimizer output file found. Run the optimizer first.")
        return
    
    print(f"\n📊 Data Overview:")
    print(f"Total players: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    if 'pos' in df.columns:
        print(f"\n🎯 Position Distribution:")
        pos_counts = df['pos'].value_counts()
        print(pos_counts)
        
        # Check if we have enough players for each position
        required = {
            'QB': 1,
            'RB': 2, 
            'WR': 3,
            'TE': 1,
            'DST': 1
        }
        
        print(f"\n🔍 Position Requirements Check:")
        for pos, count in required.items():
            available = pos_counts.get(pos, 0)
            status = "✅" if available >= count else "❌"
            print(f"{status} {pos}: Need {count}, Have {available}")
        
        # Check salary distribution
        if 'salary' in df.columns:
            print(f"\n💰 Salary Analysis:")
            print(f"Salary range: ${df['salary'].min():.0f} - ${df['salary'].max():.0f}")
            print(f"Total salary: ${df['salary'].sum():,}")
            
            # Check if we can afford a basic lineup
            min_salary = df['salary'].min()
            max_salary = df['salary'].max()
            
            # Calculate minimum possible lineup cost
            min_lineup_cost = 0
            for pos, count in required.items():
                pos_players = df[df['pos'] == pos]
                if len(pos_players) > 0:
                    min_lineup_cost += pos_players['salary'].min() * count
            
            print(f"Minimum lineup cost: ${min_lineup_cost:,}")
            print(f"Salary cap: $50,000")
            print(f"Can afford basic lineup: {'✅' if min_lineup_cost <= 50000 else '❌'}")
        
        # Check projections
        if 'proj_points' in df.columns:
            print(f"\n📈 Projection Analysis:")
            print(f"Projection range: {df['proj_points'].min():.1f} - {df['proj_points'].max():.1f}")
            
            # Check for any players with 0 or negative projections
            zero_proj = df[df['proj_points'] <= 0]
            if len(zero_proj) > 0:
                print(f"⚠️ Players with ≤0 projections: {len(zero_proj)}")
                print(zero_proj[['name', 'pos', 'proj_points']].head())
    
    else:
        print("❌ No position column found in data")

if __name__ == "__main__":
    test_constraints()
