#!/usr/bin/env python3
"""
Cleanup script to remove old/broken files and keep only the working system
"""

import os
import shutil
from pathlib import Path

def cleanup():
    print("🧹 Starting cleanup of old/broken files...")
    
    # Files to delete (old/broken)
    files_to_delete = [
        # Old projection methods
        "scripts/make_projections_from_dk.py",
        "convert_dk_to_projections.py", 
        "projections_with_salaries.csv",
        
        # Old optimizer versions
        "scripts/optimize_lineups.py",
        "scripts/optimize_lineups_v2.py",
        "run_optimizer_v2.py",
        "optimal_lineup_v2.csv",
        
        # Old name matchers (replaced by database)
        "enhanced_name_matcher_v3.py",
        "enhanced_name_matcher_v4.py", 
        "enhanced_name_matcher_v5.py",
        "scripts/enhanced_name_matching.py",
        "scripts/advanced_name_matcher.py",
        "scripts/advanced_name_matcher_v2.py",
        
        # Test/debug files
        "test_*.py",
        "debug_*.py",
        "test_*.csv",
        "test_enhanced_*.csv",
        
        # Old output files
        "my_lineups.csv",
        "this_week_lineups.csv", 
        "lineups.csv",
        
        # Old docs
        "NAME_MATCHING_ANALYSIS.md",
        "MULTI_SOURCE_DATA_STRATEGY.md",
        "OPTIMIZER_README.md",
        
        # Test outputs
        "test_original_constraint.csv",
        "test_lower_min.csv",
        "test_multiple_lineups.csv",
        "test_advanced_final.csv",
        "test_enhanced_final.csv",
        "test_enhanced_v5.csv",
        "test_enhanced_v4.csv",
        "test_enhanced_v3.csv",
        "test_enhanced_v2.csv",
        "test_enhanced.csv",
        
        # Cleanup scripts
        "cleanup_old_files.py",
        "test_dst_specifically.py",
        "test_model_registry.py"
    ]
    
    deleted_count = 0
    for file_pattern in files_to_delete:
        if "*" in file_pattern:
            # Handle wildcard patterns
            if file_pattern.startswith("test_enhanced_*.csv"):
                for file in Path(".").glob("test_enhanced_*.csv"):
                    try:
                        os.remove(file)
                        print(f"🗑️  Deleted: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️  Could not delete {file}: {e}")
            elif file_pattern.startswith("test_*.py"):
                for file in Path(".").glob("test_*.py"):
                    try:
                        os.remove(file)
                        print(f"🗑️  Deleted: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️  Could not delete {file}: {e}")
            elif file_pattern.startswith("debug_*.py"):
                for file in Path(".").glob("debug_*.py"):
                    try:
                        os.remove(file)
                        print(f"🗑️  Deleted: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️  Could not delete {file}: {e}")
            elif file_pattern.startswith("test_*.csv"):
                for file in Path(".").glob("test_*.csv"):
                    try:
                        os.remove(file)
                        print(f"🗑️  Deleted: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️  Could not delete {file}: {e}")
        else:
            # Handle specific files
            if os.path.exists(file_pattern):
                try:
                    os.remove(file_pattern)
                    print(f"🗑️  Deleted: {file_pattern}")
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Could not delete {file_pattern}: {e}")
            else:
                print(f"ℹ️  File not found: {file_pattern}")
    
    print(f"\n✅ Cleanup complete! Deleted {deleted_count} files.")
    print("\n🔍 Remaining files (the working system):")
    
    # Show what's left
    remaining_files = [f for f in os.listdir(".") if os.path.isfile(f) and not f.startswith(".")]
    remaining_files.sort()
    for file in remaining_files:
        print(f"   📄 {file}")

if __name__ == "__main__":
    cleanup()
