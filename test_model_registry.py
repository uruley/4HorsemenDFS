#!/usr/bin/env python3
"""
Test script to see if the ModelRegistry actually works with trained models
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.registry import ModelRegistry
from features.build import build_features
import pandas as pd

def test_model_registry():
    print("🧪 Testing ModelRegistry with trained models...")
    
    # Load the normalized DK data
    try:
        dk = pd.read_csv("normalized_dk.csv")
        print(f"✅ Loaded normalized_dk.csv: {len(dk)} players")
    except Exception as e:
        print(f"❌ Failed to load normalized_dk.csv: {e}")
        return
    
    # Build features
    try:
        feats_by_pos, issues = build_features(dk)
        print(f"✅ Built features for positions: {list(feats_by_pos.keys())}")
    except Exception as e:
        print(f"❌ Failed to build features: {e}")
        return
    
    # Test ModelRegistry
    try:
        registry = ModelRegistry()
        print(f"✅ Created ModelRegistry")
        print(f"   Models loaded: {list(registry.models.keys())}")
        print(f"   Models present: {[pos for pos, model in registry.models.items() if model is not None]}")
        print(f"   Models missing: {[pos for pos, model in registry.models.items() if model is None]}")
    except Exception as e:
        print(f"❌ Failed to create ModelRegistry: {e}")
        return
    
    # Test predictions for each position
    for pos in ["QB", "RB", "WR", "TE"]:
        if pos not in feats_by_pos or feats_by_pos[pos].empty:
            print(f"⚠️  No features for {pos}")
            continue
            
        sub = feats_by_pos[pos]
        print(f"\n🔍 Testing {pos} predictions:")
        print(f"   Features available: {list(sub.columns)}")
        print(f"   Required features: {registry.features_for(pos)}")
        
        try:
            # Check if we have required features
            required = registry.features_for(pos)
            missing = [f for f in required if f not in sub.columns]
            if missing:
                print(f"   ❌ Missing features: {missing}")
                continue
                
            # Try to predict
            predictions = registry.predict(pos, sub)
            print(f"   ✅ Predictions generated: {len(predictions)} values")
            print(f"   📊 Prediction range: {predictions.min():.2f} to {predictions.max():.2f}")
            print(f"   📊 Sample predictions: {predictions[:5]}")
            
        except Exception as e:
            print(f"   ❌ Prediction failed: {e}")

if __name__ == "__main__":
    test_model_registry()
