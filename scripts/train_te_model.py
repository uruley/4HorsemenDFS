#!/usr/bin/env python3
"""
Train TE regression model to predict fantasy points.
Data: nfl_data_py play-by-play + weekly stats (2020–2024).
Output: models/te_model.pkl
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

from nfl_data_py import import_weekly_data

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
        g["targets_avg"] = g["targets"].shift(1).rolling(3, min_periods=1).mean() if "targets" in g else np.nan
        g["receptions_avg"] = g["receptions"].shift(1).rolling(3, min_periods=1).mean()
        g["receiving_yards_avg"] = g["receiving_yards"].shift(1).rolling(3, min_periods=1).mean()
        return g
    df = df.groupby("player_id", group_keys=False).apply(roll)
    return df

def build_te_training_set(df: pd.DataFrame):
    # Filter to only TE rows
    te_df = df[df["pos"] == "TE"].dropna(subset=["fantasy_points_ppr"]).copy()
    
    # Features for TE (same as existing script)
    feature_cols = ["fp_avg_3", "targets_avg"]
    
    # Remove rows with missing features
    te_df = te_df.dropna(subset=feature_cols)
    
    if len(te_df) < 500:  # avoid junk models
        print(f"Warning: Only {len(te_df)} TE samples available")
        return None
    
    X = te_df[feature_cols].fillna(0.0)
    y = te_df["fantasy_points_ppr"].values
    
    # Train/test split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train RandomForestRegressor (same hyperparameters as existing)
    model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)
    
    # Evaluate
    preds = model.predict(Xte)
    mae = mean_absolute_error(yte, preds)
    r2 = r2_score(yte, preds)
    
    print(f"[TE Model] Validation MAE: {mae:.2f}")
    print(f"[TE Model] Validation R2: {r2:.3f}")
    print(f"[TE Model] Training samples: {len(Xtr)}")
    print(f"[TE Model] Validation samples: {len(Xte)}")
    
    return model, feature_cols, mae, r2

def main():
    print("Training TE model...")
    
    # Load data
    years = list(range(2020, 2025))
    df = load_weekly(years)
    df = add_rolling_features(df)
    
    # Build TE training set
    result = build_te_training_set(df)
    
    if result is None:
        print("❌ TE model training failed - insufficient data")
        return
    
    model, features, mae, r2 = result
    
    # Save model
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, "models/te_model.pkl")
    print(f"✅ Saved TE model to models/te_model.pkl")
    print(f"Features: {features}")
    print(f"MAE: {mae:.2f}, R2: {r2:.3f}")

if __name__ == "__main__":
    main()

