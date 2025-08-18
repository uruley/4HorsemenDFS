#!/usr/bin/env python3
"""
Robust DraftKings DKSalaries normalizer.

Handles schema variants:
- "Game Info" or "GameInfo"
- With or without "Opponent" (derives from Game Info when missing)
- "Position" or "Roster Position" (uses first token before '/')
- Works whether a date exists in Game Info or not

Output columns (contract):
name,pos,team,opp,is_home,salary,game_date,home,away,name_key,is_dst
"""
import argparse, re, sys, os
from pathlib import Path
import pandas as pd

# Import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.normalize import canon_team, is_dst, player_match_key

TEAM_PAIR_RE = re.compile(r"\b([A-Z]{2,3})\s*@\s*([A-Z]{2,3})\b")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")

def parse_gameinfo(gi: str):
    """
    Parse Game Info like: 'CIN@CLE 09/07/2025 01:00PM ET' or 'CIN @ CLE'
    Returns: (away, home, date or None)
    """
    s = str(gi) if gi is not None else ""
    m = TEAM_PAIR_RE.search(s)
    if not m:
        return None, None, None
    away, home = m.group(1), m.group(2)
    d = None
    md = DATE_RE.search(s)
    if md:
        d = pd.to_datetime(md.group(1), format="%m/%d/%Y", errors="coerce")
        if pd.notna(d):
            d = d.date()
        else:
            d = None
    return away, home, d

def pick_position(df: pd.DataFrame) -> pd.Series:
    if "Position" in df.columns:
        return df["Position"].astype(str).str.upper().str.strip()
    if "Roster Position" in df.columns:
        return df["Roster Position"].astype(str).str.split("/").str[0].str.upper().str.strip()
    raise SystemExit("Missing both Position and Roster Position columns")

def derive_columns(dk: pd.DataFrame) -> pd.DataFrame:
    # Normalize column names
    if "Game Info" in dk.columns and "GameInfo" not in dk.columns:
        dk = dk.rename(columns={"Game Info": "GameInfo"})

    # Parse game info → away/home/date
    away_home_date = dk["GameInfo"].apply(parse_gameinfo).tolist()
    dk["away"], dk["home"], dk["game_date"] = zip(*away_home_date)

    # Team and opponent
    dk["team"] = dk["TeamAbbrev"].apply(canon_team)

    if "Opponent" in dk.columns:
        dk["opp"] = dk["Opponent"].apply(canon_team)
    else:
        # Derive opponent from away/home and team when Opponent is absent
        def _opp(row):
            t, a, h = row.get("team"), row.get("away"), row.get("home")
            if t and a and h:
                if t == a: return h
                if t == h: return a
            return None
        dk["opp"] = dk.apply(_opp, axis=1)

    # Is player at home?
    dk["is_home"] = dk.apply(lambda r: (r["team"] == r["home"]) if (pd.notna(r["home"]) and pd.notna(r["team"])) else None, axis=1)

    # Name, position, salary, helpers
    dk["name"] = dk["Name"].astype(str).str.strip()
    dk["pos"] = pick_position(dk)
    dk["salary"] = dk["Salary"]
    dk["name_key"] = dk["name"].apply(player_match_key)
    dk["is_dst"] = dk["name"].apply(is_dst)

    cols = ["name","pos","team","opp","is_home","salary","game_date","home","away","name_key","is_dst"]
    return dk[cols]

def main():
    ap = argparse.ArgumentParser(description="Normalize DraftKings salary data (robust)")
    ap.add_argument("--dk", required=True, help="Path to DKSalaries.csv")
    ap.add_argument("--out", default="normalized_dk.csv", help="Output CSV path")
    args = ap.parse_args()

    dk = pd.read_csv(args.dk)

    # Validate minimum needed columns
    required_any = [
        ("Name",), ("TeamAbbrev",), ("Salary",), ("GameInfo","Game Info")
    ]
    missing = []
    for opts in required_any:
        if not any(o in dk.columns for o in opts):
            missing.append(opts[0] if len(opts)==1 else f"{opts[0]} or {opts[1]}")
    if missing:
        raise SystemExit(f"Missing required DK columns: {missing}")

    # Ensure we have a GameInfo column name to use downstream
    if "GameInfo" not in dk.columns and "Game Info" in dk.columns:
        dk.rename(columns={"Game Info": "GameInfo"}, inplace=True)

    out = derive_columns(dk)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"✅ Wrote {args.out} with {len(out)} rows.")
    print(out.head(12).to_string(index=False))

if __name__ == "__main__":
    main()
