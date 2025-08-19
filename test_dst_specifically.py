#!/usr/bin/env python3
"""
Test script to specifically check what's happening with DST
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.registry import ModelRegistry
from features.build import build_features
import pandas as pd

def test_dst_specifically():
    print("🧪 Testing DST specifically...")
    
    # Load the normalized DK data
    dk = pd.read_csv("normalized_dk.csv")
    
    # Build features
    feats_by_pos, issues = build_features(dk)
    
    # Check DST features
    dst_features = feats_by_pos.get('DST', pd.DataFrame())
    print(f"\n📊 DST Features Analysis:")
    print(f"   Count: {len(dst_features)} teams")
    print(f"   Columns: {list(dst_features.columns)}")
    
    if not dst_features.empty:
        print(f"\n🔍 DST Feature Values:")
        dst_cols = ['sacks_avg', 'takeaways_avg', 'opp_points_allowed', 'opp_sacks_allowed']
        for col in dst_cols:
            if col in dst_features.columns:
                values = dst_features[col].dropna()
                print(f"   {col}: {len(values)} non-null values, range: {values.min():.2f} to {values.max():.2f}")
                print(f"   {col} sample: {values.head(3).tolist()}")
            else:
                print(f"   {col}: MISSING")
    
    # Test ModelRegistry for DST
    print(f"\n🔍 Testing ModelRegistry for DST:")
    registry = ModelRegistry()
    
    print(f"   DST model exists: {registry.models.get('DST') is not None}")
    print(f"   DST required features: {registry.features_for('DST')}")
    
    if not dst_features.empty:
        try:
            # Try to predict DST
            predictions = registry.predict('DST', dst_features)
            print(f"   ✅ DST predictions generated: {len(predictions)} values")
            print(f"   📊 DST prediction range: {predictions.min():.2f} to {predictions.max():.2f}")
            print(f"   📊 DST sample predictions: {predictions[:5]}")
        except Exception as e:
            print(f"   ❌ DST prediction failed: {e}")
            print(f"   Error type: {type(e).__name__}")
    
    # Check what the projection engine currently does for DST
    print(f"\n🔍 Current Projection Engine DST Handling:")
    print(f"   From projections.csv, DST all get: 10.0 points")
    print(f"   This suggests hardcoded fallback in projection_engine.py")

if __name__ == "__main__":
    test_dst_specifically()
