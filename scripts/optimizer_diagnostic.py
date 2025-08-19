#!/usr/bin/env python3
"""
DFS Optimizer Diagnostic Tool
Diagnose why the optimizer can't find feasible lineups
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class OptimizerDiagnostic:
    """Diagnose DFS optimizer constraint issues"""
    
    def __init__(self):
        # Standard DFS lineup requirements
        self.roster_requirements = {
            'QB': 1,
            'RB': 2, 
            'WR': 3,
            'TE': 1,
            'DST': 1,
            'FLEX': 1  # Can be RB, WR, or TE
        }
        
        # DraftKings salary cap
        self.salary_cap = 50000
    
    def diagnose_lineup_feasibility(self, df: pd.DataFrame) -> Dict:
        """Comprehensive diagnosis of why optimizer might fail"""
        
        print("🔍 DIAGNOSING DFS OPTIMIZER CONSTRAINTS")
        print("=" * 50)
        
        # Basic data validation
        basic_checks = self._check_basic_data_quality(df)
        
        # Position availability
        position_checks = self._check_position_availability(df)
        
        # Salary distribution
        salary_checks = self._check_salary_constraints(df)
        
        # Projection quality
        projection_checks = self._check_projection_quality(df)
        
        # Sample lineup attempts
        lineup_attempts = self._attempt_sample_lineups(df)
        
        # Compile results
        diagnosis = {
            'basic': basic_checks,
            'positions': position_checks,
            'salary': salary_checks,
            'projections': projection_checks,
            'lineup_attempts': lineup_attempts
        }
        
        # Print summary
        self._print_diagnosis_summary(diagnosis)
        
        return diagnosis
    
    def _check_basic_data_quality(self, df: pd.DataFrame) -> Dict:
        """Check basic data quality issues"""
        
        print("\n📊 BASIC DATA QUALITY")
        print("-" * 25)
        
        issues = []
        
        # Check required columns
        required_cols = ['Name', 'Position', 'Salary', 'entity_id']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        # Check for nulls in critical columns
        for col in ['Position', 'Salary']:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    issues.append(f"{null_count} null values in {col}")
                    print(f"❌ {null_count} null values in {col}")
        
        # Check salary data types
        if 'Salary' in df.columns:
            try:
                df['Salary'].astype(float)
                print("✓ Salary data is numeric")
            except:
                issues.append("Salary column contains non-numeric values")
                print("❌ Salary column contains non-numeric values")
        
        # Check for duplicate players
        if 'entity_id' in df.columns:
            duplicates = df['entity_id'].duplicated().sum()
            if duplicates > 0:
                issues.append(f"{duplicates} duplicate entity_ids")
                print(f"⚠️  {duplicates} duplicate entity_ids")
            else:
                print("✓ No duplicate players")
        
        total_players = len(df)
        print(f"✓ Total players: {total_players}")
        
        return {
            'total_players': total_players,
            'issues': issues,
            'has_critical_issues': len([i for i in issues if 'Missing columns' in i or 'null values in Salary' in i]) > 0
        }
    
    def _check_position_availability(self, df: pd.DataFrame) -> Dict:
        """Check if enough players available in each position"""
        
        print("\n🏈 POSITION AVAILABILITY")
        print("-" * 25)
        
        if 'Position' not in df.columns:
            return {'error': 'No Position column found'}
        
        # Count players by position
        position_counts = df['Position'].value_counts()
        
        # Check against requirements
        position_status = {}
        total_feasible = True
        
        for pos, required in self.roster_requirements.items():
            if pos == 'FLEX':
                # FLEX can be RB, WR, or TE
                flex_eligible = position_counts.get('RB', 0) + position_counts.get('WR', 0) + position_counts.get('TE', 0)
                available = flex_eligible - self.roster_requirements.get('RB', 0) - self.roster_requirements.get('WR', 0) - self.roster_requirements.get('TE', 0)
                available = max(0, available)
            else:
                available = position_counts.get(pos, 0)
            
            is_sufficient = available >= required
            position_status[pos] = {
                'required': required,
                'available': available,
                'sufficient': is_sufficient
            }
            
            status_icon = "✓" if is_sufficient else "❌"
            print(f"{status_icon} {pos}: {available} available, {required} required")
            
            if not is_sufficient:
                total_feasible = False
        
        print(f"\nPosition feasibility: {'✓ PASS' if total_feasible else '❌ FAIL'}")
        
        return {
            'position_counts': position_counts.to_dict(),
            'position_status': position_status,
            'feasible': total_feasible
        }
    
    def _check_salary_constraints(self, df: pd.DataFrame) -> Dict:
        """Check salary distribution and constraints"""
        
        print("\n💰 SALARY CONSTRAINTS")
        print("-" * 20)
        
        if 'Salary' not in df.columns:
            return {'error': 'No Salary column found'}
        
        # Convert salary to numeric
        df_salary = df.copy()
        df_salary['Salary'] = pd.to_numeric(df_salary['Salary'], errors='coerce')
        
        # Remove players with invalid salaries
        valid_salary_df = df_salary.dropna(subset=['Salary'])
        invalid_count = len(df) - len(valid_salary_df)
        
        if invalid_count > 0:
            print(f"⚠️  {invalid_count} players with invalid salaries")
        
        # Salary statistics
        salary_stats = valid_salary_df['Salary'].describe()
        print(f"Salary range: ${salary_stats['min']:,.0f} - ${salary_stats['max']:,.0f}")
        print(f"Average salary: ${salary_stats['mean']:,.0f}")
        print(f"Salary cap: ${self.salary_cap:,}")
        
        # Check if cheapest possible lineup fits under cap
        cheapest_lineup_cost = self._calculate_cheapest_lineup_cost(valid_salary_df)
        
        # Check if most expensive lineup exceeds reasonable bounds
        most_expensive_cost = self._calculate_most_expensive_lineup_cost(valid_salary_df)
        
        feasible_salary = cheapest_lineup_cost <= self.salary_cap if cheapest_lineup_cost else False
        
        print(f"Cheapest possible lineup: ${cheapest_lineup_cost:,}" if cheapest_lineup_cost else "❌ Cannot calculate cheapest lineup")
        print(f"Most expensive lineup: ${most_expensive_cost:,}" if most_expensive_cost else "❌ Cannot calculate most expensive lineup")
        print(f"Salary feasibility: {'✓ PASS' if feasible_salary else '❌ FAIL'}")
        
        return {
            'salary_stats': salary_stats.to_dict(),
            'invalid_salary_count': invalid_count,
            'cheapest_lineup': cheapest_lineup_cost,
            'most_expensive_lineup': most_expensive_cost,
            'feasible': feasible_salary
        }
    
    def _calculate_cheapest_lineup_cost(self, df: pd.DataFrame) -> int:
        """Calculate cost of cheapest possible lineup"""
        try:
            cheapest_by_pos = {}
            
            for pos, required in self.roster_requirements.items():
                if pos == 'FLEX':
                    # For FLEX, get cheapest from remaining RB/WR/TE after filling required spots
                    flex_eligible = df[df['Position'].isin(['RB', 'WR', 'TE'])].copy()
                    
                    # Remove already counted cheapest players
                    for other_pos in ['RB', 'WR', 'TE']:
                        if other_pos in cheapest_by_pos:
                            already_counted = cheapest_by_pos[other_pos]['count']
                            pos_players = flex_eligible[flex_eligible['Position'] == other_pos].nsmallest(already_counted, 'Salary')
                            flex_eligible = flex_eligible.drop(pos_players.index)
                    
                    if len(flex_eligible) >= 1:
                        cheapest_flex = flex_eligible.nsmallest(1, 'Salary')['Salary'].iloc[0]
                        cheapest_by_pos[pos] = {'cost': cheapest_flex, 'count': 1}
                else:
                    pos_players = df[df['Position'] == pos]
                    if len(pos_players) >= required:
                        cheapest = pos_players.nsmallest(required, 'Salary')['Salary'].sum()
                        cheapest_by_pos[pos] = {'cost': cheapest, 'count': required}
                    else:
                        return None  # Not enough players
            
            total_cost = sum(info['cost'] for info in cheapest_by_pos.values())
            return int(total_cost)
            
        except Exception as e:
            print(f"Error calculating cheapest lineup: {e}")
            return None
    
    def _calculate_most_expensive_lineup_cost(self, df: pd.DataFrame) -> int:
        """Calculate cost of most expensive possible lineup"""
        try:
            most_expensive_by_pos = {}
            
            for pos, required in self.roster_requirements.items():
                if pos == 'FLEX':
                    # For FLEX, get most expensive from remaining RB/WR/TE
                    flex_eligible = df[df['Position'].isin(['RB', 'WR', 'TE'])].copy()
                    
                    # Remove already counted most expensive players
                    for other_pos in ['RB', 'WR', 'TE']:
                        if other_pos in most_expensive_by_pos:
                            already_counted = most_expensive_by_pos[other_pos]['count']
                            pos_players = flex_eligible[flex_eligible['Position'] == other_pos].nlargest(already_counted, 'Salary')
                            flex_eligible = flex_eligible.drop(pos_players.index)
                    
                    if len(flex_eligible) >= 1:
                        most_expensive_flex = flex_eligible.nlargest(1, 'Salary')['Salary'].iloc[0]
                        most_expensive_by_pos[pos] = {'cost': most_expensive_flex, 'count': 1}
                else:
                    pos_players = df[df['Position'] == pos]
                    if len(pos_players) >= required:
                        most_expensive = pos_players.nlargest(required, 'Salary')['Salary'].sum()
                        most_expensive_by_pos[pos] = {'cost': most_expensive, 'count': required}
                    else:
                        return None
            
            total_cost = sum(info['cost'] for info in most_expensive_by_pos.values())
            return int(total_cost)
            
        except Exception as e:
            print(f"Error calculating most expensive lineup: {e}")
            return None
    
    def _check_projection_quality(self, df: pd.DataFrame) -> Dict:
        """Check projection data quality"""
        
        print("\n📈 PROJECTION QUALITY")
        print("-" * 20)
        
        projection_cols = [col for col in df.columns if 'projection' in col.lower() or 'points' in col.lower() or 'score' in col.lower()]
        
        if not projection_cols:
            print("❌ No projection columns found")
            return {'error': 'No projection columns found', 'feasible': False}
        
        print(f"✓ Found projection columns: {projection_cols}")
        
        projection_issues = []
        
        for col in projection_cols:
            null_count = df[col].isnull().sum()
            zero_count = (df[col] == 0).sum()
            negative_count = (df[col] < 0).sum()
            
            if null_count > 0:
                projection_issues.append(f"{null_count} null values in {col}")
                print(f"⚠️  {null_count} null values in {col}")
            
            if zero_count > len(df) * 0.1:  # More than 10% zeros
                projection_issues.append(f"{zero_count} zero values in {col}")
                print(f"⚠️  {zero_count} zero projections in {col}")
            
            if negative_count > 0:
                projection_issues.append(f"{negative_count} negative values in {col}")
                print(f"⚠️  {negative_count} negative projections in {col}")
        
        # Check DST projections specifically
        if 'Position' in df.columns:
            dst_players = df[df['Position'] == 'DST']
            if len(dst_players) > 0:
                dst_with_projections = 0
                for col in projection_cols:
                    dst_with_projections += dst_players[col].notna().sum()
                
                if dst_with_projections == 0:
                    print("⚠️  DST teams have no projections (this may be expected)")
                else:
                    print(f"✓ {dst_with_projections} DST projection values found")
        
        return {
            'projection_columns': projection_cols,
            'issues': projection_issues,
            'feasible': len(projection_issues) == 0
        }
    
    def _attempt_sample_lineups(self, df: pd.DataFrame) -> Dict:
        """Attempt to build sample lineups manually"""
        
        print("\n🧪 SAMPLE LINEUP ATTEMPTS")
        print("-" * 25)
        
        attempts = {}
        
        # Attempt 1: Cheapest possible lineup
        cheapest_attempt = self._build_sample_lineup(df, strategy='cheapest')
        attempts['cheapest'] = cheapest_attempt
        
        # Attempt 2: Balanced lineup
        balanced_attempt = self._build_sample_lineup(df, strategy='balanced')
        attempts['balanced'] = balanced_attempt
        
        return attempts
    
    def _build_sample_lineup(self, df: pd.DataFrame, strategy: str = 'cheapest') -> Dict:
        """Build a sample lineup using specified strategy"""
        
        try:
            lineup = {}
            total_salary = 0
            used_players = set()
            
            # Sort strategy
            if strategy == 'cheapest':
                sort_col = 'Salary'
                ascending = True
            elif strategy == 'balanced':
                sort_col = 'Salary'
                ascending = True  # Start with cheaper players for balanced approach
            else:
                sort_col = 'Salary'
                ascending = True
            
            # Fill required positions
            for pos, required in self.roster_requirements.items():
                if pos == 'FLEX':
                    continue  # Handle FLEX separately
                
                pos_players = df[
                    (df['Position'] == pos) & 
                    (~df.index.isin(used_players))
                ].copy()
                
                if len(pos_players) < required:
                    return {
                        'success': False,
                        'error': f'Not enough {pos} players available',
                        'lineup': lineup,
                        'total_salary': total_salary
                    }
                
                selected = pos_players.sort_values(sort_col, ascending=ascending).head(required)
                
                for _, player in selected.iterrows():
                    lineup[f"{pos}_{len([k for k in lineup.keys() if k.startswith(pos)]) + 1}"] = {
                        'name': player['Name'],
                        'position': player['Position'],
                        'salary': player['Salary'],
                        'entity_id': player.get('entity_id', 'N/A')
                    }
                    total_salary += player['Salary']
                    used_players.add(player.name)
            
            # Fill FLEX position
            flex_eligible = df[
                (df['Position'].isin(['RB', 'WR', 'TE'])) & 
                (~df.index.isin(used_players))
            ].copy()
            
            if len(flex_eligible) < 1:
                return {
                    'success': False,
                    'error': 'No FLEX eligible players available',
                    'lineup': lineup,
                    'total_salary': total_salary
                }
            
            flex_player = flex_eligible.sort_values(sort_col, ascending=ascending).iloc[0]
            lineup['FLEX'] = {
                'name': flex_player['Name'],
                'position': flex_player['Position'],
                'salary': flex_player['Salary'],
                'entity_id': flex_player.get('entity_id', 'N/A')
            }
            total_salary += flex_player['Salary']
            
            # Check salary cap
            under_cap = total_salary <= self.salary_cap
            
            print(f"✓ {strategy.title()} lineup: ${total_salary:,} ({'✓ VALID' if under_cap else '❌ OVER CAP'})")
            
            return {
                'success': True,
                'lineup': lineup,
                'total_salary': total_salary,
                'under_cap': under_cap,
                'remaining_salary': self.salary_cap - total_salary
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'lineup': {},
                'total_salary': 0
            }
    
    def _print_diagnosis_summary(self, diagnosis: Dict):
        """Print summary of diagnosis"""
        
        print("\n🎯 DIAGNOSIS SUMMARY")
        print("=" * 25)
        
        # Check each area
        areas = [
            ('Basic Data', diagnosis['basic']['has_critical_issues'], True),
            ('Position Counts', not diagnosis['positions'].get('feasible', False), True),
            ('Salary Constraints', not diagnosis['salary'].get('feasible', False), True),
            ('Projections', not diagnosis['projections'].get('feasible', False), False)  # Projections not critical for feasibility
        ]
        
        critical_issues = []
        
        for area_name, has_issue, is_critical in areas:
            if has_issue:
                icon = "❌" if is_critical else "⚠️ "
                print(f"{icon} {area_name}: ISSUE FOUND")
                if is_critical:
                    critical_issues.append(area_name)
            else:
                print(f"✓ {area_name}: OK")
        
        # Overall recommendation
        print(f"\n{'❌ CRITICAL ISSUES FOUND' if critical_issues else '✅ NO CRITICAL ISSUES'}")
        
        if critical_issues:
            print("Fix these issues first:")
            for issue in critical_issues:
                print(f"  - {issue}")
        else:
            print("Optimizer should be able to find lineups.")
            print("If still failing, check your optimizer code/constraints.")

def main():
    """Run the diagnostic on your matched data"""
    
    try:
        # Load your matched data
        # Replace with your actual matched data file
        df = pd.read_csv("reports/matched_players_v5.csv")  # or whatever your file is called
        
        diagnostic = OptimizerDiagnostic()
        results = diagnostic.diagnose_lineup_feasibility(df)
        
        return results
        
    except FileNotFoundError:
        print("❌ Could not find matched data file.")
        print("Please update the file path in main() to point to your actual matched data.")
    except Exception as e:
        print(f"❌ Error running diagnostic: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()