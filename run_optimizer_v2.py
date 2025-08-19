#!/usr/bin/env python3
"""
Simple wrapper to run the new V2 lineup optimizer
"""

import subprocess
import sys
import os

def run_optimizer():
    """Run the new V2 optimizer with default settings"""
    
    print("🚀 Running Advanced DFS Lineup Optimizer V2")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ['projections.csv', 'data/DKSalaries.csv', 'data/name_aliases.csv']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("\nPlease ensure you have:")
        print("- projections.csv (your player projections)")
        print("- data/DKSalaries.csv (DraftKings salary data)")
        print("- data/name_aliases.csv (name matching aliases)")
        return False
    
    # Build the command
    cmd = [
        sys.executable, "scripts/optimize_lineups_v2.py",
        "--projections", "projections.csv",
        "--salaries", "data/DKSalaries.csv",
        "--aliases", "data/name_aliases.csv",
        "--output", "optimal_lineup_v2.csv",
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
            print("Check optimal_lineup_v2.csv for your lineup")
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
    print("   python run_optimizer_v2.py")
    
    print("\n2️⃣ Custom salary cap:")
    print("   python scripts/optimize_lineups_v2.py --salary-cap 60000")
    
    print("\n3️⃣ Minimum salary constraint:")
    print("   python scripts/optimize_lineups_v2.py --min-salary 45000")
    
    print("\n4️⃣ Custom output file:")
    print("   python scripts/optimize_lineups_v2.py --output my_lineup.csv")
    
    print("\n5️⃣ Custom projections file:")
    print("   python scripts/optimize_lineups_v2.py --projections my_projections.csv")
    
    print("\n6️⃣ Full custom command:")
    print("   python scripts/optimize_lineups_v2.py \\")
    print("     --projections projections.csv \\")
    print("     --salaries data/DKSalaries.csv \\")
    print("     --aliases data/name_aliases.csv \\")
    print("     --output optimal_lineup.csv \\")
    print("     --salary-cap 50000 \\")
    print("     --min-salary 0")

if __name__ == "__main__":
    print("🔗 DFS Lineup Optimizer V2 - Integration Ready!")
    print("This script integrates the new AdvancedNameMatcherV2 for safer name matching.")
    print()
    
    # Run the optimizer
    success = run_optimizer()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Review optimal_lineup_v2.csv")
        print("2. Check reports/ directory for matching details")
        print("3. Use the lineup in DraftKings")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check that all required files exist")
        print("2. Verify your data formats")
        print("3. Check the console output for specific errors")
        print("4. Try running the test scripts first:")
        print("   python test_integration.py")
    
    # Show usage examples
    show_usage()

