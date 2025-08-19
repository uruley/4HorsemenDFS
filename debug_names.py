#!/usr/bin/env python3
"""
Debug script to see why name matching isn't working for RBs and WRs
"""

import pandas as pd

def main():
    print("🔍 Debugging name matching...")
    
    # Load data
    proj = pd.read_csv('projections.csv')
    dk = pd.read_csv('data/DKSalaries.csv')
    
    print(f"Projections: {len(proj)} players")
    print(f"DraftKings: {len(dk)} players")
    
    # Create the name mapping like the optimizer does
    name_mapping = {}
    for _, dk_row in dk.iterrows():
        dk_name = dk_row['Name'].lower()
        dk_pos = dk_row['Position']
        name_mapping[(dk_name, dk_pos)] = dk_row
    
    print(f"\nName mapping has {len(name_mapping)} entries")
    
    # Test some specific cases
    test_cases = [
        ('C.Patterson', 'RB'),
        ('A.Thielen', 'WR'),
        ('K.Allen', 'WR'),
        ('D.Henry', 'RB')
    ]
    
    for proj_name, proj_pos in test_cases:
        print(f"\n--- Testing {proj_name} ({proj_pos}) ---")
        
        proj_name_lower = proj_name.lower()
        
        # Check exact match
        if (proj_name_lower, proj_pos) in name_mapping:
            print(f"✅ Exact match found!")
            continue
            
        # Try abbreviation matching
        if '.' in proj_name_lower:
            proj_parts = proj_name_lower.split('.')
            if len(proj_parts) == 2:
                proj_initial = proj_parts[0]
                proj_last = proj_parts[1]
                
                print(f"Looking for {proj_initial}.{proj_last} -> {proj_pos}")
                
                # Find all DK players at this position
                pos_players = [(name, pos) for (name, pos) in name_mapping.keys() if pos == proj_pos]
                print(f"Found {len(pos_players)} {proj_pos} players in DK")
                
                # Look for matches
                matches = []
                for dk_name, dk_pos in pos_players:
                    if (dk_name.startswith(proj_initial) and dk_name.endswith(proj_last)):
                        matches.append(dk_name)
                        print(f"  ✅ MATCH: {dk_name}")
                
                if not matches:
                    print(f"  ❌ No matches found")
                    # Show some examples
                    print(f"  Examples of {proj_pos} players in DK:")
                    for i, (name, pos) in enumerate(pos_players[:5]):
                        print(f"    {name}")
        else:
            print(f"Not an abbreviated name")

if __name__ == "__main__":
    main()
