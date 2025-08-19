#!/usr/bin/env python3
"""
Test script for 4HorsemenDFS optimizer
Tests both clean projections and DK export formats
"""

import subprocess
import sys
import os

def test_case_a():
    """Test Case A: Clean projections file"""
    print("=== Test Case A: Clean projections file ===")
    
    cmd = [
        "python", "scripts/optimize_lineups_v2.py",
        "--projections", "projections.csv",
        "--salaries", "data/DKSalaries.csv",
        "--num-lineups", "1",
        "--salary-cap", "50000",
        "--min-salary", "49500"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Case A PASSED: Clean projections file")
            print("Output:", result.stdout[-500:])  # Last 500 chars
        else:
            print("❌ Case A FAILED")
            print("Error:", result.stderr)
    except subprocess.TimeoutExpired:
        print("❌ Case A TIMEOUT: Took too long")
    except Exception as e:
        print(f"❌ Case A ERROR: {e}")

def test_case_b():
    """Test Case B: DK export format"""
    print("\n=== Test Case B: DK export format ===")
    
    cmd = [
        "python", "scripts/optimize_lineups_v2.py",
        "--projections", "data/DKSalaries.csv",
        "--salaries", "data/DKSalaries.csv",
        "--num-lineups", "1",
        "--salary-cap", "50000",
        "--min-salary", "49500"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Case B PASSED: DK export format")
            print("Output:", result.stdout[-500:])  # Last 500 chars
        else:
            print("❌ Case B FAILED")
            print("Error:", result.stderr)
    except subprocess.TimeoutExpired:
        print("❌ Case B TIMEOUT: Took too long")
    except Exception as e:
        print(f"❌ Case B ERROR: {e}")

def test_multiple_lineups():
    """Test multiple lineup generation"""
    print("\n=== Test Multiple Lineups ===")
    
    cmd = [
        "python", "scripts/optimize_lineups_v2.py",
        "--projections", "projections.csv",
        "--salaries", "data/DKSalaries.csv",
        "--num-lineups", "3",
        "--salary-cap", "50000",
        "--min-salary", "49500",
        "--uniq-shared", "7",
        "--alpha", "0.04",
        "--qb-stack", "1",
        "--max-team", "4"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("✅ Multiple Lineups PASSED")
            print("Output:", result.stdout[-500:])  # Last 500 chars
            
            # Check if output files were created
            if os.path.exists("outputs/lineup_01.csv"):
                print("✅ Output files created")
            else:
                print("❌ Output files missing")
        else:
            print("❌ Multiple Lineups FAILED")
            print("Error:", result.stderr)
    except subprocess.TimeoutExpired:
        print("❌ Multiple Lineups TIMEOUT: Took too long")
    except Exception as e:
        print(f"❌ Multiple Lineups ERROR: {e}")

if __name__ == "__main__":
    print("4HorsemenDFS Optimizer Test Suite")
    print("=" * 40)
    
    test_case_a()
    test_case_b()
    test_multiple_lineups()
    
    print("\nTest suite completed!")
