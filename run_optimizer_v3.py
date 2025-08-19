#!/usr/bin/env python3
"""
Simple wrapper to run the new V3 lineup optimizer with centralized database
"""

import subprocess
import sys
import os

def run_optimizer():
    """Run the new V3 optimizer with default settings"""
    
    print("🚀 Running Advanced DFS Lineup Optimizer V3 - Centralized Database Edition")
    print("=" * 70)
    print("✅ Using 100% crosswalk coverage - No more fuzzy name matching!")
    print("⚡ Near-instant player identification performance")
    print()
    
    # Check if required files exist
    required_files = ['projections.csv', 'data/DKSalaries.csv', 'data/player_database.db']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("\nPlease ensure you have:")
        print("- projections.csv (your player projections)")
        print("- data/DKSalaries.csv (DraftKings salary data)")
        print("- data/player_database.db (centralized player database)")
        return False
    
    # Build the command
    cmd = [
        sys.executable, "scripts/optimize_lineups_v3.py",
        "--projections", "projections.csv",
        "--salaries", "data/DKSalaries.csv",
        "--output", "optimal_lineup_v3.csv",
        "--salary-cap", "50000"
    ]
    
    print("📋 Running command:")
    print(" ".join(cmd))
    print()
    
    try:
        # Run the optimizer
        result = subprocess.run(cmd, check=True, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ Optimizer completed successfully!")
            print("Check optimal_lineup_v3.csv for your lineup")
            return True
        else:
            print(f"\n❌ Optimizer failed with return code {result.returncode}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Optimizer failed: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ Python executable not found")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def show_usage():
    """Show how to use the optimizer with different options"""
    
    print("\n📖 USAGE EXAMPLES:")
    print("=" * 30)
    
    print("\n1️⃣ Basic usage (default settings):")
    print("   python run_optimizer_v3.py")
    
    print("\n2️⃣ Custom salary cap:")
    print("   python scripts/optimize_lineups_v3.py --salary-cap 60000")
    
    print("\n3️⃣ Multiple lineups:")
    print("   python scripts/optimize_lineups_v3.py --num-lineups 20")
    
    print("\n4️⃣ QB stacking:")
    print("   python scripts/optimize_lineups_v3.py --qb-stack 2")
    
    print("\n5️⃣ Custom output file:")
    print("   python scripts/optimize_lineups_v3.py --output my_lineup.csv")
    
    print("\n6️⃣ Full custom command:")
    print("   python scripts/optimize_lineups_v3.py \\")
    print("     --projections projections.csv \\")
    print("     --salaries data/DKSalaries.csv \\")
    print("     --output optimal_lineup.csv \\")
    print("     --salary-cap 50000 \\")
    print("     --num-lineups 10 \\")
    print("     --qb-stack 1")

if __name__ == "__main__":
    print("🔗 DFS Lineup Optimizer V3 - Centralized Database Ready!")
    print("This version uses 100% crosswalk coverage for instant player identification.")
    print()
    
    # Run the optimizer
    success = run_optimizer()
    
    if success:
        print("\n🎯 Ready to generate optimal lineups!")
        print("💡 Try running with --num-lineups 20 for multiple lineups")
    else:
        print("\n❌ Optimizer failed. Check the errors above.")
        show_usage()
