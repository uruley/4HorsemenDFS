#!/usr/bin/env python3
"""
Enhanced DK lineup optimizer with dynamic salary merging and MINIMUM salary constraint.
Reads projections and salaries separately, merges at runtime.
"""
import argparse
import itertools
import random
import pandas as pd
import numpy as np
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, PULP_CBC_CMD
from advanced_name_matcher import enhanced_merge_with_analysis

ROSTER_REQ = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DST": 1}
FLEX_ELIG = {"RB", "WR", "TE"}

def load_dk_salaries(path):
    """Load and normalize DraftKings salary data"""
    print(f"Loading DK salaries from {path}...")
    
    # Read CSV - DraftKings files can have various formats
    df = pd.read_csv(path)
    
    # Standardize column names (DK uses various formats)
    column_mapping = {
        'Name': 'name',
        'Position': 'pos',
        'Team': 'team',
        'Salary': 'salary',
        'Game Info': 'game_info',
        'TeamAbbrev': 'team',
        'Roster Position': 'pos'
    }
    
    # Rename columns if they exist
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # Ensure required columns exist
    required = ['name', 'pos', 'team', 'salary']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Warning: Missing columns in DK file: {missing}")
        print(f"Available columns: {df.columns.tolist()}")
    
    # Clean position names
    if 'pos' in df.columns:
        df['pos'] = df['pos'].str.upper().str.strip()
        # Handle DK position naming
        df['pos'] = df['pos'].replace({
            'DEF': 'DST',
            'D': 'DST',
            'D/ST': 'DST'
        })
    
    # Ensure salary is numeric
    if 'salary' in df.columns:
        df['salary'] = pd.to_numeric(df['salary'], errors='coerce')
        # Remove any rows with invalid salaries
        df = df[df['salary'].notna() & (df['salary'] > 0)]
    
    # Parse game info to get opponent
    if 'game_info' in df.columns:
        # Format: "TB@ATL 09/08/2024 01:00PM ET"
        df['opp'] = df['game_info'].apply(parse_opponent)
    
    print(f"Loaded {len(df)} players with salaries")
    print(f"Salary range: ${df['salary'].min():.0f} - ${df['salary'].max():.0f}")
    
    return df

def parse_opponent(game_info):
    """Parse opponent from DraftKings game info string"""
    if pd.isna(game_info):
        return 'UNK'
    
    # Format: "TB@ATL 09/08/2024 01:00PM ET"
    try:
        matchup = game_info.split()[0]  # Get "TB@ATL"
        teams = matchup.split('@')
        # Return the other team (simplified - would need player's team to be accurate)
        return teams[0] if len(teams) > 1 else 'UNK'
    except:
        return 'UNK'

def load_projections(path):
    """Load projection data"""
    print(f"Loading projections from {path}...")
    df = pd.read_csv(path)
    
    # Standardize position names
    if 'pos' in df.columns:
        df['pos'] = df['pos'].str.upper().str.strip()
    
    # Ensure proj_points is numeric
    if 'proj_points' in df.columns:
        df['proj_points'] = pd.to_numeric(df['proj_points'], errors='coerce')
        df = df[df['proj_points'].notna()]
    
    print(f"Loaded {len(df)} player projections")
    
    return df

def merge_projections_and_salaries(projections_df, salaries_df):
    """
    Merge projections with DraftKings salaries.
    Handles name matching issues common in DFS.
    """
    print("\nMerging projections with salaries...")
    
    # First attempt: Direct merge on name and position
    merged = pd.merge(
        projections_df,
        salaries_df[['name', 'pos', 'salary', 'team', 'opp']],
        on=['name', 'pos'],
        how='inner',
        suffixes=('', '_dk')
    )
    
    # Update team and opp from DK data if missing
    if 'team_dk' in merged.columns:
        merged['team'] = merged['team'].fillna(merged['team_dk'])
        merged = merged.drop('team_dk', axis=1)
    
    # Handle unmatched projections (common with name variations)
    unmatched_proj = projections_df[~projections_df['name'].isin(merged['name'])]
    if len(unmatched_proj) > 0:
        print(f"Warning: {len(unmatched_proj)} projections without salaries")
        print("Attempting improved name matching...")
        
        # Create a mapping for better name matching
        # Handle common abbreviation patterns
        name_mapping = {}
        for _, dk_row in salaries_df.iterrows():
            dk_name = dk_row['name'].lower()
            dk_pos = dk_row['pos']
            
            # Store full name mapping
            name_mapping[(dk_name, dk_pos)] = dk_row
            
            # Handle abbreviated first names (e.g., "A.Rodgers" -> "Aaron Rodgers")
            if '.' in dk_name:
                # Split on dot and try to match
                parts = dk_name.split('.')
                if len(parts) == 2:
                    first_initial = parts[0]
                    last_name = parts[1]
                    
                    # Look for full names that start with this initial and have this last name
                    for _, full_dk_row in salaries_df.iterrows():
                        full_name = full_dk_row['name'].lower()
                        full_pos = full_dk_row['pos']
                        
                        if (full_name.startswith(first_initial) and 
                            full_name.endswith(last_name) and 
                            full_pos == dk_pos):
                            name_mapping[(dk_name, dk_pos)] = full_dk_row
                            break
        
        # Try to match unmatched projections
        matched_count = 0
        for _, proj_player in unmatched_proj.iterrows():
            proj_name = proj_player['name'].lower()
            proj_pos = proj_player['pos']
            
            # Try exact match first
            if (proj_name, proj_pos) in name_mapping:
                match = name_mapping[(proj_name, proj_pos)]
                matched_count += 1
            else:
                # Try to find partial matches
                possible_matches = []
                
                for (dk_name, dk_pos), dk_row in name_mapping.items():
                    if dk_pos == proj_pos:
                        # Handle abbreviated names (e.g., "C.Patterson" -> "Cordarrelle Patterson")
                        if '.' in proj_name:
                            proj_parts = proj_name.split('.')
                            if len(proj_parts) == 2:
                                proj_initial = proj_parts[0]
                                proj_last = proj_parts[1]
                                
                                # Check if DK name starts with this initial and ends with this last name
                                # Use lowercase for comparison
                                dk_name_lower = dk_name.lower()
                                if (dk_name_lower.startswith(proj_initial) and 
                                    dk_name_lower.endswith(proj_last)):
                                    possible_matches.append(dk_row)
                        else:
                            # Check if last names match
                            proj_last = proj_name.split()[-1]
                            dk_last = dk_name.split()[-1]
                            
                            if proj_last == dk_last:
                                possible_matches.append(dk_row)
                
                if len(possible_matches) == 1:
                    match = possible_matches[0]
                    matched_count += 1
                else:
                    continue
            
            # Add the matched player
            merged = pd.concat([merged, pd.DataFrame([{
                'name': proj_player['name'],
                'pos': proj_player['pos'],
                'team': match['team'],
                'opp': match['opp'],
                'salary': match['salary'],
                'proj_points': proj_player['proj_points']
            }])], ignore_index=True)
        
        print(f"✅ Matched {matched_count} additional players with improved name matching")
    
    # Ensure all required columns exist
    required_cols = ['name', 'pos', 'team', 'opp', 'salary', 'proj_points']
    for col in required_cols:
        if col not in merged.columns:
            if col == 'opp':
                merged['opp'] = 'UNK'
            elif col == 'team':
                merged['team'] = 'UNK'
            else:
                print(f"Error: Missing required column {col}")
    
    # Clean up
    merged = merged[merged['salary'].notna() & (merged['salary'] > 0)]
    merged = merged[merged['proj_points'].notna() & (merged['proj_points'] >= 0)]
    
    # Add some derived columns useful for optimization
    merged['value'] = merged['proj_points'] / (merged['salary'] / 1000)  # Points per $1000
    merged['is_home'] = True  # Would need game_info parsing for accuracy
    
    print(f"Successfully merged {len(merged)} players")
    print(f"Position breakdown: {merged['pos'].value_counts().to_dict()}")
    
    return merged

def solve(df, n_lineups=10, salary_cap=50000, min_salary=49500, max_from_team=4, exclude=None, 
          uniques=1, randomness=0.0, max_exposure=None, stack_qb_receiver=1, 
          bringback=0, no_opp_dst=False):
    """
    Main optimization solver with all constraints including MINIMUM salary
    """
    exclude = set(exclude or [])
    df = df[~df['name'].isin(exclude)].copy()
    df['id'] = range(len(df))
    
    # Add randomness to projections if specified
    if randomness > 0:
        df = df.copy()
        df['proj_points'] = df['proj_points'] * (1 + np.random.uniform(-randomness, randomness, size=len(df)))
    
    print(f"\nOptimizing {n_lineups} lineups with {len(df)} players")
    print(f"Salary range: ${min_salary} - ${salary_cap}")
    print(f"Avg salary: ${df['salary'].mean():.0f}, Avg projection: {df['proj_points'].mean():.1f} pts")
    
    # Parse exposure caps
    caps = {}
    if max_exposure:
        for item in max_exposure.split(';'):
            if '=' in item:
                name, cap = item.strip().split('=', 1)
                try:
                    caps[name.strip()] = float(cap.strip())
                except ValueError:
                    print(f"Warning: Invalid exposure cap '{cap}' for player '{name}'")
    
    appearances = {}
    lineups = []
    used_sets = set()

    for lineup_num in range(n_lineups):
        print(f"Generating lineup {lineup_num + 1}...")
        
        # Create binary variables for each player
        x = {i: LpVariable(f"x_{i}", 0, 1, LpBinary) for i in df["id"]}
        
        # Create the optimization problem
        prob = LpProblem(f"DK_Optimize_{lineup_num}", LpMaximize)
        
        # Objective: Maximize projected points
        prob += lpSum(x[i] * float(df.loc[df["id"]==i, "proj_points"].values[0]) for i in x)
        
        # Constraint: Salary constraints (BOTH min and max)
        prob += lpSum(x[i] * int(df.loc[df["id"]==i, "salary"].values[0]) for i in x) <= salary_cap
        prob += lpSum(x[i] * int(df.loc[df["id"]==i, "salary"].values[0]) for i in x) >= min_salary
        
        # Constraint: Exactly 9 players
        prob += lpSum(x[i] for i in df["id"]) == 9
        
        # Position constraints
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "QB") == 1
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "DST") == 1
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "RB") >= 2
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "WR") >= 3
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "TE") >= 1
        
        # Stacking constraints
        if stack_qb_receiver > 0:
            # Pre-index receivers by team
            receivers_by_team = {}
            for i, r in df.iterrows():
                if r["pos"] in ("WR", "TE"):
                    receivers_by_team.setdefault(r["team"], []).append(i)
            
            # For each QB, require minimum receivers from same team
            for i, r in df[df["pos"]=="QB"].iterrows():
                team = r["team"]
                same_team_rcvs = receivers_by_team.get(team, [])
                if same_team_rcvs:
                    prob += lpSum(x[j] for j in same_team_rcvs) >= stack_qb_receiver * x[i]
        
        # Bringback constraint
        if bringback == 1:
            opp_of = {}
            for i, r in df.iterrows():
                team, opp = r["team"], r.get("opp", "UNK")
                if isinstance(team, str) and isinstance(opp, str) and team != "UNK" and opp != "UNK":
                    opp_of[team] = opp
            
            for i, r in df[df["pos"]=="QB"].iterrows():
                team = r["team"]
                opp_team = opp_of.get(team)
                if opp_team:
                    opp_rcvs = receivers_by_team.get(opp_team, [])
                    if opp_rcvs:
                        prob += lpSum(x[j] for j in opp_rcvs) >= x[i]
        
        # No opposing DST constraint
        if no_opp_dst:
            for i, r in df.iterrows():
                if r["pos"] in ("QB", "RB", "WR", "TE"):
                    player_team = r["team"]
                    # Find DSTs playing against this team
                    for j, dst_row in df.iterrows():
                        if dst_row["pos"] == "DST" and dst_row.get("opp") == player_team:
                            prob += x[i] + x[j] <= 1
        
        # Team exposure constraint
        for team in df["team"].dropna().unique():
            if team != "UNK":
                tidx = df.index[df["team"]==team]
                prob += lpSum(x[int(df.loc[i, "id"])] for i in tidx) <= max_from_team
        
        # Player exposure constraints
        banned = set()
        for name, count in appearances.items():
            cap = caps.get(name)
            if cap is not None and count >= int(cap * lineup_num + 1e-9):
                banned.add(name)
        
        for i in df["id"]:
            if df.loc[df["id"]==i, "name"].values[0] in banned:
                prob += x[i] == 0
        
        # Uniqueness constraints
        for prev_lineup, _, _ in lineups:
            prev_names = {row["name"] for row in prev_lineup}
            if uniques > 1:
                prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "name"].values[0] in prev_names) <= 9 - uniques
            else:
                prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "name"].values[0] in prev_names) <= 8
        
        # Solve
        prob.solve(PULP_CBC_CMD(msg=False))
        
        if prob.status != 1:
            print(f"❌ Solver failed for lineup {lineup_num + 1}, status: {prob.status}")
            break
        
        # Extract lineup
        chosen = df.loc[[i for i in x if x[i].value()==1]]
        lineup_names = tuple(sorted(chosen["name"]))
        
        if lineup_names in used_sets:
            print(f"❌ Duplicate lineup found, stopping at {len(lineups)} lineups")
            break
        
        used_sets.add(lineup_names)
        total_salary = int(chosen["salary"].sum())
        total_proj = float(chosen["proj_points"].sum())
        
        print(f"✅ Lineup {lineup_num + 1}: ${total_salary}, {total_proj:.2f} pts")
        
        # Format lineup for output
        rows = []
        counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DST": 0, "FLEX": 0}
        
        for _, r in chosen.sort_values("proj_points", ascending=False).iterrows():
            pos = r["pos"]
            
            # Determine slot
            if pos == "QB" and counts["QB"] < 1:
                slot = "QB"
                counts["QB"] += 1
            elif pos == "RB" and counts["RB"] < 2:
                slot = "RB"
                counts["RB"] += 1
            elif pos == "WR" and counts["WR"] < 3:
                slot = "WR"
                counts["WR"] += 1
            elif pos == "TE" and counts["TE"] < 1:
                slot = "TE"
                counts["TE"] += 1
            elif pos == "DST" and counts["DST"] < 1:
                slot = "DST"
                counts["DST"] += 1
            elif pos in FLEX_ELIG and counts["FLEX"] < 1:
                slot = "FLEX"
                counts["FLEX"] += 1
            else:
                slot = pos  # Shouldn't happen
            
            rows.append({
                "slot": slot,
                "name": r["name"],
                "pos": r["pos"],
                "team": r["team"],
                "opp": r.get("opp", "UNK"),
                "salary": int(r["salary"]),
                "proj_points": float(r["proj_points"])
            })
        
        lineups.append((rows, total_salary, total_proj))
        
        # Update appearances
        for _, r in chosen.iterrows():
            appearances[r["name"]] = appearances.get(r["name"], 0) + 1
    
    print(f"\n✅ Generated {len(lineups)} valid lineups")
    return lineups

def write_csv(lineups, output_file):
    """Write lineups to CSV file"""
    out_rows = []
    for idx, (rows, sal, pts) in enumerate(lineups, start=1):
        for r in rows:
            out_rows.append({"lineup": idx, **r})
        out_rows.append({"lineup": idx, "slot": "TOTAL", "salary": sal, "proj_points": pts})
    
    pd.DataFrame(out_rows).to_csv(output_file, index=False)
    print(f"✅ Saved {len(lineups)} lineups to {output_file}")

def main():
    ap = argparse.ArgumentParser(description="DFS Lineup Optimizer with Dynamic Salary Loading and MINIMUM Salary Constraint")
    ap.add_argument("--projections", default="projections.csv", help="Projections CSV file")
    ap.add_argument("--salaries", default="data/DKSalaries.csv", help="DraftKings salary CSV file")
    ap.add_argument("--out", default="lineups.csv", help="Output file for lineups")
    ap.add_argument("--num_lineups", type=int, default=10, help="Number of lineups to generate")
    ap.add_argument("--salary_cap", type=int, default=50000, help="Maximum salary cap")
    ap.add_argument("--min_salary", type=int, default=49500, help="Minimum total salary spend")
    ap.add_argument("--uniques", type=int, default=1, help="Minimum unique players between lineups")
    ap.add_argument("--randomness", type=float, default=0.0, help="Randomness factor (0.0-1.0)")
    ap.add_argument("--max_from_team", type=int, default=4, help="Maximum players from same team")
    ap.add_argument("--exclude", nargs="*", default=[], help="Players to exclude")
    ap.add_argument("--max_exposure", default="", help='Player exposure caps (e.g., "Player Name=0.4")')
    ap.add_argument("--stack_qb_receiver", type=int, default=1, help="Minimum receivers from QB's team")
    ap.add_argument("--bringback", type=int, default=0, choices=[0,1], help="Require opponent receiver")
    ap.add_argument("--no_opp_dst", action="store_true", help="Don't use DST against your offense")
    args = ap.parse_args()
    
    # Load data
    projections = load_projections(args.projections)
    salaries = load_dk_salaries(args.salaries)
    
    # Merge projections with salaries using advanced name matching
    player_pool = enhanced_merge_with_analysis(projections, salaries, debug=False)
    
    # Validate we have enough players
    if len(player_pool) < 50:
        print(f"Warning: Only {len(player_pool)} players in pool. May not find valid lineups.")
    
    # Generate lineups
    lineups = solve(
        player_pool,
        n_lineups=args.num_lineups,
        salary_cap=args.salary_cap,
        min_salary=args.min_salary,  # Added minimum salary constraint
        max_from_team=args.max_from_team,
        exclude=args.exclude,
        uniques=args.uniques,
        randomness=args.randomness,
        max_exposure=args.max_exposure,
        stack_qb_receiver=args.stack_qb_receiver,
        bringback=args.bringback,
        no_opp_dst=args.no_opp_dst
    )
    
    # Write output
    write_csv(lineups, args.out)
    
    # Generate reports if available
    try:
        from report_lineups import generate_report
        summary = generate_report(args.out, salary_cap=args.salary_cap)
        print(f"\n📊 Report Summary:")
        print(f"  Lineups: {summary['total_lineups']}")
        print(f"  Errors: {summary['errors_count']}")
        print(f"  Min uniqueness: {summary['min_pair_uniques']} players")
        print(f"  Report files: {summary['reports']}")
    except Exception as e:
        print(f"Report generation skipped: {e}")

if __name__ == "__main__":
    main()
