#!/usr/bin/env python3
"""
Simple DK NFL optimizer (single lineup) using projections.csv.
Roster: QB, RB, RB, WR, WR, WR, TE, FLEX(RB/WR/TE), DST
Salary cap: configurable (default 50000)

Inputs  : projections.csv with columns:
          name,pos,team,opp,is_home,salary,game_date,proj_points
Output  : lineups.csv with the chosen lineup
"""

import argparse
import sys
import os
import pandas as pd

try:
    import pulp
except Exception:
    pulp = None


ROSTER_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST"]
FLEX_ELIG = {"RB", "WR", "TE"}
REQ_MIN = {"QB": 1, "DST": 1, "RB": 2, "WR": 3, "TE": 1}


def read_projections(path):
    df = pd.read_csv(path)
    # Coerce types
    df["salary"] = pd.to_numeric(df["salary"], errors="coerce").fillna(0).astype(int)
    df["proj_points"] = pd.to_numeric(df["proj_points"], errors="coerce").fillna(0.0)
    # Normalize pos strings
    df["pos"] = df["pos"].str.upper().str.strip()
    # Filter only valid DK positions we handle
    df = df[df["pos"].isin({"QB", "RB", "WR", "TE", "DST"})].copy()
    # Drop rows with missing name or team
    df = df[df["name"].notna() & df["team"].notna()]
    df.reset_index(drop=True, inplace=True)
    return df


def validate_pool(df):
    issues = []
    for p, need in REQ_MIN.items():
        have = (df["pos"] == p).sum()
        if have < need:
            issues.append(f"Not enough {p} (need {need}, have {have})")
    # Need at least one FLEX-eligible extra beyond minima
    if (df["pos"].isin(FLEX_ELIG)).sum() < (REQ_MIN["RB"] + REQ_MIN["WR"] + REQ_MIN["TE"] + 1):
        issues.append("Not enough FLEX-eligible players to fill FLEX slot.")
    return issues


def solve_ilp(df, cap, max_per_team=None, time_limit=10):
    if pulp is None:
        return None, "PuLP not installed."

    n = len(df)
    idx = range(n)

    # Decision vars: x_i ∈ {0,1}
    x = pulp.LpVariable.dicts("x", idx, lowBound=0, upBound=1, cat=pulp.LpBinary)

    model = pulp.LpProblem("DK_NFL_Optimizer", pulp.LpMaximize)

    # Objective: maximize projected points
    model += pulp.lpSum(df.loc[i, "proj_points"] * x[i] for i in idx)

    # Salary cap
    model += pulp.lpSum(df.loc[i, "salary"] * x[i] for i in idx) <= cap

    # Total players = 9
    model += pulp.lpSum(x[i] for i in idx) == 9

    # Positional minimums
    for p, need in REQ_MIN.items():
        model += pulp.lpSum(x[i] for i in idx if df.loc[i, "pos"] == p) >= need

    # Exactly 1 QB & 1 DST (also covered by minima + total=9, but make explicit)
    model += pulp.lpSum(x[i] for i in idx if df.loc[i, "pos"] == "QB") == 1
    model += pulp.lpSum(x[i] for i in idx if df.loc[i, "pos"] == "DST") == 1

    # Optional: team exposure cap (e.g., max 4 from same team)
    if max_per_team is not None and max_per_team > 0:
        for team, group in df.groupby("team").groups.items():
            model += pulp.lpSum(x[i] for i in group) <= max_per_team

    # Solve
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit)
    status = model.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        return None, f"Solver status: {pulp.LpStatus[status]}"

    chosen_idx = [i for i in idx if x[i].value() == 1]
    return df.loc[chosen_idx].copy(), None


def assign_roster_slots(selected: pd.DataFrame) -> pd.DataFrame:
    # Deterministic ordering: better proj first, then salary desc
    selected = selected.sort_values(["proj_points", "salary"], ascending=[False, False]).copy()

    # Base slot requirements (no FLEX here)
    need = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DST": 1}
    assigned = []
    flex_bucket = []

    for _, row in selected.iterrows():
        p = row["pos"]
        if p in need and need[p] > 0:
            slot = p
            need[p] -= 1
            new = dict(row)
            new["slot"] = slot
            assigned.append(new)
        else:
            # Park extras that can go to FLEX
            if p in {"RB", "WR", "TE"}:
                flex_bucket.append(row)
            else:
                # Shouldn't happen (extra QB/DST), but keep it just in case
                new = dict(row)
                new["slot"] = p
                assigned.append(new)

    # Always add exactly one FLEX from the bucket (best remaining)
    if not flex_bucket:
        raise RuntimeError("No FLEX-eligible players available to assign FLEX.")
    flex_bucket.sort(key=lambda r: (r["proj_points"], r["salary"]), reverse=True)
    f = dict(flex_bucket[0])
    f["slot"] = "FLEX"
    assigned.append(f)

    out = pd.DataFrame(assigned)
    # Final columns
    out = out[["slot", "name", "pos", "team", "salary", "proj_points"]]
    # Sort by traditional order
    slot_order = {"QB":0,"RB":1,"WR":2,"TE":3,"FLEX":4,"DST":5}
    out["__order"] = out["slot"].map(slot_order)
    out = out.sort_values("__order").drop(columns="__order")

    # Sanity guard: must be 9 players
    if len(out) != 9:
        raise RuntimeError(f"Lineup has {len(out)} players after assignment, expected 9.")
    
    return out


def optimize_main(projections_path="projections.csv", out_path="lineups.csv", salary_cap=50000, max_per_team=None):
    """Main optimization function that can be called from API or CLI."""
    if not os.path.exists(projections_path):
        return {"error": f"Projections file not found: {projections_path}"}

    df = read_projections(projections_path)
    pool_issues = validate_pool(df)
    if pool_issues:
        return {"error": "Cannot build lineup due to pool issues", "issues": pool_issues}

    selected, err = solve_ilp(df, cap=salary_cap, max_per_team=max_per_team)
    if err:
        return {"error": f"ILP error: {err}", "fallback": "greedy"}
        # Note: Could implement greedy fallback here if needed

    lineup = assign_roster_slots(selected)
    total_salary = int(lineup["salary"].sum())
    total_proj = float(lineup["proj_points"].sum())

    # Convert to dict for JSON response
    lineup_dict = lineup.to_dict('records')
    
    result = {
        "success": True,
        "lineup": lineup_dict,
        "total_salary": total_salary,
        "total_proj": round(total_proj, 2),
        "player_count": len(lineup)
    }
    
    # Optionally save to file
    if out_path:
        lineup.to_csv(out_path, index=False)
        result["saved_to"] = out_path
    
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projections", default="projections.csv", help="Input projections CSV")
    ap.add_argument("--out", default="lineups.csv", help="Output lineup CSV")
    ap.add_argument("--salary_cap", type=int, default=50000, help="DK salary cap")
    ap.add_argument("--max_per_team", type=int, default=None, help="Optional max players per team")
    args = ap.parse_args()

    result = optimize_main(
        projections_path=args.projections,
        out_path=args.out,
        salary_cap=args.salary_cap,
        max_per_team=args.max_per_team
    )
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        if "issues" in result:
            for msg in result["issues"]:
                print(" -", msg)
        sys.exit(1)
    
    print(f"✅ Wrote {args.out} with {result['player_count']} players.")
    print(f"   Total Salary: {result['total_salary']:,}  |  Total Proj: {result['total_proj']}")


if __name__ == "__main__":
    main()
