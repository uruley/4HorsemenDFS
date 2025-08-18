#!/usr/bin/env python3
"""
Simple DK lineup optimizer using PuLP.

- Reads projections.csv with cols:
  name,pos,team,opp,is_home,salary,game_date,proj_points
- Roster: QB(1), RB(2), WR(3), TE(1), FLEX(1 from RB/WR/TE), DST(1)
- Salary cap: 50000
- Outputs top N lineups to lineups.csv
"""
import argparse, itertools
import pandas as pd
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, PULP_CBC_CMD

ROSTER_REQ = {"QB":1, "RB":2, "WR":3, "TE":1, "DST":1}
FLEX_ELIG = {"RB","WR","TE"}
SALARY_CAP = 50000

def load_pool(path):
    df = pd.read_csv(path)
    # basic cleanups
    df = df[df["proj_points"].notna() & df["salary"].notna()]
    df["pos"] = df["pos"].str.upper().str.replace("FLEX","", regex=False).str.strip()
    return df

def solve(df, n_lineups=10, max_from_team=4, exclude=None):
    exclude = set(exclude or [])
    df = df[~df["name"].isin(exclude)].copy()
    df["id"] = range(len(df))
    x = {i: LpVariable(f"x_{i}", 0, 1, LpBinary) for i in df["id"]}

    prob = LpProblem("DK_Optimize", LpMaximize)
    prob += lpSum(x[i] * float(df.loc[df["id"]==i, "proj_points"].values[0]) for i in x)

    # salary cap
    prob += lpSum(x[i] * int(df.loc[df["id"]==i, "salary"].values[0]) for i in x) <= SALARY_CAP

    # position counts (without FLEX)
    for p, req in ROSTER_REQ.items():
        mask = (df["pos"]==p)
        prob += lpSum(x[i] for i in df.loc[mask, "id"]) == req

    # FLEX exactly 1 from RB/WR/TE
    mask_flex = df["pos"].isin(FLEX_ELIG)
    prob += lpSum(x[i] for i in df.loc[mask_flex, "id"]) == ROSTER_REQ["RB"]+ROSTER_REQ["WR"]+ROSTER_REQ["TE"] + 1

    # optional team exposure
    for team in df["team"].dropna().unique():
        tidx = df.index[df["team"]==team]
        prob += lpSum(x[int(df.loc[i, "id"])] for i in tidx) <= max_from_team

    lineups = []
    used_sets = set()

    for _ in range(n_lineups):
        prob.solve(PULP_CBC_CMD(msg=False))
        if prob.status != 1:
            break
        chosen = df.loc[[i for i in x if x[i].value()==1]]
        lineup_names = tuple(sorted(chosen["name"]))
        if lineup_names in used_sets:
            break
        used_sets.add(lineup_names)
        total_salary = int(chosen["salary"].sum())
        total_proj = float(chosen["proj_points"].sum())
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
        # add diversity: forbid this exact set
        prob += lpSum(x[i] for i in chosen["id"]) <= len(chosen)-1

    # write CSV
    out_rows = []
    for idx,(rows, sal, pts) in enumerate(lineups, start=1):
        for r in rows:
            out_rows.append({"lineup": idx, **r})
        out_rows.append({"lineup": idx, "slot": "TOTAL", "salary": sal, "proj_points": pts})
    pd.DataFrame(out_rows).to_csv("lineups.csv", index=False)
    print(f"✅ Wrote lineups.csv with {len(lineups)} lineups.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projections", default="projections.csv")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max_from_team", type=int, default=4)
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()

    df = load_pool(args.projections)
    solve(df, n_lineups=args.n, max_from_team=args.max_from_team, exclude=args.exclude)

if __name__ == "__main__":
    main()
