#!/usr/bin/env python3
"""
Simple DK lineup optimizer using PuLP.

- Reads projections.csv with cols:
  name,pos,team,opp,is_home,salary,game_date,proj_points
- Roster: QB(1), RB(2), WR(3), TE(1), FLEX(1 from RB/WR/TE), DST(1)
- Salary cap: configurable (default 50000)
- Outputs top N lineups to specified file
- Supports uniqueness constraints and randomness
"""
import argparse, itertools, random
import pandas as pd
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, PULP_CBC_CMD

ROSTER_REQ = {"QB":1, "RB":2, "WR":3, "TE":1, "DST":1}
FLEX_ELIG = {"RB","WR","TE"}

def load_pool(path):
    df = pd.read_csv(path)
    # basic cleanups
    df = df[df["proj_points"].notna() & df["salary"].notna()]
    df["pos"] = df["pos"].str.upper().str.replace("FLEX","", regex=False).str.strip()
    return df

def solve(df, n_lineups=10, salary_cap=50000, max_from_team=4, exclude=None, uniques=1, randomness=0.0):
    exclude = set(exclude or [])
    df = df[~df["name"].isin(exclude)].copy()
    df["id"] = range(len(df))
    
    # Add randomness to projections if specified
    if randomness > 0:
        df = df.copy()
        df["proj_points"] = df["proj_points"] * (1 + random.uniform(-randomness, randomness))
    
    print(f"Solving for {n_lineups} lineups with {len(df)} players, salary cap {salary_cap}")
    
    lineups = []
    used_sets = set()

    for lineup_num in range(n_lineups):
        print(f"Generating lineup {lineup_num + 1}...")
        
        x = {i: LpVariable(f"x_{i}", 0, 1, LpBinary) for i in df["id"]}

        prob = LpProblem(f"DK_Optimize_{lineup_num}", LpMaximize)
        prob += lpSum(x[i] * float(df.loc[df["id"]==i, "proj_points"].values[0]) for i in x)

        # salary cap
        prob += lpSum(x[i] * int(df.loc[df["id"]==i, "salary"].values[0]) for i in x) <= salary_cap

        # --- Basic roster constraints (no explicit FLEX constraint) ---

        # exactly 9 players
        prob += lpSum(x[i] for i in df["id"]) == 9

        # positions (use == for singletons, >= for groups)
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "QB") == 1
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "DST") == 1
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "RB") >= 2
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "WR") >= 3
        prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "pos"].values[0] == "TE") >= 1

        # optional team exposure
        for team in df["team"].dropna().unique():
            tidx = df.index[df["team"]==team]
            prob += lpSum(x[int(df.loc[i, "id"])] for i in tidx) <= max_from_team

        # Add constraints to avoid previous lineups
        for prev_lineup, _, _ in lineups:
            prev_names = {row["name"] for row in prev_lineup}
            # For uniques > 1, we need to ensure at least 'uniques' different players
            if uniques > 1:
                # Count how many players from current lineup are in previous lineup
                # We want at least 'uniques' different players
                prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "name"].values[0] in prev_names) <= 9 - uniques
            else:
                # For uniques = 1, just avoid exact duplicates
                prob += lpSum(x[i] for i in df["id"] if df.loc[df["id"]==i, "name"].values[0] in prev_names) <= 8

        prob.solve(PULP_CBC_CMD(msg=False))
        if prob.status != 1:
            print(f"❌ Solver failed for lineup {lineup_num + 1}, status: {prob.status}")
            break
            
        chosen = df.loc[[i for i in x if x[i].value()==1]]
        lineup_names = tuple(sorted(chosen["name"]))
        if lineup_names in used_sets:
            print(f"❌ Duplicate lineup found, stopping at {len(lineups)} lineups")
            break
            
        used_sets.add(lineup_names)
        total_salary = int(chosen["salary"].sum())
        total_proj = float(chosen["proj_points"].sum())
        
        print(f"✅ Lineup {lineup_num + 1}: ${total_salary}, {total_proj:.2f} pts")
        
        # classify one FLEX (pick lowest-scarcity or highest proj among RB/WR/TE not filling min)
        # simple: mark an extra from RB/WR/TE as FLEX by lowest proj tag to avoid dup labels
        counts = chosen["pos"].value_counts().to_dict()
        needed = {"QB":1,"RB":2,"WR":3,"TE":1,"DST":1}
        rows = []
        # assign slots
        assigned = {"QB":[],"RB":[],"WR":[],"TE":[],"DST":[],"FLEX":[]}
        # primary slots
        for _, r in chosen.sort_values("proj_points", ascending=False).iterrows():
            p = r["pos"]
            if p in needed and needed[p]>0:
                assigned[p].append(r)
                needed[p]-=1
            elif p in FLEX_ELIG:
                assigned["FLEX"].append(r)
            else:
                assigned[p].append(r)
        # save lineup
        for slot in ["QB","RB","RB","WR","WR","WR","TE","FLEX","DST"]:
            r = assigned[slot].pop(0)
            rows.append({
                "slot": slot,
                "name": r["name"],
                "pos": r["pos"],
                "team": r["team"],
                "opp": r["opp"],
                "salary": int(r["salary"]),
                "proj_points": float(r["proj_points"])
            })
        lineups.append((rows, total_salary, total_proj))

    print(f"Generated {len(lineups)} lineups successfully")
    return lineups

def write_csv(lineups, output_file):
    # write CSV
    out_rows = []
    for idx,(rows, sal, pts) in enumerate(lineups, start=1):
        for r in rows:
            out_rows.append({"lineup": idx, **r})
        out_rows.append({"lineup": idx, "slot": "TOTAL", "salary": sal, "proj_points": pts})
    pd.DataFrame(out_rows).to_csv(output_file, index=False)
    print(f"✅ Wrote {output_file} with {len(lineups)} lineups.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projections", default="projections.csv")
    ap.add_argument("--out", default="lineups.csv")
    ap.add_argument("--num_lineups", type=int, default=10)
    ap.add_argument("--salary_cap", type=int, default=50000)
    ap.add_argument("--uniques", type=int, default=1, help="Minimum unique players between lineups")
    ap.add_argument("--randomness", type=float, default=0.0, help="Randomness factor (0.0-1.0)")
    ap.add_argument("--max_from_team", type=int, default=4)
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()

    df = load_pool(args.projections)
    lineups = solve(df, n_lineups=args.num_lineups, salary_cap=args.salary_cap, 
                   max_from_team=args.max_from_team, exclude=args.exclude, 
                   uniques=args.uniques, randomness=args.randomness)
    write_csv(lineups, args.out)
    
    # --- after writing the lineups CSV in scripts/optimizer.py ---
    try:
        from report_lineups import generate_report
        _summary = generate_report(args.out, salary_cap=args.salary_cap)
        print(
            f"[REPORT] Lineups: {_summary['total_lineups']}  "
            f"Errors: {_summary['errors_count']}  "
            f"MinPairOverlap: {_summary['min_pair_overlap']}  "
            f"MinPairUniques: {_summary['min_pair_uniques']}"
        )
        print(f"[REPORT] Files: {_summary['reports']}")
    except Exception as e:
        # Don't fail the entire run if reporting hiccups — just warn
        print(f"[WARN] Reporting step failed: {e}")

if __name__ == "__main__":
    main()
