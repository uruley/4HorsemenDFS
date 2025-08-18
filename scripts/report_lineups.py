# scripts/report_lineups.py
import json
import math
import os
from collections import Counter, defaultdict
from itertools import combinations
import pandas as pd


def _is_total_row(row) -> bool:
    # Your generator writes a "TOTAL" line per lineup; skip those for validation/exposures
    return str(row.get("slot", "")).upper() == "TOTAL"


def _validate_lineup(df_lineup: pd.DataFrame, salary_cap: int = 50000) -> list[str]:
    """Return a list of human-readable validation errors for a single lineup."""
    errs = []

    # 9 players?
    if len(df_lineup) != 9:
        errs.append(f"Expected 9 players, got {len(df_lineup)}")
        return errs  # other checks depend on correct size

    # Salary
    total_salary = df_lineup["salary"].sum()
    if total_salary > salary_cap:
        errs.append(f"Salary {total_salary} exceeds cap {salary_cap}")

    # Position counts
    pos_counts = df_lineup["pos"].value_counts().to_dict()
    need = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DST": 1}
    for p, req in need.items():
        if pos_counts.get(p, 0) < req:
            errs.append(f"Needs at least {req} {p}, has {pos_counts.get(p, 0)}")

    # FLEX must be exactly one, and from RB/WR/TE
    flex_rows = df_lineup[df_lineup["slot"].str.upper() == "FLEX"]
    if len(flex_rows) != 1:
        errs.append(f"Expected exactly 1 FLEX, found {len(flex_rows)}")
    else:
        flex_pos = flex_rows.iloc[0]["pos"]
        if flex_pos not in {"RB", "WR", "TE"}:
            errs.append(f"FLEX must be RB/WR/TE, got {flex_pos}")

    return errs


def _pairwise_uniqueness(all_lineups_names: list[set[str]]) -> dict:
    """Compute minimal overlap and minimal uniqueness across all lineup pairs."""
    min_overlap = math.inf
    min_uniques = math.inf
    worst_pair = None

    for i, j in combinations(range(len(all_lineups_names)), 2):
        overlap = len(all_lineups_names[i] & all_lineups_names[j])
        uniques = 18 - 2 * overlap  # total players across two lineups is 18; uniques = 18 - 2*overlap
        if overlap < min_overlap:
            min_overlap = overlap
            worst_pair = (i + 1, j + 1)  # 1-based for readability
        if uniques < min_uniques:
            min_uniques = uniques

    if min_overlap is math.inf:
        # Only one lineup — define safe defaults
        min_overlap = 0
        min_uniques = 9

    return {
        "min_pair_overlap": int(min_overlap),
        "min_pair_uniques": int(min_uniques),
        "worst_pair": worst_pair,
    }


def _stacking(df_lineup: pd.DataFrame) -> dict:
    """
    Simple stack check:
      - QB has at least 1 WR/TE teammate (same team) => 'has_stack'
      - Optional 'bring_back': at least 1 WR/TE from opposing team of QB
    """
    try:
        qb = df_lineup[df_lineup["pos"] == "QB"].iloc[0]
        qb_team = qb["team"]
        qb_opp = qb.get("opp", "")

        wrte = df_lineup[df_lineup["pos"].isin(["WR", "TE"])]
        has_stack = any(wrte["team"] == qb_team)
        bring_back = any(wrte["team"] == qb_opp)
        return {"qb": qb["name"], "qb_team": qb_team, "has_stack": bool(has_stack), "bring_back": bool(bring_back)}
    except Exception as e:
        # Fallback if stacking analysis fails
        return {"qb": "Unknown", "qb_team": "Unknown", "has_stack": False, "bring_back": False}


def generate_report(lineups_csv: str, salary_cap: int = 50000, out_dir: str | None = None) -> dict:
    """
    Reads lineup CSV, validates each lineup, computes exposures, stacking, and pairwise uniqueness.
    Writes:
      - reports/validation_report.json
      - reports/player_exposure.csv
      - reports/team_exposure.csv
      - reports/stacks.csv
    Returns a small summary dict for printing.
    """
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(lineups_csv) or ".", "reports")
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(lineups_csv)

    # Drop TOTAL rows
    df_clean = df[~df.apply(_is_total_row, axis=1)].copy()

    # Ensure required columns
    required_cols = {"lineup", "slot", "name", "pos", "team", "salary", "proj_points"}
    missing = required_cols - set(df_clean.columns)
    if missing:
        raise ValueError(f"Missing columns in {lineups_csv}: {missing}")

    # Build per-lineup frames
    lineups = []
    for lid, group in df_clean.groupby("lineup"):
        # Make a normalized view with consistent column names
        g = pd.DataFrame({
            "lineup": lid,
            "slot": group["slot"].astype(str),
            "name": group["name"].astype(str),
            "pos": group["pos"].astype(str),
            "team": group["team"].astype(str),
            "opp": group.get("opp", pd.Series([""] * len(group))),
            "salary": pd.to_numeric(group["salary"], errors="coerce").fillna(0).astype(int),
            "proj_points": pd.to_numeric(group["proj_points"], errors="coerce").fillna(0.0),
        })
        lineups.append(g)

    # Validate each lineup
    errors = {}
    stacks_rows = []
    lineup_name_sets = []
    for g in lineups:
        lid = int(g["lineup"].iloc[0])
        errs = _validate_lineup(g, salary_cap=salary_cap)
        if errs:
            errors[str(lid)] = errs
        lineup_name_sets.append(set(g["name"].tolist()))
        stacks_rows.append({"lineup": lid, **_stacking(g)})

    # Pairwise uniqueness
    uniq = _pairwise_uniqueness(lineup_name_sets)

    # Exposures
    players = []
    teams = Counter()
    for g in lineups:
        for _, r in g.iterrows():
            players.append((r["name"], r["pos"], r["team"], r["salary"], r["proj_points"]))
            teams[(r["team"], r["pos"])] += 1

    total_lineups = len(lineups)
    player_counter = Counter((n, p, t) for (n, p, t, _, _) in players)
    exposure_rows = []
    for (name, pos, team), count in player_counter.items():
        rows = [(n, p, t, s, pr) for (n, p, t, s, pr) in players if (n, p, t) == (name, pos, team)]
        avg_salary = sum(r[3] for r in rows) / count
        avg_proj = sum(r[4] for r in rows) / count
        exposure_rows.append({
            "name": name,
            "pos": pos,
            "team": team,
            "appearances": count,
            "exposure_pct": round(100.0 * count / total_lineups, 2),
            "avg_salary": round(avg_salary, 2),
            "avg_proj": round(avg_proj, 3),
        })
    exposure_df = pd.DataFrame(exposure_rows).sort_values(["appearances", "name"], ascending=[False, True])

    team_rows = []
    for (team, pos), count in sorted(teams.items(), key=lambda x: (-x[1], x[0])):
        team_rows.append({
            "team": team, "pos": pos,
            "appearances": count,
            "exposure_pct": round(100.0 * count / total_lineups, 2)
        })
    team_df = pd.DataFrame(team_rows)

    stacks_df = pd.DataFrame(stacks_rows).sort_values("lineup")

    # Write files
    validation_path = os.path.join(out_dir, "validation_report.json")
    exposures_path = os.path.join(out_dir, "player_exposure.csv")
    team_exp_path = os.path.join(out_dir, "team_exposure.csv")
    stacks_path = os.path.join(out_dir, "stacks.csv")

    with open(validation_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_lineups": total_lineups,
            "lineups_with_errors": len(errors),
            "errors": errors,  # dict { lineup_id: [errors...] }
            "pairwise_uniqueness": uniq,  # min_pair_overlap, min_pair_uniques, worst_pair
        }, f, indent=2)

    exposure_df.to_csv(exposures_path, index=False)
    team_df.to_csv(team_exp_path, index=False)
    stacks_df.to_csv(stacks_path, index=False)

    # Return summary for console print
    return {
        "total_lineups": total_lineups,
        "errors_count": len(errors),
        "min_pair_overlap": uniq["min_pair_overlap"],
        "min_pair_uniques": uniq["min_pair_uniques"],
        "reports": {
            "validation_json": validation_path,
            "player_exposure_csv": exposures_path,
            "team_exposure_csv": team_exp_path,
            "stacks_csv": stacks_path,
        }
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lineups", required=True, help="Path to lineup CSV produced by optimizer")
    ap.add_argument("--salary_cap", type=int, default=50000)
    ap.add_argument("--out_dir", default=None)
    args = ap.parse_args()
    summary = generate_report(args.lineups, salary_cap=args.salary_cap, out_dir=args.out_dir)
    print(
        f"[REPORT] Lineups: {summary['total_lineups']}  "
        f"Errors: {summary['errors_count']}  "
        f"MinPairOverlap: {summary['min_pair_overlap']}  "
        f"MinPairUniques: {summary['min_pair_uniques']}\n"
        f"Wrote: {summary['reports']}"
    )
