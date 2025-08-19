#!/usr/bin/env python3
"""
Train DST regression model to predict fantasy points.
Data: nfl_data_py play-by-play + weekly stats (2020–2024).
Output: models/dst_model.pkl
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
        "receptions","targets","sacks","interceptions",
        "sack_fumbles_lost","rushing_fumbles_lost","receiving_fumbles_lost",
        "special_teams_tds","fantasy_points"
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
        g["sacks_avg"] = g["sacks"].shift(1).rolling(3, min_periods=1).mean()
        g["interceptions_avg"] = g["interceptions"].shift(1).rolling(3, min_periods=1).mean()
        g["fumbles_avg"] = (g["sack_fumbles_lost"] + g["rushing_fumbles_lost"] + g["receiving_fumbles_lost"]).shift(1).rolling(3, min_periods=1).mean()
        g["tds_avg"] = (g["passing_tds"] + g["rushing_tds"] + g["receiving_tds"] + g["special_teams_tds"]).shift(1).rolling(3, min_periods=1).mean()
        return g
    df = df.groupby("player_id", group_keys=False).apply(roll)
    return df

def build_dst_training_set(df: pd.DataFrame):
    # Filter to only DST rows
    dst_df = df[df["pos"] == "DST"].dropna(subset=["fantasy_points_ppr"]).copy()
    
    # Features for DST
    feature_cols = ["fp_avg_3", "sacks_avg", "interceptions_avg", "fumbles_avg", "tds_avg"]
    
    # Remove rows with missing features
    dst_df = dst_df.dropna(subset=feature_cols)
    
    if len(dst_df) < 100:  # DST data is more limited
        print(f"Warning: Only {len(dst_df)} DST samples available")
        return None
    
    X = dst_df[feature_cols].fillna(0.0)
    y = dst_df["fantasy_points_ppr"].values
    
    # Train/test split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train RandomForestRegressor (same hyperparameters as other positions)
    model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)
    
    # Evaluate
    preds = model.predict(Xte)
    mae = mean_absolute_error(yte, preds)
    r2 = r2_score(yte, preds)
    
    print(f"[DST Model] Validation MAE: {mae:.2f}")
    print(f"[DST Model] Validation R2: {r2:.3f}")
    print(f"[DST Model] Training samples: {len(Xtr)}")
    print(f"[DST Model] Validation samples: {len(Xte)}")
    
    return model, feature_cols, mae, r2

def main():
    print("Training DST model...")
    
    # Load data
    years = list(range(2020, 2025))
    df = load_weekly(years)
    df = add_rolling_features(df)
    
    # Build DST training set
    result = build_dst_training_set(df)
    
    if result is None:
        print("❌ DST model training failed - insufficient data")
        return
    
    model, features, mae, r2 = result
    
    # Save model
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, "models/dst_model.pkl")
    print(f"✅ Saved DST model to models/dst_model.pkl")
    print(f"Features: {features}")
    print(f"MAE: {mae:.2f}, R2: {r2:.3f}")

if __name__ == "__main__":
    main()
