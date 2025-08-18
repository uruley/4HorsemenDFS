# features/build.py
import pandas as pd
import numpy as np
from nfl_data_py import import_weekly_data

# Helper: map DK date to NFL season/week (rough; good enough for rolling lookback)
def guess_season_week(date: pd.Timestamp):
    # NFL regular season typically Sep–Jan; treat Aug–Dec as same-year season, Jan as prior season playoffs
    y = date.year
    m = date.month
    if m == 1:
        season = y - 1
    else:
        season = y
    # We won't compute exact week; we will filter strictly to games with (game_date < DK date)
    return season

def _prep_weekly(years):
    w = import_weekly_data(years)
    # Normalize columns we need
    rename = {
        "recent_team":"team",
        "opponent_team":"opp",
        "position":"pos",
        "player_name":"name"
    }
    for k,v in rename.items():
        if k in w.columns:
            w.rename(columns={k:v}, inplace=True)
    # Keep only what we need
    keep = [c for c in [
        "name","pos","team","opp","week","season","game_date",
        "fantasy_points_ppr","passing_yards","rushing_yards","targets"
    ] if c in w.columns]
    w = w[keep].copy()
    # Ensure datetime for game_date if present; if absent, derive (best effort)
    if "game_date" in w.columns:
        w["game_date"] = pd.to_datetime(w["game_date"], errors="coerce")
    return w

def _rolling_features(df: pd.DataFrame):
    df = df.sort_values(["name","season","week"])
    def roll(g):
        g["fp_avg_3"] = g["fantasy_points_ppr"].shift(1).rolling(3, min_periods=1).mean()
        g["passing_yards_avg"] = g.get("passing_yards", pd.Series(index=g.index)).shift(1).rolling(3, min_periods=1).mean()
        g["rush_yards_avg"]    = g.get("rushing_yards", pd.Series(index=g.index)).shift(1).rolling(3, min_periods=1).mean()
        g["targets_avg"]       = g.get("targets", pd.Series(index=g.index)).shift(1).rolling(3, min_periods=1).mean()
        return g
    return df.groupby("name", group_keys=False).apply(roll)

def build_features(dk_df: pd.DataFrame):
    """
    Input: normalized DK df: name,pos,team,opp,is_home,salary,game_date
    Output: dict[pos] -> DataFrame with required features for each pos, using rolling stats
            prior to the DK game_date. Fallbacks to neutral constants if missing.
    """
    issues = {}
    pos_groups = {}
    base = dk_df.copy()
    base["game_date"] = pd.to_datetime(base["game_date"], errors="coerce")

    # Load weekly data for enough history (2020–2025)
    weekly = _prep_weekly(list(range(2020, 2025)))
    weekly = _rolling_features(weekly)

    # ... keep the imports and helpers you already have ...

    HAS_GAME_DATE = "game_date" in weekly.columns and pd.api.types.is_datetime64_any_dtype(weekly["game_date"])

    def attach_row_features(row):
        name = row["name"]
        gdate = row.get("game_date", pd.NaT)
        sub = weekly[weekly["name"] == name].copy()

        # Filter to games prior to DK slate date if we can
        if pd.notna(gdate):
            if HAS_GAME_DATE:
                sub = sub[(sub["game_date"].notna()) & (sub["game_date"] < gdate)]
            elif "season" in sub.columns:
                # Heuristic fallback: keep seasons up to the slate's season
                slate_season = guess_season_week(pd.to_datetime(gdate))
                sub = sub[sub["season"] <= slate_season]

        if sub.empty:
            # Neutral fallbacks
            return pd.Series({
                "fp_avg_3": 10.0,
                "passing_yards_avg": 200.0,
                "rush_yards_avg": 40.0,
                "targets_avg": 6.0,
            })

        last = sub.sort_values(["season","week"]).iloc[-1]
        return pd.Series({
            "fp_avg_3": float(last.get("fp_avg_3", 10.0)),
            "passing_yards_avg": float(last.get("passing_yards_avg", 200.0)),
            "rush_yards_avg": float(last.get("rush_yards_avg", 40.0)),
            "targets_avg": float(last.get("targets_avg", 6.0)),
        })

    # Build feat_df with rolling features attached (as before) ...
    feat_df = base.copy()
    feats = feat_df.apply(attach_row_features, axis=1)
    feat_df = pd.concat([feat_df, feats], axis=1)

    # Ensure DST has required placeholders so registry won't error
    if not {"sacks_avg","takeaways_avg","opp_points_allowed","opp_sacks_allowed"}.issubset(feat_df.columns):
        feat_df["sacks_avg"] = 2.1
        feat_df["takeaways_avg"] = 1.0
        feat_df["opp_points_allowed"] = 22.0
        feat_df["opp_sacks_allowed"] = 2.5

    # Split by position
    pos_groups = {}
    for pos in ["QB","RB","WR","TE","DST"]:
        sub = feat_df[feat_df["pos"] == pos].copy()
        pos_groups[pos] = sub

    return pos_groups, issues
