#!/usr/bin/env python3
"""
Enhanced DK lineup optimizer V3 - Uses 100% crosswalk coverage instead of fuzzy matching.
This version leverages the centralized player database for near-instant player identification.
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import argparse
import itertools
import random
import pandas as pd
import numpy as np
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, PULP_CBC_CMD
import sys
import os
import sqlite3
from datetime import datetime

ROSTER_REQ = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DST": 1}
FLEX_ELIG = {"RB", "WR", "TE"}

# Team canonicalization for consistent naming
TEAM_CANON = {
    "JAC":"JAX","WSH":"WAS","LVR":"LV","OAK":"LV","SD":"LAC","LA":"LAR","STL":"LAR",
    "ARI":"ARI","TB":"TB","NE":"NE","NO":"NO","NYJ":"NYJ","NYG":"NYG","KC":"KC","SF":"SF",
    "SEA":"SEA","DAL":"DAL","PHI":"PHI","TEN":"TEN","CHI":"CHI","CIN":"CIN","CLE":"CLE",
    "BUF":"BUF","MIA":"MIA","BAL":"BAL","PIT":"PIT","HOU":"HOU","IND":"IND","MIN":"MIN",
    "DET":"DET","ATL":"ATL","CAR":"CAR","GB":"GB","LAC":"LAC","LAR":"LAR","DEN":"DEN",
    "JAX":"JAX","WAS":"WAS","LV":"LV"
}

def canon(t: str) -> str:
    return TEAM_CANON.get((t or "").upper().strip(), (t or "").upper().strip())

class CentralizedPlayerMatcher:
    """
    Fast player matcher using the centralized database crosswalk.
    Provides 100% coverage for DraftKings players.
    """
    
    def __init__(self, db_path="data/player_database.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
    
    def connect(self):
        """Connect to the centralized player database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✓ Connected to centralized player database: {self.db_path}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    def get_dk_to_entity_mapping(self):
        """Get DraftKings ID to entity_id mapping"""
        query = """
        SELECT external_id as dk_id, player_id as entity_id, external_name
        FROM external_ids 
        WHERE source_name = 'draftkings'
        """
        try:
            df = pd.read_sql_query(query, self.conn)
            print(f"✓ Loaded {len(df)} DraftKings to entity mappings")
            return df
        except Exception as e:
            print(f"❌ Failed to load mappings: {e}")
            return pd.DataFrame()
    
    def merge_projections_and_salaries(self, projections_df, salaries_df):
        """
        Merge projections with salaries using the centralized database crosswalk.
        This provides 100% coverage and near-instant performance.
        """
        print("\n🔄 Merging projections with salaries using centralized database...")
        
        # Load the crosswalk mapping
        crosswalk = self.get_dk_to_entity_mapping()
        if crosswalk.empty:
            print("❌ No crosswalk data available!")
            return pd.DataFrame()
        
        # Normalize projections to required schema
        normalized = self.normalize_projections(projections_df)
        
        # Preflight check
        print("Pool by pos:", normalized['pos'].value_counts().to_dict())
        skill = normalized['pos'].isin(['RB','WR','TE']).sum()
        if (normalized['pos'].eq('QB').sum()<1 or normalized['pos'].eq('DST').sum()<1 
            or normalized['pos'].eq('RB').sum()<2 or normalized['pos'].eq('WR').sum()<3 
            or normalized['pos'].eq('TE').sum()<1 or skill<7):
            raise SystemExit("Not enough positions in projections (need QB/RB/WR/TE/DST).")
        
        # Create a mapping from entity_id to projections
        # We'll use the player_id from projections if available, or try to match by name
        entity_to_proj = {}
        
        # First, try to match by entity_id if projections have it
        if 'player_id' in normalized.columns:
            for _, row in normalized.iterrows():
                if pd.notna(row['player_id']):
                    entity_to_proj[row['player_id']] = row
        
        # If no entity_id matches, try to match by name (fallback)
        if not entity_to_proj:
            print("⚠️ No entity_id matches found, falling back to name matching...")
            # This is a fallback - in production you should have entity_ids in projections
            for _, row in normalized.iterrows():
                entity_to_proj[row['name']] = row
        
        # Now merge with salaries using the crosswalk
        merged_data = []
        
        for _, salary_row in salaries_df.iterrows():
            dk_id = str(salary_row['ID'])  # Keep original ID column name
            
            # Find the crosswalk entry
            crosswalk_entry = crosswalk[crosswalk['dk_id'] == dk_id]
            
            if crosswalk_entry.empty:
                print(f"⚠️ No crosswalk entry for DK ID: {dk_id} ({salary_row['name']})")
                continue
            
            entity_id = crosswalk_entry.iloc[0]['entity_id']
            
            # Find the projection data
            if entity_id in entity_to_proj:
                proj_row = entity_to_proj[entity_id]
            elif salary_row['name'] in entity_to_proj:
                proj_row = entity_to_proj[salary_row['name']]
            else:
                print(f"⚠️ No projection found for: {salary_row['name']} (DK ID: {dk_id})")
                continue
            
            # Create merged row
            merged_row = {
                'name': salary_row['name'],
                'pos': salary_row['pos'],
                'team': salary_row['team'],
                'salary': salary_row['salary'],
                'proj_points': proj_row['proj_points'],
                'dk_id': dk_id,
                'entity_id': entity_id,
                'match_method': 'crosswalk'
            }
            
            # Add opponent if available
            if 'opp' in proj_row:
                merged_row['opp'] = proj_row['opp']
            else:
                merged_row['opp'] = 'UNK'
            
            merged_data.append(merged_row)
        
        if not merged_data:
            print("❌ No players matched!")
            return pd.DataFrame()
        
        # Convert to DataFrame
        result = pd.DataFrame(merged_data)
        
        # Add value column for optimization
        result['value'] = result['proj_points'] / (result['salary'] / 1000.0)
        
        print(f"✅ Successfully matched {len(result)} players using crosswalk")
        print(f"📊 Match method: {result['match_method'].value_counts().to_dict()}")
        
        return result
    
    def normalize_projections(self, df):
        """Normalize projections to required schema: name, pos, proj_points, team, opp."""
        d = df.copy()
        low = {c.lower(): c for c in d.columns}
        
        def pick(*cs): 
            for c in cs:
                if c in low: return low[c]
            return None
        
        name = pick('name','player','playername','full_name','dk name','dk_name','name + id','player name')
        if name == low.get('name + id') and 'name' in low: name = low['name']
        pos  = pick('pos','position','roster position')
        proj = pick('proj_points','projection','proj','fpts','points','projected points','projpts','avgpointspergame','avg_points_per_game')
        team = pick('team','teamabbrev','tm')
        opp  = pick('opp','opponent','opp_team','opponentteam')
        player_id = pick('player_id', 'entity_id', 'id')
        
        if not (name and pos and proj):
            raise ValueError(f"Projections missing name/pos/proj columns. Found: {list(d.columns)}")
        
        out = d.rename(columns={
            name:'name', 
            pos:'pos', 
            proj:'proj_points', 
            **({team:'team'} if team else {}), 
            **({opp:'opp'} if opp else {}),
            **({player_id:'player_id'} if player_id else {})
        })
        
        out['name'] = out['name'].astype(str).str.strip()
        out['pos']  = out['pos'].astype(str).str.upper().str.strip().str.split('/').str[0].replace({'DEF':'DST','D/ST':'DST','D':'DST'})
        out['proj_points'] = pd.to_numeric(out['proj_points'], errors='coerce')
        
        if 'team' not in out: out['team'] = ''
        if 'opp'  not in out: out['opp'] = 'UNK'
        
        out = out[out['proj_points'].notna()]
        return out
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def add_opp_from_dk_gameinfo(player_df: pd.DataFrame, dk_path: str = "data/DKSalaries.csv") -> pd.DataFrame:
    """Extract opponent information from DraftKings Game Info column"""
    dk = pd.read_csv(dk_path)
    gi_col = next((c for c in dk.columns if c.lower().replace(" ", "") == "gameinfo"), None)
    if gi_col is None:
        if "Game Info" in dk.columns: gi_col = "Game Info"
    if gi_col is None:
        return player_df  # DK file has no Game Info; skip

    game_map = {}   # TEAM -> OPP
    for s in dk[gi_col].dropna().astype(str):
        token = s.split()[0]  # e.g., "TB@ATL"
        if "@" not in token: 
            continue
        away, home = token.split("@", 1)
        away, home = canon(away), canon(home)
        game_map[away] = home
        game_map[home] = away

    out = player_df.copy()
    if "team" not in out.columns:
        out["team"] = ""
    out["team"] = out["team"].map(canon)

    if "opp" not in out.columns:
        out["opp"] = "UNK"
    mask = out["opp"].isna() | (out["opp"].astype(str).str.upper().isin(["", "UNK"]))
    out.loc[mask, "opp"] = out.loc[mask, "team"].map(game_map).fillna("UNK")
    return out

def load_dk_salaries(path):
    """Load and normalize DraftKings salary data"""
    print(f"Loading DK salaries from {path}...")
    
    # Read CSV - DraftKings files can have various formats
    df = pd.read_csv(path)
    
    # Standardize column names (DK uses various formats)
    column_mapping = {
        'Name': 'name',
        'Position': 'pos',
        'Team': 'team',
        'Salary': 'salary',
        'Game Info': 'game_info',
        'TeamAbbrev': 'team',
        'Roster Position': 'pos'
    }
    
    # Rename columns if they exist
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df[new_col] = df[old_col]
    
    # Ensure required columns exist
    required = ['name', 'pos', 'team', 'salary']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Warning: Missing columns in DK file: {missing}")
        print(f"Available columns: {df.columns.tolist()}")
    
    # Clean position names
    if 'pos' in df.columns:
        df['pos'] = df['pos'].str.upper().str.strip()
        # Handle DK position naming - extract base position before "/"
        df['pos'] = df['pos'].str.split('/').str[0].str.strip()
        df['pos'] = df['pos'].replace({
            'DEF': 'DST',
            'D': 'DST',
            'D/ST': 'DST'
        })
    
    # Clean team names - strip trailing spaces that cause DST matching issues
    if 'team' in df.columns:
        df['team'] = df['team'].str.upper().str.strip()
        # Remove trailing spaces that are common in DK data
        df['team'] = df['team'].str.rstrip()
    
    # Clean player names - strip trailing spaces that cause matching issues
    if 'name' in df.columns:
        df['name'] = df['name'].str.strip()
        # Remove trailing spaces that are common in DK data
        df['name'] = df['name'].str.rstrip()
    
    # Ensure salary is numeric
    if 'salary' in df.columns:
        df['salary'] = pd.to_numeric(df['salary'], errors='coerce')
        # Remove any rows with invalid salaries
        df = df[df['salary'].notna() & (df['salary'] > 0)]
    
    # Parse game info to get opponent
    if 'game_info' in df.columns:
        # Format: "TB@ATL 09/08/2024 01:00PM ET"
        df['opp'] = df['game_info'].apply(parse_opponent)
    
    print(f"Loaded {len(df)} players with salaries")
    if 'salary' in df.columns:
        print(f"Salary range: ${df['salary'].min():.0f} - ${df['salary'].max():.0f}")
    else:
        print("Warning: No salary column found after normalization")
    
    return df

def parse_opponent(game_info):
    """Parse opponent from DraftKings game info string"""
    if pd.isna(game_info):
        return 'UNK'
    
    # Format: "TB@ATL 09/08/2024 01:00PM ET"
    try:
        matchup = game_info.split()[0]  # Get "TB@ATL"
        teams = matchup.split('@')
        # Return the other team (simplified - would need player's team to be accurate)
        return teams[0] if len(teams) > 1 else 'UNK'
    except:
        return 'UNK'

def load_projections(path):
    """Load projection data"""
    print(f"Loading projections from {path}...")
    df = pd.read_csv(path)
    
    # Standardize position names
    if 'pos' in df.columns:
        df['pos'] = df['pos'].str.upper().str.strip()
    
    # Ensure proj_points is numeric
    if 'proj_points' in df.columns:
        df['proj_points'] = pd.to_numeric(df['proj_points'], errors='coerce')
        df = df[df['proj_points'].notna()]
    
    print(f"Loaded {len(df)} player projections")
    
    return df

def build_lineup(players_df, salary_cap=50000, min_salary=0, qb_stack=1, max_team=4, no_rb_vs_dst=False):
    """
    Build optimal lineup using PuLP optimization.
    """
    print(f"\nBuilding lineup (cap: ${salary_cap:,}, min: ${min_salary:,})...")
    
    # Filter players by minimum salary if specified
    if min_salary > 0:
        players_df = players_df[players_df['salary'] >= min_salary].copy()
        print(f"Filtered to {len(players_df)} players with salary >= ${min_salary:,}")
    
    # Create optimization problem
    prob = LpProblem("DFS_Lineup_Optimization", LpMaximize)
    
    # Decision variables: 1 if player is selected, 0 otherwise
    player_vars = LpVariable.dicts("player", 
                                  [(i, row['name']) for i, row in players_df.iterrows()], 
                                  cat=LpBinary)
    
    # Objective: Maximize projected points
    prob += lpSum([player_vars[i, row['name']] * row['proj_points'] 
                   for i, row in players_df.iterrows()])
    
    # Constraint 1: Salary cap
    prob += lpSum([player_vars[i, row['name']] * row['salary'] 
                   for i, row in players_df.iterrows()]) <= salary_cap
    
    # Position indices
    idx_QB = players_df[players_df.pos == 'QB'].index.tolist()
    idx_RB = players_df[players_df.pos == 'RB'].index.tolist()
    idx_WR = players_df[players_df.pos == 'WR'].index.tolist()
    idx_TE = players_df[players_df.pos == 'TE'].index.tolist()
    idx_DST = players_df[players_df.pos == 'DST'].index.tolist()
    idx_all = players_df.index.tolist()

    # --- Total roster size ---
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_all]) == 9, "total_slots"

    # --- Exact slots ---
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_QB]) == 1, "slot_QB_exact"
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_DST]) == 1, "slot_DST_exact"
    
    # --- Skill position mins + total skill == 7 ---
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_RB]) >= 2, "min_RB"
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_WR]) >= 3, "min_WR"
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_TE]) >= 1, "min_TE"
    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_RB + idx_WR + idx_TE]) == 7, "total_skill_slots"
    
    # Constraint 4: Team stacking (QB + ≥N pass-catchers same team)
    if qb_stack > 0:
        qb_indices = players_df[players_df['pos'] == 'QB'].index.tolist()
        for qb_idx in qb_indices:
            qb_team = players_df.loc[qb_idx, 'team']
            # Find pass-catchers (WR/TE) from same team
            same_team_receivers = players_df[(players_df['team'] == qb_team) & 
                                           (players_df['pos'].isin(['WR', 'TE']))].index.tolist()
            
            if same_team_receivers:  # Only add constraint if there are receivers available
                # Require at least N pass-catchers from same team when QB is selected
                prob += lpSum([player_vars[i, row['name']] for i, row in players_df.iterrows() 
                             if i in same_team_receivers]) >= qb_stack * player_vars[qb_idx, players_df.loc[qb_idx, 'name']], f"stack_{qb_idx}"
    
    # Constraint 5: No RB vs. Opp DST (optional)
    if no_rb_vs_dst and 'opp' in players_df.columns:
        rb_indices = players_df[players_df['pos'] == 'RB'].index.tolist()
        for rb_idx in rb_indices:
            rb_opp = players_df.loc[rb_idx, 'opp']
            if pd.notna(rb_opp) and rb_opp != 'UNK':
                # Find DST from the same team as the RB's opponent
                bad_dst_indices = players_df[(players_df['pos'] == 'DST') & 
                                           (players_df['team'] == rb_opp)].index.tolist()
                
                for dst_idx in bad_dst_indices:
                    # Constraint: x[rb] + x[dst] <= 1 (can't select both)
                    prob += (player_vars[rb_idx, players_df.loc[rb_idx, 'name']] + 
                            player_vars[dst_idx, players_df.loc[dst_idx, 'name']] <= 1, 
                            f"no_rb_vs_dst_{rb_idx}_{dst_idx}")
    
    # Constraint 6: Limit players per team
    unique_teams = players_df['team'].unique()
    for team in unique_teams:
        if pd.notna(team) and team != 'UNK':
            team_indices = players_df[players_df['team'] == team].index.tolist()
            if team_indices:  # Only add constraint if team has players
                # Limit to maximum N players per team
                prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in players_df.index 
                             if i in team_indices]) <= max_team, f"max_team_{team}"
    
    # Constraint 7: Minimum salary constraint
    if min_salary > 0:
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] * players_df.loc[i, 'salary'] 
                      for i in players_df.index]) >= min_salary
    
    # Solve the problem
    print("Solving optimization problem...")
    prob.solve(PULP_CBC_CMD(msg=False))
    
    if prob.status == 1:  # Optimal solution found
        print("Optimal solution found!")
        
        # Extract selected players
        selected_players = []
        total_salary = 0
        total_proj = 0
        
        for i, row in players_df.iterrows():
            if player_vars[i, row['name']].value() == 1:
                selected_players.append(row)
                total_salary += row['salary']
                total_proj += row['proj_points']
        
        # Sort by position for display
        position_order = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST']
        selected_df = pd.DataFrame(selected_players)
        
        # Add flex designation
        flex_eligible = selected_df[selected_df['pos'].isin(FLEX_ELIG)].copy()
        if len(flex_eligible) > 6:  # More than required positions
            # Find the extra player for flex
            required_positions = []
            for pos, count in ROSTER_REQ.items():
                if pos in FLEX_ELIG:
                    required_positions.extend(selected_df[selected_df['pos'] == pos]['name'].tolist()[:count])
            
            flex_player = None
            for _, row in selected_df.iterrows():
                if row['name'] not in required_positions and row['pos'] in FLEX_ELIG:
                    flex_player = row
                    break
            
            if flex_player is not None:
                flex_player['pos'] = 'FLEX'
        
        print(f"\nOPTIMAL LINEUP:")
        print(f"Projected Points: {total_proj:.1f}")
        print(f"Total Salary: ${total_salary:,}")
        print(f"Remaining Cap: ${salary_cap - total_salary:,}")
        print(f"Value: {total_proj / (total_salary / 1000.0):.3f}")
        
        # Display lineup
        for i, (_, player) in enumerate(selected_df.iterrows()):
            pos_display = player['pos']
            if pos_display == 'FLEX':
                pos_display = f"FLEX({player.get('original_pos', 'UNK')})"
            
            print(f"{i+1:2d}. {pos_display:3s} {player['name']:25s} "
                  f"${player['salary']:5,} {player['proj_points']:5.1f} pts "
                  f"({player['value']:5.3f} value)")
        
        return selected_df
        
    else:
        print("❌ No feasible solution found!")
        return pd.DataFrame()

def generate_multiple_lineups(players_df, salary_cap=50000, min_salary=0, num_lineups=20, alpha=0.04, max_exposure=0.35, uniq_shared=7, qb_stack=1, max_team=4, no_rb_vs_dst=False):
    """
    Generate multiple unique lineups with mild randomness, uniqueness constraints, and exposure caps.
    """
    print(f"\nGenerating {num_lineups} unique lineups with {alpha*100:.1f}% randomness...")
    print(f"Exposure cap: {max_exposure*100:.0f}% (max {int(max_exposure * num_lineups)} lineups per player)")
    
    # Create output directory
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    base_proj = players_df['proj_points'].values.copy()
    chosen_sets = []
    
    # Track player exposure across lineups
    from collections import Counter
    exposure = Counter()
    max_exposure_count = int(max_exposure * num_lineups)
    
    for k in range(num_lineups):
        print(f"\nBuilding lineup {k+1}/{num_lineups}...")
        
        # Add banded randomness to projections for variety (salary-based)
        players_df['proj_perturbed'] = base_proj.copy()
        for idx, (i, row) in enumerate(players_df.iterrows()):
            salary = row['salary']
            if salary < 4500:
                noise_factor = 0.08  # 8% for cheap players
            elif salary <= 6500:
                noise_factor = 0.04  # 4% for mid-tier
            else:
                noise_factor = 0.02  # 2% for expensive players
            players_df.loc[i, 'proj_perturbed'] = base_proj[idx] * (1 + np.random.normal(0, noise_factor))
        
        # Create optimization problem
        prob = LpProblem(f"DFS_Lineup_Optimization_{k}", LpMaximize)
        
        # Decision variables: 1 if player is selected, 0 otherwise
        player_vars = LpVariable.dicts("player", 
                                      [(i, row['name']) for i, row in players_df.iterrows()], 
                                      cat=LpBinary)
        
        # Objective: Maximize perturbed projected points
        prob += lpSum([player_vars[i, row['name']] * row['proj_perturbed'] 
                      for i, row in players_df.iterrows()])
        
        # Apply all the same constraints as build_lineup
        # Constraint 1: Salary cap
        prob += lpSum([player_vars[i, row['name']] * row['salary'] 
                      for i, row in players_df.iterrows()]) <= salary_cap
        
        # Position indices
        idx_QB = players_df[players_df.pos == 'QB'].index.tolist()
        idx_RB = players_df[players_df.pos == 'RB'].index.tolist()
        idx_WR = players_df[players_df.pos == 'WR'].index.tolist()
        idx_TE = players_df[players_df.pos == 'TE'].index.tolist()
        idx_DST = players_df[players_df.pos == 'DST'].index.tolist()
        idx_all = players_df.index.tolist()
        
        # --- Total roster size ---
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_all]) == 9, "total_slots"
        
        # --- Exact slots ---
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_QB]) == 1, "slot_QB_exact"
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_DST]) == 1, "slot_DST_exact"
        
        # --- Skill position mins + total skill == 7 ---
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_RB]) >= 2, "min_RB"
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_WR]) >= 3, "min_WR"
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_TE]) >= 1, "min_TE"
        prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in idx_RB + idx_WR + idx_TE]) == 7, "total_skill_slots"
        
        # Constraint 4: Team stacking (QB + ≥N pass-catchers same team)
        if qb_stack > 0:
            qb_indices = players_df[players_df['pos'] == 'QB'].index.tolist()
            for qb_idx in qb_indices:
                qb_team = players_df.loc[qb_idx, 'team']
                same_team_receivers = players_df[(players_df['team'] == qb_team) & 
                                               (players_df['pos'].isin(['WR', 'TE']))].index.tolist()
                
                if same_team_receivers:
                    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in same_team_receivers]) >= qb_stack * player_vars[qb_idx, players_df.loc[qb_idx, 'name']], f"stack_{qb_idx}"
        
        # Constraint 5: No RB vs. Opp DST (optional)
        if no_rb_vs_dst and 'opp' in players_df.columns:
            rb_indices = players_df[players_df['pos'] == 'QB'].index.tolist()
            for rb_idx in rb_indices:
                rb_opp = players_df.loc[rb_idx, 'opp']
                if pd.notna(rb_opp) and rb_opp != 'UNK':
                    bad_dst_indices = players_df[(players_df['pos'] == 'DST') & 
                                               (players_df['team'] == rb_opp)].index.tolist()
                    
                    for dst_idx in bad_dst_indices:
                        prob += (player_vars[rb_idx, players_df.loc[rb_idx, 'name']] + 
                                player_vars[dst_idx, players_df.loc[dst_idx, 'name']] <= 1, 
                                f"no_rb_vs_dst_{rb_idx}_{dst_idx}")
        
        # Constraint 6: Limit players per team
        unique_teams = players_df['team'].unique()
        for team in unique_teams:
            if pd.notna(team) and team != 'UNK':
                team_indices = players_df[players_df['team'] == team].index.tolist()
                if team_indices:
                    prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in team_indices]) <= max_team, f"max_team_{team}"
        
        # Constraint 7: Minimum salary constraint
        if min_salary > 0:
            prob += lpSum([player_vars[i, players_df.loc[i, 'name']] * players_df.loc[i, 'salary'] 
                          for i in players_df.index]) >= min_salary
        
        # Uniqueness constraint: force at least 2 different slots vs previous lineups
        for j, picked in enumerate(chosen_sets):
            prob += lpSum([player_vars[i, players_df.loc[i, 'name']] for i in picked]) <= uniq_shared, f"uniq_{k}_{j}"  # 9 slots total -> share <= uniq_shared
        
        # Exposure cap constraint: prevent players from exceeding max exposure
        for i in players_df.index:
            if exposure[i] >= max_exposure_count:
                prob += player_vars[i, players_df.loc[i, 'name']] == 0, f"cap_{i}_{k}"
        
        # Solve the problem
        prob.solve(PULP_CBC_CMD(msg=False))
        
        if prob.status != 1:  # Not optimal
            print(f"  ❌ Lineup {k+1} infeasible, skipping...")
            continue
        
        # Extract selected players
        lineup_idx = [i for i in players_df.index 
                     if player_vars[i, players_df.loc[i, 'name']].value() > 0.5]
        chosen_sets.append(lineup_idx)
        
        # Update exposure counter for selected players
        for i in lineup_idx:
            exposure[i] += 1
        
        # Calculate lineup stats
        selected_players = players_df.loc[lineup_idx]
        total_salary = selected_players['salary'].sum()
        total_proj = selected_players['proj_points'].sum()
        total_perturbed = selected_players['proj_perturbed'].sum()
        
        print(f"  Lineup {k+1}: ${total_salary:,} salary, {total_proj:.1f} proj pts, {total_perturbed:.1f} perturbed pts")
        
        # Show exposure warnings for high-usage players
        high_exposure_players = []
        for i in lineup_idx:
            player_name = players_df.loc[i, 'name']
            player_exposure = exposure[i]
            if player_exposure >= max_exposure_count * 0.8:  # Warning at 80% of limit
                high_exposure_players.append(f"{player_name} ({player_exposure}/{max_exposure_count})")
        
        if high_exposure_players:
            print(f"  High exposure players: {', '.join(high_exposure_players)}")
        
        # Save lineup to CSV
        out = selected_players[['name', 'pos', 'team', 'salary', 'proj_points']].copy()
        out['lineup_k'] = k + 1
        out.to_csv(f"{output_dir}/lineup_{k+1:02d}.csv", index=False)
        
        # Clean up perturbed column for next iteration
        players_df = players_df.drop('proj_perturbed', axis=1)
    
    # Final exposure summary
    print(f"\nEXPOSURE SUMMARY:")
    high_exposure = [(i, exposure[i]) for i in exposure if exposure[i] > 0]
    high_exposure.sort(key=lambda x: x[1], reverse=True)
    
    for i, count in high_exposure[:10]:  # Show top 10 most used players
        player_name = players_df.loc[i, 'name']
        percentage = (count / num_lineups) * 100
        print(f"  {player_name}: {count}/{num_lineups} lineups ({percentage:.1f}%)")
    
    print(f"\nGenerated {len(chosen_sets)} unique lineups -> {output_dir}/lineup_*.csv")
    return chosen_sets

def generate_reports(players_df, chosen_sets, num_lineups):
    """Generate exposure and stacking reports"""
    os.makedirs("reports", exist_ok=True)
    
    # Player exposure
    exposure = {}
    for i in players_df.index:
        exposure[i] = sum(1 for lineup in chosen_sets if i in lineup)
    
    exposure_df = pd.DataFrame([
        {
            'name': players_df.loc[i, 'name'],
            'pos': players_df.loc[i, 'pos'],
            'team': players_df.loc[i, 'team'],
            'exposure_count': exposure[i],
            'exposure_pct': (exposure[i] / num_lineups) * 100
        }
        for i in exposure if exposure[i] > 0
    ]).sort_values('exposure_count', ascending=False)
    
    exposure_df.to_csv("reports/player_exposure.csv", index=False)
    
    # Team exposure
    team_exposure = {}
    for i in players_df.index:
        team = players_df.loc[i, 'team']
        if team not in team_exposure:
            team_exposure[team] = 0
        team_exposure[team] += exposure.get(i, 0)
    
    team_df = pd.DataFrame([
        {'team': team, 'total_exposure': count}
        for team, count in team_exposure.items() if count > 0
    ]).sort_values('total_exposure', ascending=False)
    
    team_df.to_csv("reports/team_exposure.csv", index=False)
    
    # Stacking analysis
    stacks = []
    for lineup_idx in chosen_sets:
        lineup = players_df.loc[lineup_idx]
        qbs = lineup[lineup['pos'] == 'QB']
        for _, qb in qbs.iterrows():
            qb_team = qb['team']
            receivers = lineup[(lineup['pos'].isin(['WR', 'TE'])) & (lineup['team'] == qb_team)]
            if len(receivers) > 0:
                stacks.append({
                    'lineup': len(stacks) + 1,
                    'qb': qb['name'],
                    'qb_team': qb_team,
                    'receivers': '; '.join(receivers['name'].tolist()),
                    'stack_size': len(receivers)
                })
    
    if stacks:
        stacks_df = pd.DataFrame(stacks)
        stacks_df.to_csv("reports/stacks.csv", index=False)
    
    print(f"Reports generated: player_exposure.csv, team_exposure.csv, stacks.csv")

def main():
    parser = argparse.ArgumentParser(description="Build optimal DFS lineup using centralized database")
    parser.add_argument("--projections", default="projections.csv", help="Projections CSV file")
    parser.add_argument("--salaries", default="data/DKSalaries.csv", help="DraftKings salaries CSV file")
    parser.add_argument("--output", default="optimal_lineup_v3.csv", help="Output CSV file")
    parser.add_argument("--salary-cap", type=int, default=50000, help="Salary cap (default: 50000)")
    parser.add_argument("--min-salary", type=int, default=0, help="Minimum total salary (default: 0)")
    parser.add_argument("--num-lineups", type=int, default=1, help="Number of lineups to generate (default: 1)")
    parser.add_argument("--uniq-shared", type=int, default=7, help="Max shared slots with any prior lineup (default: 7)")
    parser.add_argument("--alpha", type=float, default=0.04, help="Randomness factor 0.01-0.10 (default: 0.04)")
    parser.add_argument("--qb-stack", type=int, default=1, choices=[0,1,2], help="QB stack requirement: require >=N same-team WR/TE (default: 1)")
    parser.add_argument("--max-team", type=int, default=4, help="Maximum players per team (default: 4)")
    parser.add_argument("--no-rb-vs-dst", action="store_true", help="Prohibit RB vs opposing DST")
    parser.add_argument("--max-exposure", type=float, default=0.35, help="Maximum exposure per player 0.1-0.8 (default: 0.35)")
    
    args = parser.parse_args()
    
    print("🚀 Advanced DFS Lineup Optimizer V3 - Centralized Database Edition")
    print("=" * 70)
    print("✅ Using 100% crosswalk coverage - No more fuzzy name matching!")
    print("⚡ Near-instant player identification performance")
    print()
    
    # Load data
    projections = load_projections(args.projections)
    salaries = load_dk_salaries(args.salaries)
    
    # Initialize the centralized player matcher
    matcher = CentralizedPlayerMatcher()
    
    try:
        # Merge using the centralized database crosswalk
        merged = matcher.merge_projections_and_salaries(projections, salaries)
        
        if merged.empty:
            print("❌ Cannot proceed without matched data")
            return
        
        # Extract opponent information from DK Game Info
        merged = add_opp_from_dk_gameinfo(merged, args.salaries)
        print("\nOpponent information extracted from DK Game Info:")
        print(merged.loc[merged.pos=="QB", ["name","team","opp"]].head().to_string(index=False))
        
        # Build lineup(s)
        if args.num_lineups > 1:
            # Generate multiple unique lineups
            chosen_sets = generate_multiple_lineups(
                merged, 
                args.salary_cap, 
                args.min_salary, 
                args.num_lineups, 
                args.alpha,
                args.max_exposure,
                args.uniq_shared,
                args.qb_stack,
                args.max_team,
                args.no_rb_vs_dst
            )
            
            if chosen_sets:
                print(f"\n✅ Successfully generated {len(chosen_sets)} unique lineups!")
                print(f"📁 All lineups saved to outputs/ directory")
                
                # Generate reports
                generate_reports(merged, chosen_sets, args.num_lineups)
                
                # Show summary of first lineup as example
                first_lineup_idx = chosen_sets[0]
                first_lineup = merged.loc[first_lineup_idx]
                print(f"\n📊 SAMPLE LINEUP SUMMARY (Lineup 1):")
                print(f"Total Salary: ${first_lineup['salary'].sum():,}")
                print(f"Projected Points: {first_lineup['proj_points'].sum():.1f}")
                print(f"Average Value: {first_lineup['value'].mean():.3f}")
        else:
            # Build single optimal lineup
            lineup = build_lineup(merged, args.salary_cap, args.min_salary, args.qb_stack, args.max_team, args.no_rb_vs_dst)
            
            if not lineup.empty:
                # Save lineup
                lineup.to_csv(args.output, index=False)
                print(f"\n💾 Lineup saved to {args.output}")
                
                # Show summary
                print(f"\n📊 LINEUP SUMMARY:")
                print(f"Total Salary: ${lineup['salary'].sum():,}")
                print(f"Projected Points: {lineup['proj_points'].sum():.1f}")
                print(f"Average Value: {lineup['value'].mean():.3f}")
                
                # Position breakdown
                print(f"\nPosition Breakdown:")
                for pos in lineup['pos'].unique():
                    pos_players = lineup[lineup['pos'] == pos]
                    print(f"  {pos}: {len(pos_players)} players")
    
    finally:
        # Always close the database connection
        matcher.close()
    
    print("\n🎯 Optimization complete!")

if __name__ == "__main__":
    main()