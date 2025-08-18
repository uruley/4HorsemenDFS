#!/usr/bin/env python3
"""
Train per-position regression models (QB/RB/WR/TE/DST) to predict PPR fantasy points.
Data: nfl_data_py play-by-play + weekly stats (2020–2024).
Output: models/*.pkl
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import joblib

from nfl_data_py import import_weekly_data

POSITIONS = ["QB","RB","WR","TE","DST"]

def load_weekly(years):
    # Weekly player-level stats contain fantasy_points columns already
    df = import_weekly_data(years)
    # keep needed basics
    cols_keep = [
        "player_id","player_name","position","recent_team","opponent_team",
        "week","season","fantasy_points_ppr",
        "passing_yards","rushing_yards","receiving_yards",
        "rushing_tds","receiving_tds","passing_tds",
        "receptions","targets","sacks","interceptions","fumbles_lost",
        "fantasy_points"
    ]
    df = df[[c for c in cols_keep if c in df.columns]].copy()
    df.rename(columns={
        "recent_team":"team",
        "opponent_team":"opp",
        "position":"pos"
    }, inplace=True)
    df.dropna(subset=["pos","fantasy_points_ppr"], inplace=True)
    return df

def add_rolling_features(df: pd.DataFrame):
    df = df.sort_values(["player_id","season","week"]).copy()
    def roll(g):
        g["fp_avg_3"] = g["fantasy_points_ppr"].shift(1).rolling(3, min_periods=1).mean()
        g["passing_yards_avg"] = g["passing_yards"].shift(1).rolling(3, min_periods=1).mean()
        g["rush_yards_avg"] = g["rushing_yards"].shift(1).rolling(3, min_periods=1).mean()
        g["targets_avg"] = g["targets"].shift(1).rolling(3, min_periods=1).mean() if "targets" in g else np.nan
        g["aDOT_avg"] = np.nan  # placeholder; not in weekly by default
        g["redzone_tgt_rate"] = np.nan  # placeholder
        # DST-ish proxies (per team): we don't have team DST weekly per player; use team aggregates later
        return g
    df = df.groupby("player_id", group_keys=False).apply(roll)
    # opponent ranks (rough): use previous season mean FP allowed by position
    return df

def build_training_sets(df: pd.DataFrame):
    out = {}
    # Minimal feature sets aligned with features_contract.yml
    cfg = {
        "QB": ["fp_avg_3","passing_yards_avg"],
        "RB": ["fp_avg_3","rush_yards_avg"],
        "WR": ["fp_avg_3","targets_avg"],
        "TE": ["fp_avg_3","targets_avg"],
        # DST training is messy with player weekly; skip initial DST model to unblock others
    }
    for pos in ["QB","RB","WR","TE"]:
        sub = df[df["pos"]==pos].dropna(subset=["fantasy_points_ppr"]).copy()
        feats = cfg[pos]
        X = sub[feats].fillna(0.0)
        y = sub["fantasy_points_ppr"].values
        if len(sub) < 500:  # avoid junk models
            continue
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
        model.fit(Xtr, ytr)
        r2 = r2_score(yte, model.predict(Xte))
        out[pos] = (model, feats, r2)
    return out

def main():
    years = list(range(2020, 2025))
    df = load_weekly(years)
    df = add_rolling_features(df)
    models = build_training_sets(df)
    Path("models").mkdir(parents=True, exist_ok=True)
    for pos, (model, feats, r2) in models.items():
        joblib.dump(model, f"models/{pos}_model.pkl")
        print(f"Saved models/{pos}_model.pkl  R2={r2:.3f}  feats={feats}")
    # For QB optimized naming expected by registry:
    if "QB" in models:
        import shutil
        shutil.copyfile("models/QB_model.pkl", "models/QB_model_optimized.pkl")

if __name__ == "__main__":
    main()
