import json, pandas as pd
from pathlib import Path
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.build import build_features
from models.registry import ModelRegistry

def run(dk_normalized_csv: str, out_csv: str = "projections.csv", report_path: str = "validation_report.json"):
    dk = pd.read_csv(dk_normalized_csv)
    
    # Build features for all positions at once
    feats_by_pos, issues = build_features(dk)
    
    # Initialize ModelRegistry for ML predictions
    registry = ModelRegistry()
    print(f"🔧 Using ModelRegistry with models: {[pos for pos, model in registry.models.items() if model is not None]}")
    
    rows = []
    for pos, sub in feats_by_pos.items():
        if sub.empty:
            issues.setdefault("empty_positions", []).append(pos)
            continue
        try:
            # Use actual ML models for predictions
            if pos in ['QB', 'RB', 'WR', 'TE']:
                try:
                    yhat = registry.predict(pos, sub)
                    print(f"🔍 {pos} ML predictions: {yhat[:5]}")  # Debug
                except Exception as model_error:
                    print(f"⚠️  ML model failed for {pos}, falling back to features: {model_error}")
                    # Fallback to feature averages if ML fails
                    yhat = sub['fp_avg_3'].values
            else:
                # For DST, use a simple baseline (no ML model available)
                yhat = [10.0] * len(sub)
            
            # Prepare output row
            tmp = sub[['name','pos','team','opp','is_home','salary','game_date']].copy()
            tmp['proj_points'] = yhat
            rows.append(tmp)
            
        except Exception as e:
            issues.setdefault("prediction_errors", []).append({pos: str(e)})

    out = pd.concat(rows, axis=0, ignore_index=True) if rows else pd.DataFrame(
        columns=['name','pos','team','opp','is_home','salary','game_date','proj_points']
    )
    out.to_csv(out_csv, index=False)
    with open(report_path, 'w') as f:
        json.dump(issues, f, indent=2, default=str)

    return out, issues

if __name__ == "__main__":
    if not Path("normalized_dk.csv").exists():
        print("Tip: run dk_normalize.py first to create normalized_dk.csv")
    run("normalized_dk.csv")
