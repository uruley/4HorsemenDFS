#!/usr/bin/env python3
"""
Train RB regression model to predict fantasy points.
Data: nfl_data_py play-by-play + weekly stats (2020–2024).
Output: models/rb_model.pkl
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
        g["rush_yards_avg"] = g["rushing_yards"].shift(1).rolling(3, min_periods=1).mean()
        g["receptions_avg"] = g["receptions"].shift(1).rolling(3, min_periods=1).mean()
        g["targets_avg"] = g["targets"].shift(1).rolling(3, min_periods=1).mean() if "targets" in g else np.nan
        return g
    df = df.groupby("player_id", group_keys=False).apply(roll)
    return df

def build_rb_training_set(df: pd.DataFrame):
    # Filter to only RB rows
    rb_df = df[df["pos"] == "RB"].dropna(subset=["fantasy_points_ppr"]).copy()
    
    # Features for RB (same as existing script)
    feature_cols = ["fp_avg_3", "rush_yards_avg"]
    
    # Remove rows with missing features
    rb_df = rb_df.dropna(subset=feature_cols)
    
    if len(rb_df) < 500:  # avoid junk models
        print(f"Warning: Only {len(rb_df)} RB samples available")
        return None
    
    X = rb_df[feature_cols].fillna(0.0)
    y = rb_df["fantasy_points_ppr"].values
    
    # Train/test split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train RandomForestRegressor (same hyperparameters as existing)
    model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)
    
    # Evaluate
    preds = model.predict(Xte)
    mae = mean_absolute_error(yte, preds)
    r2 = r2_score(yte, preds)
    
    print(f"[RB Model] Validation MAE: {mae:.2f}")
    print(f"[RB Model] Validation R2: {r2:.3f}")
    print(f"[RB Model] Training samples: {len(Xtr)}")
    print(f"[RB Model] Validation samples: {len(Xte)}")
    
    return model, feature_cols, mae, r2

def main():
    print("Training RB model...")
    
    # Load data
    years = list(range(2020, 2025))
    df = load_weekly(years)
    df = add_rolling_features(df)
    
    # Build RB training set
    result = build_rb_training_set(df)
    
    if result is None:
        print("❌ RB model training failed - insufficient data")
        return
    
    model, features, mae, r2 = result
    
    # Save model
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, "models/rb_model.pkl")
    print(f"✅ Saved RB model to models/rb_model.pkl")
    print(f"Features: {features}")
    print(f"MAE: {mae:.2f}, R2: {r2:.3f}")

if __name__ == "__main__":
    main()
