#!/usr/bin/env python3
"""
Build projections.csv for the optimizer using:
1. ML models (QB/RB/WR/TE) 
2. DST projection system (fallback)
3. DraftKings salary data
"""

import argparse
import pandas as pd
import numpy as np
import joblib
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.dst_projection_system import DSTProjectionSystem

def load_ml_model(position: str) -> object:
    """Load trained ML model for a position"""
    model_path = f"models/{position}_model.pkl"
    try:
        model = joblib.load(model_path)
        print(f"✅ Loaded {position} model from {model_path}")
        return model
    except Exception as e:
        print(f"❌ Failed to load {position} model: {e}")
        return None

def get_historical_features(season: int, week: int, position: str) -> pd.DataFrame:
    """
    Get historical features for ML model predictions
    This is a simplified version - you'd normally load from nfl_data_py
    """
    try:
        import nfl_data_py as nfl
        
        # Load weekly data for the season
        weekly_data = nfl.import_weekly_data([season])
        
        # Filter for position and recent weeks
        pos_data = weekly_data[weekly_data['position'] == position].copy()
        
        # Sort by player and week
        pos_data = pos_data.sort_values(['player_id', 'week'])
        
        # Calculate rolling averages (3-game)
        features = []
        for player_id in pos_data['player_id'].unique():
            player_data = pos_data[pos_data['player_id'] == player_id].copy()
            
            if len(player_data) >= 3:
                # Get last 3 games
                recent = player_data.tail(3)
                
                # Calculate features based on position
                if position == 'QB':
                    fp_avg_3 = recent['fantasy_points_ppr'].mean()
                    passing_yards_avg = recent['passing_yards'].mean()
                    rush_yards_avg = recent['rushing_yards'].mean()
                    tds_avg = recent['passing_tds'].mean() + recent['rushing_tds'].mean()
                    
                    features.append({
                        'player_id': player_id,
                        'name': player_data.iloc[-1]['player_name'],
                        'team': player_data.iloc[-1]['recent_team'],
                        'fp_avg_3': fp_avg_3,
                        'passing_yards_avg': passing_yards_avg,
                        'rush_yards_avg': rush_yards_avg,
                        'tds_avg': tds_avg
                    })
                    
                elif position == 'RB':
                    fp_avg_3 = recent['fantasy_points_ppr'].mean()
                    rush_yards_avg = recent['rushing_yards'].mean()
                    
                    features.append({
                        'player_id': player_id,
                        'name': player_data.iloc[-1]['player_name'],
                        'team': player_data.iloc[-1]['recent_team'],
                        'fp_avg_3': fp_avg_3,
                        'rush_yards_avg': rush_yards_avg
                    })
                    
                elif position in ['WR', 'TE']:
                    fp_avg_3 = recent['fantasy_points_ppr'].mean()
                    targets_avg = recent['targets'].mean()
                    
                    features.append({
                        'player_id': player_id,
                        'name': player_data.iloc[-1]['player_name'],
                        'team': player_data.iloc[-1]['recent_team'],
                        'fp_avg_3': fp_avg_3,
                        'targets_avg': targets_avg
                    })
        
        return pd.DataFrame(features)
        
    except Exception as e:
        print(f"❌ Error loading historical data: {e}")
        return pd.DataFrame()

def predict_with_ml_model(model: object, features: pd.DataFrame, position: str) -> pd.DataFrame:
    """Make predictions using ML model"""
    if model is None or features.empty:
        return pd.DataFrame()
    
    try:
        # Select feature columns based on position
        if position == 'QB':
            # QB model was trained with only ['fp_avg_3', 'passing_yards_avg']
            feature_cols = ['fp_avg_3', 'passing_yards_avg']
            # Check if we have these features
            missing_features = [col for col in feature_cols if col not in features.columns]
            if missing_features:
                print(f"⚠️  Missing QB features: {missing_features}")
                return pd.DataFrame()
        elif position == 'RB':
            feature_cols = ['fp_avg_3', 'rush_yards_avg']
        elif position in ['WR', 'TE']:
            feature_cols = ['fp_avg_3', 'targets_avg']
        else:
            return pd.DataFrame()
        
        # Ensure all features exist
        missing_cols = [col for col in feature_cols if col not in features.columns]
        if missing_cols:
            print(f"⚠️  Missing features for {position}: {missing_cols}")
            return pd.DataFrame()
        
        # Make predictions
        X = features[feature_cols].fillna(0)
        predictions = model.predict(X)
        
        # Create results DataFrame
        results = features[['player_id', 'name', 'team']].copy()
        results['proj_points'] = predictions
        results['pos'] = position
        
        print(f"✅ Generated {len(results)} {position} projections")
        return results
        
    except Exception as e:
        print(f"❌ Error predicting {position}: {e}")
        return pd.DataFrame()

def create_dst_projections() -> pd.DataFrame:
    """Create DST projections using the fallback system"""
    try:
        dst_system = DSTProjectionSystem()
        
        # Create sample salary data for DST
        sample_salary = pd.DataFrame({
            'pos': ['DST'] * 32,
            'team': list(dst_system.team_mappings.keys()),
            'salary': [2500] * 32,
            'opp': ['TBD'] * 32,
            'game_date': ['2024-09-08'] * 32
        })
        
        # Generate DST projections
        dst_proj = dst_system.create_dst_projections_for_optimizer(1, sample_salary)
        
        # Add player_id for consistency
        dst_proj['player_id'] = dst_proj['team']
        
        print(f"✅ Generated {len(dst_proj)} DST projections")
        return dst_proj
        
    except Exception as e:
        print(f"❌ Error creating DST projections: {e}")
        return pd.DataFrame()

def merge_with_salaries(projections: pd.DataFrame, dk_salaries_path: str) -> pd.DataFrame:
    """Merge projections with DraftKings salary data"""
    try:
        # Load DraftKings salaries
        dk_salaries = pd.read_csv(dk_salaries_path)
        
        # Merge on name and position
        merged = pd.merge(
            projections, 
            dk_salaries[['Name', 'Position', 'Salary', 'TeamAbbrev', 'Game Info']],
            left_on=['name', 'pos'],
            right_on=['Name', 'Position'],
            how='left'
        )
        
        # Clean up and format
        final = pd.DataFrame({
            'name': merged['name'],
            'pos': merged['pos'],
            'team': merged['team'],
            'opp': merged['Game Info'].fillna('UNK'),  # Use Game Info for opponent info
            'salary': merged['Salary'].fillna(2500),
            'proj_points': merged['proj_points']
        })
        
        # Remove duplicates and sort
        final = final.drop_duplicates(subset=['name', 'pos']).reset_index(drop=True)
        
        print(f"✅ Merged with salaries: {len(final)} players")
        return final
        
    except Exception as e:
        print(f"❌ Error merging with salaries: {e}")
        # Return projections without salary data
        return projections[['name', 'pos', 'team', 'proj_points']].copy()

def main():
    parser = argparse.ArgumentParser(description="Build projections for DFS optimizer")
    parser.add_argument("--season", type=int, required=True, help="NFL season year")
    parser.add_argument("--week", type=int, required=True, help="NFL week number")
    parser.add_argument("--out", required=True, help="Output projections CSV path")
    args = parser.parse_args()
    
    print(f"🏈 Building projections for {args.season} Week {args.week}")
    
    all_projections = []
    
    # 1. Generate projections for each position using ML models
    positions = ['QB', 'RB', 'WR', 'TE']
    
    for pos in positions:
        print(f"\n--- {pos} Projections ---")
        
        # Load ML model
        model = load_ml_model(pos)
        
        # Get historical features
        features = get_historical_features(args.season, args.week, pos)
        
        if not features.empty:
            # Make predictions
            pos_projections = predict_with_ml_model(model, features, pos)
            if not pos_projections.empty:
                all_projections.append(pos_projections)
        else:
            print(f"⚠️  No features available for {pos}, skipping")
    
    # 2. Generate DST projections using fallback system
    print(f"\n--- DST Projections ---")
    dst_projections = create_dst_projections()
    if not dst_projections.empty:
        all_projections.append(dst_projections)
    
    # 3. Combine all projections
    if all_projections:
        combined = pd.concat(all_projections, ignore_index=True)
        print(f"\n✅ Total projections: {len(combined)} players")
        
        # 4. Merge with salary data if available
        dk_salaries_path = "data/DKSalaries.csv"
        if os.path.exists(dk_salaries_path):
            final_projections = merge_with_salaries(combined, dk_salaries_path)
        else:
            print("⚠️  DKSalaries.csv not found, using projections without salary data")
            final_projections = combined
        
        # 5. Save to file
        final_projections.to_csv(args.out, index=False)
        print(f"✅ Saved projections to {args.out}")
        
        # 6. Summary
        pos_counts = final_projections['pos'].value_counts()
        print(f"\n📊 Position breakdown:")
        for pos, count in pos_counts.items():
            print(f"   {pos}: {count}")
            
    else:
        print("❌ No projections generated")
        sys.exit(1)

if __name__ == "__main__":
    main()
