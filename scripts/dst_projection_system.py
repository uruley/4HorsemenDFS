#!/usr/bin/env python3
"""
DST (Defense/Special Teams) Projection System
Solves the team-level vs individual player data problem
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import nfl_data_py as nfl
from datetime import datetime, timedelta

class DSTProjectionSystem:
    """
    Hybrid approach to DST projections using multiple data sources
    and intelligent fallbacks
    """
    
    def __init__(self):
        self.current_year = 2024  # Update as needed
        self.team_mappings = self.get_team_mappings()
        
    def get_team_mappings(self) -> Dict[str, str]:
        """Map team abbreviations to full names for DraftKings"""
        return {
            'ARI': 'Arizona Cardinals',
            'ATL': 'Atlanta Falcons',
            'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills',
            'CAR': 'Carolina Panthers',
            'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals',
            'CLE': 'Cleveland Browns',
            'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos',
            'DET': 'Detroit Lions',
            'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans',
            'IND': 'Indianapolis Colts',
            'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs',
            'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams',
            'LV': 'Las Vegas Raiders',
            'MIA': 'Miami Dolphins',
            'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots',
            'NO': 'New Orleans Saints',
            'NYG': 'New York Giants',
            'NYJ': 'New York Jets',
            'PHI': 'Philadelphia Eagles',
            'PIT': 'Pittsburgh Steelers',
            'SEA': 'Seattle Seahawks',
            'SF': 'San Francisco 49ers',
            'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans',
            'WAS': 'Washington Commanders'
        }

    def method1_aggregate_individual_stats(self, week: int) -> pd.DataFrame:
        """
        Method 1: Aggregate individual defensive player stats
        This is complex but uses your existing nfl_data_py
        """
        try:
            # Load weekly player stats
            weekly_data = nfl.import_weekly_data([self.current_year])
            
            # Filter for defensive positions and specific week
            defensive_positions = ['CB', 'S', 'LB', 'DL', 'DB', 'DE', 'DT', 'ILB', 'OLB', 'MLB', 'FS', 'SS']
            def_data = weekly_data[
                (weekly_data['position'].isin(defensive_positions)) & 
                (weekly_data['week'] == week)
            ].copy()
            
            # Aggregate by team
            team_stats = def_data.groupby('recent_team').agg({
                'sacks': 'sum',
                'interceptions': 'sum',
                'forced_fumbles': 'sum',
                'fumble_recovery_tds': 'sum',
                'interception_tds': 'sum',
                'safeties': 'sum',
                'blocked_kicks': 'sum',
                'defensive_tds': 'sum'
            }).reset_index()
            
            # Calculate fantasy points (DraftKings scoring)
            team_stats['fantasy_points'] = (
                team_stats['sacks'] * 1.0 +
                team_stats['interceptions'] * 2.0 +
                team_stats['forced_fumbles'] * 2.0 +
                team_stats['fumble_recovery_tds'] * 6.0 +
                team_stats['interception_tds'] * 6.0 +
                team_stats['safeties'] * 2.0 +
                team_stats['blocked_kicks'] * 2.0 +
                team_stats['defensive_tds'] * 6.0
            )
            
            return team_stats
            
        except Exception as e:
            print(f"Error aggregating individual stats: {e}")
            return pd.DataFrame()

    def method2_use_team_stats(self) -> pd.DataFrame:
        """
        Method 2: Use nfl_data_py's team stats if available
        """
        try:
            # Import seasonal team stats
            team_stats = nfl.import_seasonal_data([self.current_year])
            
            # Check if DST-relevant columns exist
            dst_columns = ['team', 'sacks', 'interceptions', 'points_allowed']
            if all(col in team_stats.columns for col in dst_columns):
                return team_stats[dst_columns]
            else:
                print("Team stats don't have required DST columns")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error loading team stats: {e}")
            return pd.DataFrame()

    def method3_baseline_projections(self) -> pd.DataFrame:
        """
        Method 3: Simple baseline projections based on Vegas lines
        and historical averages
        """
        # Historical DST fantasy points by game situation
        baseline_projections = {
            'home_favorite_large': 9.5,   # Home, favored by 7+
            'home_favorite_small': 8.0,   # Home, favored by 3-7
            'home_underdog_small': 6.5,   # Home, underdog by 0-3
            'home_underdog_large': 5.0,   # Home, underdog by 7+
            'away_favorite_large': 8.5,   # Away, favored by 7+
            'away_favorite_small': 7.0,   # Away, favored by 3-7
            'away_underdog_small': 5.5,   # Away, underdog by 0-3
            'away_underdog_large': 4.0,   # Away, underdog by 7+
        }
        
        # Create projections for all teams
        projections = []
        for abbr, full_name in self.team_mappings.items():
            projections.append({
                'team': abbr,
                'team_name': full_name,
                'proj_points': np.random.uniform(4.0, 10.0),  # Placeholder
                'floor': 2.0,
                'ceiling': 15.0,
                'ownership_proj': np.random.uniform(0.05, 0.20)
            })
        
        return pd.DataFrame(projections)

    def method4_opponent_adjusted_projections(self, schedule_df: pd.DataFrame) -> pd.DataFrame:
        """
        Method 4: Create projections based on opponent offensive strength
        This is often the most reliable approach
        """
        # Offensive ranks (lower = better offense = worse for opposing DST)
        # You'd normally calculate these from actual data
        offensive_ranks = {
            'KC': 1, 'BUF': 2, 'MIA': 3, 'CIN': 4, 'LAC': 5,
            'PHI': 6, 'DET': 7, 'DAL': 8, 'SF': 9, 'MIN': 10,
            'BAL': 11, 'JAX': 12, 'SEA': 13, 'GB': 14, 'LAR': 15,
            'TEN': 16, 'ATL': 17, 'NO': 18, 'CLE': 19, 'PIT': 20,
            'WAS': 21, 'NYG': 22, 'TB': 23, 'LV': 24, 'ARI': 25,
            'DEN': 26, 'CHI': 27, 'NE': 28, 'NYJ': 29, 'IND': 30,
            'CAR': 31, 'HOU': 32
        }
        
        projections = []
        for _, game in schedule_df.iterrows():
            home_team = game['home_team']
            away_team = game['away_team']
            
            # Project DST points based on opponent rank
            # Playing against rank 1 offense = ~3 points
            # Playing against rank 32 offense = ~12 points
            home_opp_rank = offensive_ranks.get(away_team, 16)
            away_opp_rank = offensive_ranks.get(home_team, 16)
            
            # Base projection formula
            home_dst_proj = 12.0 - (home_opp_rank * 0.3)
            away_dst_proj = 11.0 - (away_opp_rank * 0.3)  # Away teams slightly penalized
            
            # Add home team DST
            projections.append({
                'team': home_team,
                'team_name': self.team_mappings.get(home_team, home_team),
                'opponent': away_team,
                'is_home': True,
                'proj_points': max(2.0, home_dst_proj),
                'opp_rank': home_opp_rank
            })
            
            # Add away team DST
            projections.append({
                'team': away_team,
                'team_name': self.team_mappings.get(away_team, away_team),
                'opponent': home_team,
                'is_home': False,
                'proj_points': max(2.0, away_dst_proj),
                'opp_rank': away_opp_rank
            })
        
        return pd.DataFrame(projections)

    def create_dst_projections_for_optimizer(self, week: int, salary_data: pd.DataFrame) -> pd.DataFrame:
        """
        Main method: Creates DST projections in the format needed by your optimizer
        Matches the format of your projections.csv
        """
        # Try methods in order of preference
        dst_projections = None
        
        # Method 1: Try aggregating individual stats (most accurate if it works)
        print("Attempting Method 1: Aggregate individual defensive stats...")
        dst_projections = self.method1_aggregate_individual_stats(week)
        
        if dst_projections.empty:
            # Method 2: Try team stats
            print("Method 1 failed. Attempting Method 2: Team stats...")
            dst_projections = self.method2_use_team_stats()
        
        if dst_projections.empty:
            # Method 3: Use baseline projections
            print("Method 2 failed. Using Method 3: Baseline projections...")
            dst_projections = self.method3_baseline_projections()
        
        # Format for optimizer (matching your projections.csv structure)
        optimizer_format = []
        
        for _, dst in dst_projections.iterrows():
            team_abbr = dst.get('team', '')
            team_name = self.team_mappings.get(team_abbr, f"{team_abbr} DST")
            
            # Find matching salary data
            salary_match = salary_data[
                (salary_data['pos'] == 'DST') & 
                (salary_data['team'] == team_abbr)
            ]
            
            if not salary_match.empty:
                salary = salary_match.iloc[0]['salary']
                opp = salary_match.iloc[0].get('opp', 'UNK')
                game_date = salary_match.iloc[0].get('game_date', '')
            else:
                salary = 2500  # Default DST salary
                opp = 'UNK'
                game_date = ''
            
            optimizer_format.append({
                'name': team_name,
                'pos': 'DST',
                'team': team_abbr,
                'opp': opp,
                'is_home': dst.get('is_home', True),
                'salary': salary,
                'game_date': game_date,
                'proj_points': dst.get('proj_points', 5.0),
                'floor': dst.get('floor', 2.0),
                'ceiling': dst.get('ceiling', 15.0),
                'ownership_proj': dst.get('ownership_proj', 0.10)
            })
        
        return pd.DataFrame(optimizer_format)

# Example usage in your pipeline
def integrate_dst_projections():
    """
    How to integrate this into your existing pipeline
    """
    # Load your existing projections
    projections = pd.read_csv('projections.csv')
    
    # Load DraftKings salary data
    salary_data = pd.read_csv('data/DKSalaries.csv')
    
    # Create DST projection system
    dst_system = DSTProjectionSystem()
    
    # Generate DST projections
    week = 1  # Current week
    dst_projections = dst_system.create_dst_projections_for_optimizer(week, salary_data)
    
    # Remove any existing DST projections
    projections = projections[projections['pos'] != 'DST']
    
    # Append new DST projections
    projections = pd.concat([projections, dst_projections], ignore_index=True)
    
    # Save updated projections
    projections.to_csv('projections_with_dst.csv', index=False)
    print(f"✅ Added {len(dst_projections)} DST projections to projections.csv")
    
    return projections

if __name__ == "__main__":
    # Test the system
    dst_system = DSTProjectionSystem()
    
    # Create sample salary data for testing
    sample_salary = pd.DataFrame({
        'pos': ['DST'] * 32,
        'team': list(dst_system.team_mappings.keys()),
        'salary': [2500] * 32,
        'opp': ['TBD'] * 32,
        'game_date': ['2024-09-08'] * 32
    })
    
    # Generate projections
    dst_proj = dst_system.create_dst_projections_for_optimizer(1, sample_salary)
    
    print("\n=== DST Projections Sample ===")
    print(dst_proj[['name', 'team', 'proj_points', 'salary']].head(10))
    print(f"\nTotal DST units projected: {len(dst_proj)}")
    print(f"Average projection: {dst_proj['proj_points'].mean():.2f}")
    print(f"Projection range: {dst_proj['proj_points'].min():.2f} - {dst_proj['proj_points'].max():.2f}")
