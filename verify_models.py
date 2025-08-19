#!/usr/bin/env python3
"""
Verification Script - Loads and validates all trained models.
One command: python verify_models.py
"""
import joblib
import os
from pathlib import Path

def verify_model(model_path, position):
    """Verify a single model and return status info."""
    try:
        model = joblib.load(model_path)
        
        # Basic model info
        info = {
            'status': '✅ WORKING',
            'type': type(model).__name__,
            'n_estimators': model.n_estimators,
            'n_features': model.n_features_in_,
            'features': list(model.feature_names_in_) if hasattr(model, 'feature_names_in_') else [],
            'file_size_mb': round(os.path.getsize(model_path) / (1024 * 1024), 1)
        }
        
        # Test prediction
        try:
            # Create sample features based on position
            if position == 'QB':
                sample_features = [[15.2, 245.8]]  # fp_avg_3, passing_yards_avg
            elif position == 'RB':
                sample_features = [[12.5, 85.2]]   # fp_avg_3, rush_yards_avg
            elif position == 'WR':
                sample_features = [[14.8, 8.5]]   # fp_avg_3, targets_avg
            elif position == 'TE':
                sample_features = [[10.2, 6.3]]   # fp_avg_3, targets_avg
            else:
                sample_features = [[10.0, 5.0]]   # generic
            
            prediction = model.predict(sample_features)
            info['sample_prediction'] = round(prediction[0], 2)
            info['prediction_status'] = '✅ SUCCESS'
            
        except Exception as e:
            info['sample_prediction'] = 'N/A'
            info['prediction_status'] = f'❌ FAILED: {str(e)}'
            
        return info
        
    except Exception as e:
        return {
            'status': '❌ FAILED',
            'error': str(e),
            'type': 'N/A',
            'n_estimators': 'N/A',
            'n_features': 'N/A',
            'features': [],
            'file_size_mb': 'N/A',
            'sample_prediction': 'N/A',
            'prediction_status': '❌ NOT TESTED'
        }

def main():
    print("=" * 60)
    print("🏈 DFS MODEL VERIFICATION SCRIPT")
    print("=" * 60)
    
    # Check models directory
    models_dir = Path("models")
    if not models_dir.exists():
        print("❌ Models directory not found!")
        return
    
    # Define expected models
    expected_models = {
        'QB': 'models/qb_model.pkl',
        'RB': 'models/rb_model.pkl', 
        'WR': 'models/wr_model.pkl',
        'TE': 'models/te_model.pkl',
        'DST': 'models/dst_model.pkl'
    }
    
    print(f"\n📁 Models Directory: {models_dir.absolute()}")
    print(f"🔍 Checking {len(expected_models)} expected models...\n")
    
    # Verify each model
    results = {}
    working_count = 0
    
    for position, model_path in expected_models.items():
        print(f"🔍 Verifying {position} Model...")
        
        if os.path.exists(model_path):
            result = verify_model(model_path, position)
            results[position] = result
            
            # Print results
            print(f"   Status: {result['status']}")
            if result['status'] == '✅ WORKING':
                working_count += 1
                print(f"   Type: {result['type']}")
                print(f"   Trees: {result['n_estimators']}")
                print(f"   Features: {result['n_features']}")
                print(f"   Feature Names: {result['features']}")
                print(f"   File Size: {result['file_size_mb']} MB")
                print(f"   Sample Prediction: {result['sample_prediction']}")
                print(f"   Prediction Test: {result['prediction_status']}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        else:
            results[position] = {'status': '❌ FILE NOT FOUND'}
            print(f"   Status: ❌ FILE NOT FOUND")
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for position, result in results.items():
        status_icon = "✅" if result['status'] == '✅ WORKING' else "❌"
        print(f"{status_icon} {position}: {result['status']}")
    
    print(f"\n🎯 Overall Status: {working_count}/{len(expected_models)} models working")
    
    if working_count == len(expected_models):
        print("🎉 ALL MODELS VERIFIED SUCCESSFULLY!")
    elif working_count >= 4:
        print("👍 Most models working - system is operational")
    else:
        print("⚠️  Multiple model failures - system needs attention")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
