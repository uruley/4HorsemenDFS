#!/usr/bin/env python3
"""
Enhanced Name Matcher V5 - Multi-Factor Matching with Position & Team
This version uses position, team, and name for significantly better accuracy
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import logging
from centralized_player_database import CentralizedPlayerDatabase
from fuzzywuzzy import fuzz
import jellyfish

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedNameMatcherV5:
    """
    Enhanced name matching system that uses position, team, and name
    for significantly better matching accuracy
    """
    
    def __init__(self, db_path: str = "data/player_database.db", debug: bool = False):
        self.debug = debug
        self.db = CentralizedPlayerDatabase(db_path)
        self.matching_stats = {
            'exact_matches': 0,
            'database_matches': 0,
            'position_team_matches': 0,
            'fuzzy_matches': 0,
            'unmatched': 0,
            'ambiguous': 0
        }
        
        # Position mapping for validation
        self.position_mapping = {
            'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'K': 'K', 'DST': 'DST',
            'DEF': 'DST', 'DEFENSE': 'DST', 'DEF/ST': 'DST'
        }
        
        # Team abbreviation mapping
        self.team_mapping = {
            'KC': 'KC', 'SF': 'SF', 'MIA': 'MIA', 'CIN': 'CIN', 'ATL': 'ATL', 'DET': 'DET',
            'LAR': 'LAR', 'HOU': 'HOU', 'BUF': 'BUF', 'DAL': 'DAL', 'PHI': 'PHI', 'GB': 'GB',
            'NE': 'NE', 'TB': 'TB', 'LV': 'LV', 'LAC': 'LAC', 'ARI': 'ARI', 'CHI': 'CHI',
            'CLE': 'CLE', 'DEN': 'DEN', 'IND': 'IND', 'JAX': 'JAX', 'MIN': 'MIN', 'NO': 'NO',
            'NYG': 'NYG', 'NYJ': 'NYJ', 'PIT': 'PIT', 'SEA': 'SEA', 'TEN': 'TEN', 'WAS': 'WAS'
        }
        
        # NEW: Team change mapping for known trades/roster moves
        # Format: 'Player Name': {'old_team': 'NFL_API_team', 'new_team': 'DraftKings_team'}
        self.team_changes = {
            'Stefon Diggs': {'old_team': 'HOU', 'new_team': 'NE'},
            'Darren Waller': {'old_team': 'NYG', 'new_team': 'MIA'},
            'Cooper Kupp': {'old_team': 'LAR', 'new_team': 'SEA'},
            'Russell Wilson': {'old_team': 'DEN', 'new_team': 'NYG'},
            'Davante Adams': {'old_team': 'LV', 'new_team': 'LAR'},
            'Joe Mixon': {'old_team': 'CIN', 'new_team': 'HOU'},
            'DK Metcalf': {'old_team': 'SEA', 'new_team': 'PIT'},
            'Matthew Stafford': {'old_team': 'LAR', 'new_team': 'LAR'},  # Same team but different abbreviation
            'Nick Chubb': {'old_team': 'CLE', 'new_team': 'HOU'},
            'Deebo Samuel': {'old_team': 'SF', 'new_team': 'WAS'},
            'Justin Fields': {'old_team': 'CHI', 'new_team': 'NYJ'},
            'Aaron Rodgers': {'old_team': 'NYJ', 'new_team': 'PIT'},
            'Sam Darnold': {'old_team': 'SF', 'new_team': 'SEA'},
            'Geno Smith': {'old_team': 'SEA', 'new_team': 'LV'},
            'Rico Dowdle': {'old_team': 'DAL', 'new_team': 'CAR'},
            'Raheem Mostert': {'old_team': 'MIA', 'new_team': 'LV'},
            'Cam Akers': {'old_team': 'LAR', 'new_team': 'NO'},
            'J.K. Dobbins': {'old_team': 'BAL', 'new_team': 'DEN'},
            'Joe Flacco': {'old_team': 'CLE', 'new_team': 'IND'},
            'Kenny Pickett': {'old_team': 'PIT', 'new_team': 'CLE'},
            'Desmond Ridder': {'old_team': 'ATL', 'new_team': 'CIN'},
            'Payton Thorne': {'old_team': 'AUB', 'new_team': 'CIN'},
            'Ahmani Marshall': {'old_team': 'CLE', 'new_team': 'CLE'},  # Same team
            'Gary Brightwell': {'old_team': 'NYG', 'new_team': 'CIN'},
            'Kendall Milton': {'old_team': 'UGA', 'new_team': 'CIN'},
            'Quali Conley': {'old_team': 'CLE', 'new_team': 'CIN'},
            'Sam Ehlinger': {'old_team': 'IND', 'new_team': 'DEN'},
            'Kalel Mullings': {'old_team': 'MICH', 'new_team': 'TEN'},
            'Jordan Mims': {'old_team': 'FRES', 'new_team': 'TEN'},
            'Kurtis Rourke': {'old_team': 'OHIO', 'new_team': 'SF'},
            'Tanner Mordecai': {'old_team': 'WIS', 'new_team': 'SF'},
            'Damien Martinez': {'old_team': 'ORST', 'new_team': 'SEA'},
            'Jacardia Wright': {'old_team': 'KSU', 'new_team': 'SEA'},
            'Robbie Ouzts': {'old_team': 'CLEM', 'new_team': 'SEA'},
            'Kyle Juszczyk': {'old_team': 'SF', 'new_team': 'SF'},  # Same team
            'Brady Russell': {'old_team': 'COL', 'new_team': 'SEA'},
            'Sean Clifford': {'old_team': 'PSU', 'new_team': 'GB'},
            'Taylor Elgersma': {'old_team': 'RICH', 'new_team': 'GB'},
            'Jalen White': {'old_team': 'GASO', 'new_team': 'GB'},
            'Kye Robichaux': {'old_team': 'WAKE', 'new_team': 'DET'},
            'Jabari Small': {'old_team': 'TENN', 'new_team': 'DET'},
            'Stetson Bennett': {'old_team': 'UGA', 'new_team': 'LAR'},
            'Dresser Winn': {'old_team': 'UTST', 'new_team': 'LAR'},
            'Graham Mertz': {'old_team': 'WIS', 'new_team': 'HOU'},
            'Kedon Slovis': {'old_team': 'PITT', 'new_team': 'HOU'},
            'Jordan Waters': {'old_team': 'DUKE', 'new_team': 'LAR'},
            # ADDITIONAL COLLEGE TO NFL TRANSITIONS
            'Braelon Allen': {'old_team': 'WIS', 'new_team': 'NYJ'},
            'Tyrone Tracy Jr.': {'old_team': 'PURDUE', 'new_team': 'NYG'},
            'Ashton Jeanty': {'old_team': 'BOISE', 'new_team': 'LV'},
            'Jayden Daniels': {'old_team': 'LSU', 'new_team': 'WAS'},
            'Malik Nabers': {'old_team': 'LSU', 'new_team': 'NYG'},
            'Brian Thomas Jr.': {'old_team': 'LSU', 'new_team': 'JAX'},
            'Bucky Irving': {'old_team': 'ORE', 'new_team': 'TB'},
            'Drake Maye': {'old_team': 'UNC', 'new_team': 'NE'},
            'TreVeyon Henderson': {'old_team': 'OSU', 'new_team': 'NE'},
            'Marvin Harrison Jr.': {'old_team': 'OSU', 'new_team': 'ARI'},
            'Brock Bowers': {'old_team': 'UGA', 'new_team': 'LV'},
            'Xavier Legette': {'old_team': 'SCAR', 'new_team': 'CAR'},
            'Ricky Pearsall': {'old_team': 'FLA', 'new_team': 'SF'},
            'Luke McCaffrey': {'old_team': 'RICE', 'new_team': 'WAS'},
            'Troy Franklin': {'old_team': 'ORE', 'new_team': 'DEN'},
            'Jacob Cowing': {'old_team': 'ARIZ', 'new_team': 'SF'},
            'Adonai Mitchell': {'old_team': 'TEX', 'new_team': 'IND'},
            'Xavier Restrepo': {'old_team': 'MIAMI', 'new_team': 'TEN'},
            'Jordan Watkins': {'old_team': 'OLEMISS', 'new_team': 'SF'},
            'Savion Williams': {'old_team': 'TCU', 'new_team': 'GB'},
            'Malik Washington': {'old_team': 'UVA', 'new_team': 'MIA'},
            'Jermaine Burton': {'old_team': 'ALA', 'new_team': 'CIN'},
            'Ja\'Lynn Polk': {'old_team': 'WASH', 'new_team': 'NE'},
            'Javon Baker': {'old_team': 'UCF', 'new_team': 'NE'},
            'Roman Wilson': {'old_team': 'MICH', 'new_team': 'PIT'},
            'Malachi Corley': {'old_team': 'WKU', 'new_team': 'NYJ'},
            'Trey Palmer': {'old_team': 'NEB', 'new_team': 'TB'},
            'Tank Dell': {'old_team': 'HOU', 'new_team': 'HOU'},
            'Jalin Hyatt': {'old_team': 'TENN', 'new_team': 'NYG'},
            'Rashod Bateman': {'old_team': 'MINN', 'new_team': 'BAL'},
            'Kadarius Toney': {'old_team': 'FLA', 'new_team': 'KC'},
            'Rondale Moore': {'old_team': 'PURDUE', 'new_team': 'ATL'},
            'Amon-Ra St. Brown': {'old_team': 'USC', 'new_team': 'DET'},
            'DeVonta Smith': {'old_team': 'ALA', 'new_team': 'PHI'},
            'Jaylen Waddle': {'old_team': 'ALA', 'new_team': 'MIA'},
            'Jerry Jeudy': {'old_team': 'ALA', 'new_team': 'CLE'},
            'Henry Ruggs III': {'old_team': 'ALA', 'new_team': 'LV'},
            'CeeDee Lamb': {'old_team': 'OKLA', 'new_team': 'DAL'},
            'Justin Jefferson': {'old_team': 'LSU', 'new_team': 'MIN'},
            'Tee Higgins': {'old_team': 'CLEM', 'new_team': 'CIN'},
            'Chase Claypool': {'old_team': 'ND', 'new_team': 'BUF'},
            'Denzel Mims': {'old_team': 'BAYLOR', 'new_team': 'PIT'},
            'Laviska Shenault Jr.': {'old_team': 'COLO', 'new_team': 'CAR'},
            'Bryan Edwards': {'old_team': 'SCAR', 'new_team': 'NO'},
            'Van Jefferson': {'old_team': 'FLA', 'new_team': 'TEN'},
            'Darnell Mooney': {'old_team': 'TULANE', 'new_team': 'ATL'},
            'Gabriel Davis': {'old_team': 'UCF', 'new_team': 'BUF'},
            'Chase Claypool': {'old_team': 'ND', 'new_team': 'BUF'},
            'Donovan Peoples-Jones': {'old_team': 'MICH', 'new_team': 'NO'},
            'Quintez Cephus': {'old_team': 'WIS', 'new_team': 'HOU'},
            'Isaiah Neyor': {'old_team': 'WYO', 'new_team': 'GB'},
            'Phillip Dorsett II': {'old_team': 'MIAMI', 'new_team': 'LV'},
            'Seth Williams': {'old_team': 'AUB', 'new_team': 'LV'},
            'Ja\'Corey Brooks': {'old_team': 'ALA', 'new_team': 'NE'},
            'Efton Chism III': {'old_team': 'ARKST', 'new_team': 'NE'},
            'John Jiles': {'old_team': 'WESTFLA', 'new_team': 'NE'},
            'DeMeer Blankumsee': {'old_team': 'TEMPLE', 'new_team': 'NE'},
            'Jeremiah Webb': {'old_team': 'MARYLAND', 'new_team': 'NE'},
            'Tommy Mellott': {'old_team': 'MONTST', 'new_team': 'LV'},
            'Alex Bachman': {'old_team': 'WAKE', 'new_team': 'LV'},
            'Collin Johnson': {'old_team': 'TEX', 'new_team': 'LV'},
            'Kyle Philips': {'old_team': 'UCLA', 'new_team': 'LV'},
            'Shedrick Jackson': {'old_team': 'AUB', 'new_team': 'LV'},
            'Ketron Jackson Jr.': {'old_team': 'ARK', 'new_team': 'LV'},
            'Michael Mayer': {'old_team': 'ND', 'new_team': 'LV'},
            'Scotty Miller': {'old_team': 'BOWLING', 'new_team': 'PIT'},
            'Ben Skowronek': {'old_team': 'ND', 'new_team': 'PIT'},
            'Brandon Johnson': {'old_team': 'UCF', 'new_team': 'PIT'},
            'Lance McCutcheon': {'old_team': 'MONTST', 'new_team': 'PIT'},
            'Roc Taylor': {'old_team': 'MEM', 'new_team': 'PIT'},
            'Ke\'Shawn Williams': {'old_team': 'WAKE', 'new_team': 'PIT'},
            'Montana Lemonious-Craig': {'old_team': 'COLO', 'new_team': 'PIT'},
            'Arian Smith': {'old_team': 'UGA', 'new_team': 'NYJ'},
            'Tyler Johnson': {'old_team': 'MINN', 'new_team': 'NYJ'},
            'Xavier Gipson': {'old_team': 'STEPHFA', 'new_team': 'NYJ'},
            'Irvin Charles': {'old_team': 'PENNST', 'new_team': 'NYJ'},
            'Brandon Smith': {'old_team': 'PENNST', 'new_team': 'NYJ'},
            'Ontaria Wilson': {'old_team': 'FSU', 'new_team': 'NYJ'},
            'Dymere Miller': {'old_team': 'MONMOUTH', 'new_team': 'NYJ'},
            'Jamaal Pritchett': {'old_team': 'COASTAL', 'new_team': 'NYJ'},
            'Quentin Skinner': {'old_team': 'SOUTHALA', 'new_team': 'NYJ'},
            'Tez Johnson': {'old_team': 'ORE', 'new_team': 'TB'},
            'Ryan Miller': {'old_team': 'FURMAN', 'new_team': 'TB'},
            'Rakim Jarrett': {'old_team': 'MARYLAND', 'new_team': 'TB'},
            'Kameron Johnson': {'old_team': 'NCAT', 'new_team': 'TB'},
            'Dennis Houston': {'old_team': 'WESTERN', 'new_team': 'TB'},
            'Garrett Greene': {'old_team': 'WVU', 'new_team': 'TB'},
            'Casey Washington': {'old_team': 'ILL', 'new_team': 'ATL'},
            'Jamal Agnew': {'old_team': 'RICHMOND', 'new_team': 'ATL'},
            'Chris Blair': {'old_team': 'LIBERTY', 'new_team': 'ATL'},
            'Dylan Drummond': {'old_team': 'EMU', 'new_team': 'ATL'},
            'Jesse Matthews': {'old_team': 'SDSU', 'new_team': 'ATL'},
            'David Sills V': {'old_team': 'WVU', 'new_team': 'ATL'},
            'Nick Nash': {'old_team': 'SJSU', 'new_team': 'ATL'},
            'Makai Polk': {'old_team': 'MISSST', 'new_team': 'ATL'},
            'Quincy Skinner Jr.': {'old_team': 'VANDY', 'new_team': 'ATL'},
            'Dee Eskridge': {'old_team': 'WMU', 'new_team': 'MIA'},
            'Erik Ezukanma': {'old_team': 'TTU', 'new_team': 'MIA'},
            'Tahj Washington': {'old_team': 'USC', 'new_team': 'MIA'},
            'Tarik Black': {'old_team': 'MICH', 'new_team': 'MIA'},
            'Theo Wease Jr.': {'old_team': 'OKLA', 'new_team': 'MIA'},
            'Andrew Armstrong': {'old_team': 'ARK', 'new_team': 'MIA'},
            'Monaray Baldwin': {'old_team': 'BAYLOR', 'new_team': 'MIA'},
            'A.J. Henning': {'old_team': 'MICH', 'new_team': 'MIA'},
            'Ashton Dulin': {'old_team': 'MALONE', 'new_team': 'IND'},
            'Anthony Gould': {'old_team': 'OREST', 'new_team': 'IND'},
            'Laquon Treadwell': {'old_team': 'OLEMISS', 'new_team': 'IND'},
            'D.J. Montgomery': {'old_team': 'AUSTINPEAY', 'new_team': 'IND'},
            'Ajou Ajou': {'old_team': 'CLEM', 'new_team': 'IND'},
            'Blayne Taylor': {'old_team': 'LIBERTY', 'new_team': 'IND'},
            'Landon Parker': {'old_team': 'JACKSONST', 'new_team': 'IND'},
            'Coleman Owen': {'old_team': 'NAU', 'new_team': 'IND'},
            'Tyler Kahmann': {'old_team': 'WISWHITEWATER', 'new_team': 'IND'},
            'Cedrick Wilson Jr.': {'old_team': 'BOISE', 'new_team': 'NO'},
            'Kevin Austin Jr.': {'old_team': 'ND', 'new_team': 'NO'},
            'Simi Fehoko': {'old_team': 'STAN', 'new_team': 'ARI'},
            'Xavier Weaver': {'old_team': 'COLO', 'new_team': 'ARI'},
            'Andre Baccellia': {'old_team': 'WASH', 'new_team': 'ARI'},
            'Tejhaun Palmer': {'old_team': 'UAB', 'new_team': 'ARI'},
            'Quez Watkins': {'old_team': 'SOUTHMISS', 'new_team': 'ARI'},
            'Trishton Jackson': {'old_team': 'SYR', 'new_team': 'ARI'},
            'Bryson Green': {'old_team': 'OKST', 'new_team': 'ARI'},
            'Dante Pettis': {'old_team': 'WASH', 'new_team': 'NO'},
            'Mason Tipton': {'old_team': 'YALE', 'new_team': 'NO'},
            'Moochie Dixon': {'old_team': 'TEXASST', 'new_team': 'NO'},
            'Chris Tyree': {'old_team': 'ND', 'new_team': 'NO'},
            'Tay Martin': {'old_team': 'OKST', 'new_team': 'WAS'},
            'K.J. Osborn': {'old_team': 'MIAMI', 'new_team': 'WAS'},
            'Chris Moore': {'old_team': 'CINCY', 'new_team': 'WAS'},
            'Mike Strachan': {'old_team': 'CHARLESTON', 'new_team': 'WAS'},
            'Ja\'Corey Brooks': {'old_team': 'ALA', 'new_team': 'WAS'},
            'Jacoby Jones': {'old_team': 'LANE', 'new_team': 'WAS'},
            'Lil\'Jordan Humphrey': {'old_team': 'TEX', 'new_team': 'NYG'},
            'Zach Pascal': {'old_team': 'ODU', 'new_team': 'NYG'},
            'Ihmir Smith-Marsette': {'old_team': 'IOWA', 'new_team': 'NYG'},
            'Bryce Ford-Wheaton': {'old_team': 'WVU', 'new_team': 'NYG'},
            'Montrell Washington': {'old_team': 'SAMFORD', 'new_team': 'NYG'},
            'Da\'Quan Felton': {'old_team': 'NORFOLKST', 'new_team': 'NYG'},
            'Beaux Collins': {'old_team': 'CLEM', 'new_team': 'NYG'},
            'Juice Wells Jr.': {'old_team': 'SCAR', 'new_team': 'NYG'},
            'Jordan Bly': {'old_team': 'APPST', 'new_team': 'NYG'},
            'Dalen Cambre': {'old_team': 'ULL', 'new_team': 'NYG'},
            'Theo Johnson': {'old_team': 'PENNST', 'new_team': 'NYG'},
            'David Moore': {'old_team': 'MEM', 'new_team': 'CAR'},
            'Joshua Cephus': {'old_team': 'UTSA', 'new_team': 'JAX'},
            'Austin Trammell': {'old_team': 'RICE', 'new_team': 'JAX'},
            'Trenton Irwin': {'old_team': 'STAN', 'new_team': 'JAX'},
            'Louis Rees-Zammit': {'old_team': 'GLOUCESTER', 'new_team': 'JAX'},
            'Chandler Brayboy': {'old_team': 'HOWARD', 'new_team': 'JAX'},
            'Eli Pancol': {'old_team': 'NORTHWESTERN', 'new_team': 'JAX'},
            'Cam Camper': {'old_team': 'IND', 'new_team': 'JAX'},
            'Dorian Singer': {'old_team': 'USC', 'new_team': 'JAX'},
            'Darius Lassiter': {'old_team': 'EMU', 'new_team': 'JAX'},
            'J.J. Jones': {'old_team': 'WESTERN', 'new_team': 'JAX'},
            'Jimmy Horn Jr.': {'old_team': 'USF', 'new_team': 'CAR'},
            'Dan Chisena': {'old_team': 'PENNST', 'new_team': 'CAR'},
            'Brycen Tremayne': {'old_team': 'STAN', 'new_team': 'CAR'},
            'T.J. Luther': {'old_team': 'GARDNER', 'new_team': 'CAR'},
            'Kobe Hudson': {'old_team': 'UCF', 'new_team': 'CAR'},
            'Jacolby George': {'old_team': 'MIAMI', 'new_team': 'CAR'},
            'David Bell': {'old_team': 'PURDUE', 'new_team': 'CLE'},
            'Jamari Thrash': {'old_team': 'LOU', 'new_team': 'CLE'},
            'Michael Woods II': {'old_team': 'OKLA', 'new_team': 'CLE'},
            'DeAndre Carter': {'old_team': 'SACST', 'new_team': 'CLE'},
            'Kaden Davis': {'old_team': 'WICHITAST', 'new_team': 'CLE'},
            'Luke Floriea': {'old_team': 'KENTST', 'new_team': 'CLE'},
            'Gage Larvadain': {'old_team': 'SOUTHEAST', 'new_team': 'CLE'},
            'Kisean Johnson': {'old_team': 'BALLST', 'new_team': 'CLE'},
            'Cade McDonald': {'old_team': 'NORTHERN', 'new_team': 'CLE'},
            'Charlie Jones': {'old_team': 'IOWA', 'new_team': 'CIN'},
            'Kendric Pryor': {'old_team': 'WIS', 'new_team': 'CIN'},
            'Isaiah Williams': {'old_team': 'ILL', 'new_team': 'CIN'},
            'Cole Burgess': {'old_team': 'BUFFALO', 'new_team': 'CIN'},
            'Mitchell Tinsley': {'old_team': 'PENNST', 'new_team': 'CIN'},
            'Rashod Owens': {'old_team': 'OKST', 'new_team': 'CIN'},
            'Jordan Moore': {'old_team': 'DUKE', 'new_team': 'CIN'},
            'Jamoi Mayes': {'old_team': 'TROY', 'new_team': 'CIN'},
            'Chimere Dike': {'old_team': 'WIS', 'new_team': 'TEN'},
            'Mason Kinsey': {'old_team': 'BERRY', 'new_team': 'TEN'},
            'James Proche II': {'old_team': 'SMU', 'new_team': 'TEN'},
            'Jha\'Quan Jackson': {'old_team': 'TULANE', 'new_team': 'TEN'},
            'Colton Dowell': {'old_team': 'UTMARTIN', 'new_team': 'TEN'},
            'Bryce Oliver': {'old_team': 'YOUNGSTOWN', 'new_team': 'TEN'},
            'TJ Sheffield': {'old_team': 'PURDUE', 'new_team': 'TEN'},
            'Trent Sherfield Sr.': {'old_team': 'VANDY', 'new_team': 'DEN'},
            'A.T. Perry': {'old_team': 'WAKE', 'new_team': 'DEN'},
            'Michael Bandy': {'old_team': 'USD', 'new_team': 'DEN'},
            'Joaquin Davis': {'old_team': 'UTEP', 'new_team': 'DEN'},
            'Courtney Jackson': {'old_team': 'UMASS', 'new_team': 'DEN'},
            'Jerjuan Newton': {'old_team': 'PITT', 'new_team': 'DEN'},
            'Kyrese Rowan': {'old_team': 'WESTERN', 'new_team': 'DEN'},
            'Equanimeous St. Brown': {'old_team': 'ND', 'new_team': 'SF'},
            'John Rhys Plumlee': {'old_team': 'UCF', 'new_team': 'SEA'},
            'Tory Horton': {'old_team': 'COLOST', 'new_team': 'SEA'},
            'Jake Bobo': {'old_team': 'UCLA', 'new_team': 'SEA'},
            'Ricky White III': {'old_team': 'UNLV', 'new_team': 'SEA'},
            'Steven Sims': {'old_team': 'KU', 'new_team': 'SEA'},
            'Dareke Young': {'old_team': 'LENOIR', 'new_team': 'SEA'},
            'Cody White': {'old_team': 'MICHST', 'new_team': 'SEA'},
            'Tyrone Broden': {'old_team': 'BOWLING', 'new_team': 'SEA'},
            'Montorie Foster Jr.': {'old_team': 'ABILENE', 'new_team': 'SEA'},
            'Junior Bergen': {'old_team': 'MONTANA', 'new_team': 'SF'},
            'Russell Gage Jr.': {'old_team': 'LSU', 'new_team': 'SF'},
            'Terique Owens': {'old_team': 'MISSST', 'new_team': 'SF'},
            'Isaiah Hodgins': {'old_team': 'OREST', 'new_team': 'SF'},
            'Malik Knowles': {'old_team': 'KSU', 'new_team': 'SF'},
            'Trent Taylor': {'old_team': 'LA', 'new_team': 'SF'},
            'Will Sheppard': {'old_team': 'VANDY', 'new_team': 'GB'},
            'Malik Heath': {'old_team': 'OLEMISS', 'new_team': 'GB'},
            'Bo Melton': {'old_team': 'RUTG', 'new_team': 'GB'},
            'Mecole Hardman': {'old_team': 'UGA', 'new_team': 'GB'},
            'Julian Hicks': {'old_team': 'CAL', 'new_team': 'GB'},
            'Cornelius Johnson': {'old_team': 'MICH', 'new_team': 'GB'},
            'Sam Brown Jr.': {'old_team': 'WESTERN', 'new_team': 'GB'},
            'Dominic Lovett': {'old_team': 'MIZZ', 'new_team': 'DET'},
            'Tom Kennedy': {'old_team': 'BRYANT', 'new_team': 'DET'},
            'Ronnie Bell': {'old_team': 'MICH', 'new_team': 'DET'},
            'Malik Taylor': {'old_team': 'MARQUETTE', 'new_team': 'DET'},
            'Jackson Meeks': {'old_team': 'UGA', 'new_team': 'DET'},
            'Jakobie Keeney-James': {'old_team': 'NORTHERN', 'new_team': 'DET'},
            'Xavier Hutchinson': {'old_team': 'IOWAST', 'new_team': 'HOU'},
            'Konata Mumpfield': {'old_team': 'PITT', 'new_team': 'LAR'},
            'Xavier Smith': {'old_team': 'FAMU', 'new_team': 'LAR'},
            'Britain Covey': {'old_team': 'UTAH', 'new_team': 'LAR'},
            'Tru Edwards': {'old_team': 'ARKST', 'new_team': 'LAR'},
            'Brennan Presley': {'old_team': 'OKST', 'new_team': 'LAR'},
            'Mario Williams': {'old_team': 'USC', 'new_team': 'LAR'},
            'Drake Stoops': {'old_team': 'OKLA', 'new_team': 'LAR'},
            'Justin Watson': {'old_team': 'PENN', 'new_team': 'HOU'},
            'Braxton Berrios': {'old_team': 'MIAMI', 'new_team': 'HOU'},
            'Jared Wayne': {'old_team': 'PITT', 'new_team': 'HOU'},
            'Johnny Johnson III': {'old_team': 'ORE', 'new_team': 'HOU'},
            'Xavier Johnson': {'old_team': 'ARIZ', 'new_team': 'HOU'},
            'Daniel Jackson': {'old_team': 'NMST', 'new_team': 'HOU'},
            'Austin Hooper': {'old_team': 'STAN', 'new_team': 'NE'},
            'Ja\'Tavion Sanders': {'old_team': 'TEX', 'new_team': 'CAR'},
            'Adam Trautman': {'old_team': 'DAYTON', 'new_team': 'DEN'},
            'AJ Barner': {'old_team': 'MICH', 'new_team': 'SEA'},
            'Luke Musgrave': {'old_team': 'OREST', 'new_team': 'GB'},
            'Julian Hill': {'old_team': 'MIAMI', 'new_team': 'MIA'},
            'Foster Moreau': {'old_team': 'LSU', 'new_team': 'NO'},
            'Elijah Arroyo': {'old_team': 'MIAMI', 'new_team': 'SEA'},
            'Payne Durham': {'old_team': 'PURDUE', 'new_team': 'TB'},
            'Gunnar Helm': {'old_team': 'UTAH', 'new_team': 'TEN'},
            'Cade Stover': {'old_team': 'OSU', 'new_team': 'HOU'},
            'Mason Pline': {'old_team': 'FERRIS', 'new_team': 'NO'},
            'Albert Okwuegbunam Jr.': {'old_team': 'MIZZ', 'new_team': 'LV'},
            'Jaheim Bell': {'old_team': 'FSU', 'new_team': 'NE'},
            'Jack Westover': {'old_team': 'WASH', 'new_team': 'NE'},
            'CJ Dippre': {'old_team': 'ALA', 'new_team': 'NE'},
            'Gee Scott Jr.': {'old_team': 'OSU', 'new_team': 'NE'},
            'Ian Thomas': {'old_team': 'IND', 'new_team': 'LV'},
            'Justin Shorter': {'old_team': 'FLA', 'new_team': 'LV'},
            'Qadir Ismail': {'old_team': 'SMU', 'new_team': 'LV'},
            'Carter Runyon': {'old_team': 'MARSHALL', 'new_team': 'LV'},
            'Pat Conroy': {'old_team': 'STAN', 'new_team': 'LV'},
            'Stone Smartt': {'old_team': 'OLD', 'new_team': 'NYJ'},
            'Darnell Washington': {'old_team': 'UGA', 'new_team': 'PIT'},
            'Connor Heyward': {'old_team': 'MICHST', 'new_team': 'PIT'},
            'JJ Galbreath': {'old_team': 'OREST', 'new_team': 'PIT'},
            'Donald Parham Jr.': {'old_team': 'STETSON', 'new_team': 'PIT'},
            'DJ Thomas-Jones': {'old_team': 'BUFFALO', 'new_team': 'PIT'},
            'Jeremy Ruckert': {'old_team': 'OSU', 'new_team': 'NYJ'},
            'Zack Kuntz': {'old_team': 'OLD', 'new_team': 'NYJ'},
            'Neal Johnson': {'old_team': 'LA', 'new_team': 'NYJ'},
            'Devin Culp': {'old_team': 'WASH', 'new_team': 'TB'},
            'Ko Kieft': {'old_team': 'MINN', 'new_team': 'TB'},
            'Tanner Taula': {'old_team': 'WASH', 'new_team': 'TB'},
            'Evan Deckers': {'old_team': 'NORTHERN', 'new_team': 'TB'},
            'Charlie Woerner': {'old_team': 'UGA', 'new_team': 'ATL'},
            'Feleipe Franks': {'old_team': 'FLA', 'new_team': 'ATL'},
            'Teagan Quitoriano': {'old_team': 'OREST', 'new_team': 'ATL'},
            'Nikola Kalinic': {'old_team': 'CAL', 'new_team': 'ATL'},
            'Joshua Simon': {'old_team': 'WESTERN', 'new_team': 'ATL'},
            'Pharaoh Brown': {'old_team': 'ORE', 'new_team': 'MIA'},
            'Tanner Conner': {'old_team': 'IDAHOST', 'new_team': 'MIA'},
            'Hayden Rucci': {'old_team': 'WIS', 'new_team': 'MIA'},
            'Jalin Conyers': {'old_team': 'ARIZST', 'new_team': 'MIA'},
            'Mo Alie-Cox': {'old_team': 'VCU', 'new_team': 'IND'},
            'Drew Ogletree': {'old_team': 'YOUNGSTOWN', 'new_team': 'IND'},
            'Jelani Woods': {'old_team': 'OKLA', 'new_team': 'IND'},
            'Will Mallory': {'old_team': 'MIAMI', 'new_team': 'IND'},
            'Sean McKeon': {'old_team': 'MICH', 'new_team': 'IND'},
            'Maximilian Mang': {'old_team': 'WIS', 'new_team': 'IND'},
            'Tip Reiman': {'old_team': 'ILL', 'new_team': 'ARI'},
            'Elijah Higgins': {'old_team': 'STAN', 'new_team': 'ARI'},
            'Josiah Deguara': {'old_team': 'CINCY', 'new_team': 'ARI'},
            'Travis Vokolek': {'old_team': 'NEB', 'new_team': 'ARI'},
            'Oscar Cardenas': {'old_team': 'UTSA', 'new_team': 'ARI'},
            'Jack Stoll': {'old_team': 'NEB', 'new_team': 'NO'},
            'Moliki Matavao': {'old_team': 'ORE', 'new_team': 'NO'},
            'Michael Jacobson': {'old_team': 'IOWAST', 'new_team': 'NO'},
            'Seth Green': {'old_team': 'MINN', 'new_team': 'NO'},
            'Treyton Welch': {'old_team': 'WYO', 'new_team': 'NO'},
            'Zach Wood': {'old_team': 'SMU', 'new_team': 'NO'},
            'John Bates': {'old_team': 'OREST', 'new_team': 'WAS'},
            'Ben Sinnott': {'old_team': 'KSU', 'new_team': 'WAS'},
            'Colson Yankoff': {'old_team': 'UCLA', 'new_team': 'WAS'},
            'Tyree Jackson': {'old_team': 'BUFFALO', 'new_team': 'WAS'},
            'Lawrence Cager': {'old_team': 'UGA', 'new_team': 'WAS'},
            'Cole Turner': {'old_team': 'NEVADA', 'new_team': 'WAS'},
            'Tyler Ott': {'old_team': 'HARV', 'new_team': 'WAS'},
            'Daniel Bellinger': {'old_team': 'SDSU', 'new_team': 'NYG'},
            'Chris Manhertz': {'old_team': 'CANISIUS', 'new_team': 'NYG'},
            'Greg Dulcich': {'old_team': 'UCLA', 'new_team': 'NYG'},
            'Thomas Fidone II': {'old_team': 'NEB', 'new_team': 'NYG'},
            'Jermaine Terry II': {'old_team': 'CAL', 'new_team': 'NYG'},
            'Tyler Mabry': {'old_team': 'MARYLAND', 'new_team': 'CAR'},
            'Tommy Tremble': {'old_team': 'ND', 'new_team': 'CAR'},
            'Hunter Long': {'old_team': 'BOSTON', 'new_team': 'JAX'},
            'Johnny Mundt': {'old_team': 'ORE', 'new_team': 'JAX'},
            'Quintin Morris': {'old_team': 'BOWLING', 'new_team': 'JAX'},
            'Shawn Bowman': {'old_team': 'BOSTON', 'new_team': 'JAX'},
            'Patrick Herbert': {'old_team': 'ORE', 'new_team': 'JAX'},
            'John Copenhaver': {'old_team': 'WAKE', 'new_team': 'JAX'},
            'Mitchell Evans': {'old_team': 'ND', 'new_team': 'CAR'},
            'Dominique Dafney': {'old_team': 'INDST', 'new_team': 'CAR'},
            'James Mitchell': {'old_team': 'VT', 'new_team': 'CAR'},
            'Bryce Pierre': {'old_team': 'NORTHERN', 'new_team': 'CAR'},
            'Blake Whiteheart': {'old_team': 'WAKE', 'new_team': 'CLE'},
            'Brenden Bates': {'old_team': 'UK', 'new_team': 'CLE'},
            'Sal Cannella': {'old_team': 'AUB', 'new_team': 'CLE'},
            'Brent Matiscik': {'old_team': 'BAYLOR', 'new_team': 'CLE'},
            'Drew Sample': {'old_team': 'WASH', 'new_team': 'CIN'},
            'Erick All Jr.': {'old_team': 'MICH', 'new_team': 'CIN'},
            'Tanner Hudson': {'old_team': 'SOUTHEAST', 'new_team': 'CIN'},
            'Tanner McLachlan': {'old_team': 'ARIZ', 'new_team': 'CIN'},
            'Cam Grandy': {'old_team': 'ILLST', 'new_team': 'CIN'},
            'Kole Taylor': {'old_team': 'LSU', 'new_team': 'CIN'},
            'William Wagner': {'old_team': 'BUFFALO', 'new_team': 'CIN'},
            'Cal Adomitis': {'old_team': 'PITT', 'new_team': 'CIN'},
            'Josh Whyle': {'old_team': 'CINCY', 'new_team': 'TEN'},
            'David Martin-Robinson': {'old_team': 'TEMPLE', 'new_team': 'TEN'},
            'Thomas Odukoya': {'old_team': 'EASTERN', 'new_team': 'TEN'},
            'Drake Dabney': {'old_team': 'BAYLOR', 'new_team': 'TEN'},
            'Lucas Krull': {'old_team': 'PITT', 'new_team': 'DEN'},
            'Nate Adkins': {'old_team': 'ETSU', 'new_team': 'DEN'},
            'Caleb Lohner': {'old_team': 'BYU', 'new_team': 'DEN'},
            'Caden Prieskorn': {'old_team': 'MEM', 'new_team': 'DEN'},
            'Mitchell Fraboni': {'old_team': 'ARIZST', 'new_team': 'DEN'},
            'Eric Saubert': {'old_team': 'DRAKE', 'new_team': 'SEA'},
            'Nick Kallerup': {'old_team': 'CAL', 'new_team': 'SEA'},
            'Marshall Lang': {'old_team': 'NORTHWESTERN', 'new_team': 'SEA'},
            'Luke Farrell': {'old_team': 'OSU', 'new_team': 'SF'},
            'Ross Dwelley': {'old_team': 'USD', 'new_team': 'SF'},
            'Brayden Willis': {'old_team': 'OKLA', 'new_team': 'SF'},
            'Jake Tonges': {'old_team': 'CAL', 'new_team': 'SF'},
            'Ben Sims': {'old_team': 'BAYLOR', 'new_team': 'GB'},
            'John FitzPatrick': {'old_team': 'UGA', 'new_team': 'GB'},
            'Messiah Swinson': {'old_team': 'ARIZST', 'new_team': 'GB'},
            'Johnny Lumpkin': {'old_team': 'ULM', 'new_team': 'GB'},
            'Brock Wright': {'old_team': 'ND', 'new_team': 'DET'},
            'Kenny Yeboah': {'old_team': 'OLEMISS', 'new_team': 'DET'},
            'Shane Zylstra': {'old_team': 'MINNST', 'new_team': 'DET'},
            'Luke Deal': {'old_team': 'AUB', 'new_team': 'DET'},
            'Zach Horton': {'old_team': 'OHIO', 'new_team': 'DET'},
            'Colby Parkinson': {'old_team': 'STAN', 'new_team': 'LAR'},
            'Davis Allen': {'old_team': 'CLEM', 'new_team': 'LAR'},
            'Mark Redman': {'old_team': 'SDSU', 'new_team': 'LAR'},
            'Anthony Torres': {'old_team': 'STAN', 'new_team': 'LAR'},
            'Brevin Jordan': {'old_team': 'MIAMI', 'new_team': 'HOU'},
            'Luke Lachey': {'old_team': 'IOWA', 'new_team': 'HOU'},
            'Irv Smith Jr.': {'old_team': 'ALA', 'new_team': 'HOU'},
            'Jakob Johnson': {'old_team': 'TENN', 'new_team': 'HOU'}
        }
    
    def _normalize_name(self, name: str) -> str:
        """Enhanced normalization with better handling of common variations"""
        if pd.isna(name):
            return ""
        
        name = str(name).strip()
        
        # Handle common nickname patterns BEFORE removing suffixes
        nickname_patterns = {
            r'\b(DJ|D\.J\.)\b': 'DJ',
            r'\b(CJ|C\.J\.)\b': 'CJ', 
            r'\b(TJ|T\.J\.)\b': 'TJ',
            r'\b(AJ|A\.J\.)\b': 'AJ',
            r'\b(JJ|J\.J\.)\b': 'JJ',
            r'\b(RJ|R\.J\.)\b': 'RJ',
            r'\bMike\b': 'Michael',
            r'\bTony\b': 'Anthony',
            r'\bBill\b': 'William',
            r'\bBob\b': 'Robert',
            r'\bJim\b': 'James',
            r'\bTom\b': 'Thomas',
            r'\bDan\b': 'Daniel',
            r'\bMatt\b': 'Matthew',
            r'\bChris\b': 'Christopher',
            r'\bNick\b': 'Nicholas',
            r'\bAlex\b': 'Alexander',
            r'\bSam\b': 'Samuel',
            r'\bBen\b': 'Benjamin',
            r'\bZach\b': 'Zachary',
            r'\bJosh\b': 'Joshua',
            r'\bJake\b': 'Jacob',
            r'\bDave\b': 'David',
            r'\bSteve\b': 'Steven',
            r'\bGreg\b': 'Gregory',
            r'\bJeff\b': 'Jeffrey',
            r'\bTim\b': 'Timothy',
            r'\bJoe\b': 'Joseph',
            r'\bAndy\b': 'Andrew',
            r'\bMike\b': 'Michael'
        }
        
        for pattern, replacement in nickname_patterns.items():
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
        
        # Handle apostrophes and contractions
        name = re.sub(r"'", "", name)  # Remove apostrophes (O'Dell -> ODell)
        
        # Remove common suffixes that cause issues
        suffixes_to_remove = [
            r'\s+Jr\.?$', r'\s+Sr\.?$', r'\s+I{2,4}$', r'\s+V+$',  # Jr., Sr., III, IV, V
            r'\s+II$', r'\s+IV$', r'\s+VI$', r'\s+VII$', r'\s+VIII$', r'\s+IX$'
        ]
        
        for suffix in suffixes_to_remove:
            name = re.sub(suffix, '', name, flags=re.IGNORECASE)
        
        # Remove extra spaces and convert to lowercase
        name = re.sub(r'\s+', ' ', name).lower()
        
        # Remove special characters but keep spaces
        name = re.sub(r'[^\w\s]', '', name)
        
        return name.strip()
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Multi-algorithm similarity calculation for significantly better accuracy"""
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # NEW: Handle abbreviated names (e.g., "S.Diggs" vs "Stefon Diggs")
        if '.' in norm1 or '.' in norm2:
            # Split by dots and spaces
            parts1 = re.split(r'[.\s]+', norm1)
            parts2 = re.split(r'[.\s]+', norm2)
            
            # Check if one is abbreviation of the other
            if len(parts1) == 1 and len(parts2) > 1:
                # norm1 is abbreviated (e.g., "sdiggs")
                if parts1[0] in ''.join(parts2):
                    return 0.9  # High confidence for abbreviation match
            elif len(parts2) == 1 and len(parts1) > 1:
                # norm2 is abbreviated (e.g., "sdiggs")
                if parts2[0] in ''.join(parts1):
                    return 0.9  # High confidence for abbreviation match
            elif len(parts1) == 2 and len(parts2) == 2:
                # Both have 2 parts, check initials
                if parts1[0][0] == parts2[0][0] and parts1[1] == parts2[1]:
                    return 0.95  # Very high confidence for initial + last name match
        
        # Multiple similarity metrics using different algorithms
        ratio = fuzz.ratio(norm1, norm2) / 100
        partial_ratio = fuzz.partial_ratio(norm1, norm2) / 100
        token_sort = fuzz.token_sort_ratio(norm1, norm2) / 100
        token_set = fuzz.token_set_ratio(norm1, norm2) / 100
        
        # Jellyfish algorithms for additional coverage
        jaro = jellyfish.jaro_winkler_similarity(norm1, norm2)
        hamming = 1 - (jellyfish.hamming_distance(norm1, norm2) / max(len(norm1), len(norm2))) if len(norm1) > 0 and len(norm2) > 0 else 0
        
        # Weighted combination of all algorithms
        similarity = (
            ratio * 0.25 +           # Basic ratio
            partial_ratio * 0.20 +   # Partial matching
            token_sort * 0.20 +      # Token order independent
            token_set * 0.15 +       # Token set matching
            jaro * 0.15 +            # Jaro-Winkler (good for names)
            hamming * 0.05           # Hamming distance
        )
        
        # Boost for partial contains (substring matches)
        if norm1 in norm2 or norm2 in norm1:
            similarity += 0.15
        
        # Boost for high partial ratio (indicates strong partial match)
        if partial_ratio > 0.8:
            similarity += 0.1
        
        # Boost for high token set ratio (indicates same words, different order)
        if token_set > 0.8:
            similarity += 0.1
        
        return min(similarity, 1.0)
    
    def _validate_position_match(self, dk_position: str, nfl_position: str) -> Tuple[bool, float]:
        """Validate if positions match and return confidence score"""
        if pd.isna(dk_position) or pd.isna(nfl_position):
            return False, 0.0
        
        dk_pos = str(dk_position).strip().upper()
        nfl_pos = str(nfl_position).strip().upper()
        
        # Direct match
        if dk_pos == nfl_pos:
            return True, 1.0
        
        # Mapped match
        dk_mapped = self.position_mapping.get(dk_pos, dk_pos)
        if dk_mapped == nfl_pos:
            return True, 0.95
        
        # Partial match (e.g., "WR" vs "WR1")
        if dk_pos in nfl_pos or nfl_pos in dk_pos:
            return True, 0.9
        
        return False, 0.0
    
    def _validate_team_match(self, dk_team: str, nfl_team: str, dk_name: str = None, dk_position: str = None) -> Tuple[bool, float]:
        """Enhanced team validation with trade awareness and position-based logic"""
        if pd.isna(dk_team) or pd.isna(nfl_team):
            return False, 0.0
        
        dk_team = str(dk_team).strip().upper()
        nfl_team = str(nfl_team).strip().upper()
        
        # Direct match
        if dk_team == nfl_team:
            return True, 1.0
        
        # Mapped match
        dk_mapped = self.team_mapping.get(dk_team, dk_team)
        if dk_mapped == nfl_team:
            return True, 0.95
        
        # Check manual team changes first
        if dk_name and dk_name in self.team_changes:
            expected_old = self.team_changes[dk_name]['old_team']
            expected_new = self.team_changes[dk_name]['new_team']
            
            if (nfl_team == expected_old and dk_team == expected_new) or \
               (nfl_team == expected_new and dk_team == expected_old):
                return True, 0.95  # High confidence for known trades
        
        # NEW: Try dynamic team change detection
        dynamic_match, dynamic_confidence = self._detect_dynamic_team_changes(dk_team, nfl_team, dk_position)
        if dynamic_match:
            return True, dynamic_confidence
        
        # For high-value positions (QB, RB, WR, TE), be more forgiving of team mismatches
        # as they're more likely to be traded or moved between teams
        if dk_position and dk_position in ['QB', 'RB', 'WR', 'TE']:
            # These positions are more likely to be traded/moved
            return False, 0.5  # Increased from 0.3 to 0.5 for skill positions
        else:
            # For K, DST, etc., be more strict about team matches
            return False, 0.2  # Lower confidence for non-skill positions
    
    def _calculate_composite_score(self, name_similarity: float, position_match: bool, 
                                  position_confidence: float, team_match: bool, 
                                  team_confidence: float, dk_position: str = None) -> float:
        """Calculate composite confidence score based on multiple factors with position-aware logic"""
        
        # Base score from name similarity
        base_score = name_similarity
        
        # Position bonus/penalty
        if position_match:
            base_score += position_confidence * 0.2  # Position adds up to 20%
        else:
            base_score *= 0.5  # No position match cuts score in half
        
        # Team bonus/penalty - ENHANCED with position-aware logic
        if team_match:
            base_score += team_confidence * 0.15  # Team adds up to 15%
        else:
            # NEW: More intelligent team mismatch handling
            if dk_position and dk_position in ['QB', 'RB', 'WR', 'TE']:
                # Skill positions are more likely to be traded
                if name_similarity > 0.85:
                    # Very high name similarity - likely the same player, just traded
                    base_score *= 0.85  # Only reduce by 15% instead of 20%
                elif name_similarity > 0.75:
                    # High name similarity - probably the same player
                    base_score *= 0.9  # Reduce by 10%
                else:
                    # Lower name similarity - team mismatch is more concerning
                    base_score *= 0.8  # Normal penalty
            else:
                # Non-skill positions (K, DST) - be more strict about team matches
                base_score *= 0.7  # Higher penalty for team mismatches
        
        return min(base_score, 1.0)
    
    def _find_best_match_with_context(self, dk_player: Dict, nfl_players: List[Dict], 
                                     threshold: float = 0.7) -> Tuple[Optional[Dict], float]:
        """Find best NFL match using position, team, and name context"""
        best_match = None
        best_score = 0.0
        
        dk_name = dk_player['Name']
        dk_position = dk_player.get('Position')
        dk_team = dk_player.get('TeamAbbrev')
        
        for nfl_player in nfl_players:
            nfl_name = nfl_player['player_name']
            nfl_position = nfl_player.get('position')
            nfl_team = nfl_player.get('recent_team')
            
            # Calculate name similarity
            name_similarity = self._calculate_name_similarity(dk_name, nfl_name)
            
            # Validate position match
            position_match, position_confidence = self._validate_position_match(dk_position, nfl_position)
            
            # Validate team match
            team_match, team_confidence = self._validate_team_match(dk_team, nfl_team, dk_name, dk_position)
            
            # Calculate composite score
            composite_score = self._calculate_composite_score(
                name_similarity, position_match, position_confidence, 
                team_match, team_confidence, dk_position
            )
            
            if composite_score > best_score and composite_score >= threshold:
                best_score = composite_score
                best_match = {
                    'nfl_player': nfl_player,
                    'name_similarity': name_similarity,
                    'position_match': position_match,
                    'position_confidence': position_confidence,
                    'team_match': team_match,
                    'team_confidence': team_confidence,
                    'composite_score': composite_score
                }
        
        return best_match, best_score
    
    def match_players_with_context(self, dk_df: pd.DataFrame, nfl_df: pd.DataFrame,
                                 similarity_threshold: float = 0.7) -> Tuple[pd.DataFrame, Dict]:
        """
        Match players using position, team, and name context for better accuracy
        """
        logger.info(f"Starting context-enhanced matching: {len(dk_df)} DK players vs {len(nfl_df)} NFL players")
        
        # Get unique NFL players (avoid duplicates)
        nfl_unique = nfl_df.drop_duplicates(subset=['player_name', 'position', 'recent_team'])
        nfl_players = nfl_unique.to_dict('records')
        
        # Initialize results
        matches = []
        unmatched = []
        ambiguous = []
        
        for _, dk_row in dk_df.iterrows():
            dk_player = dk_row.to_dict()
            dk_name = dk_player['Name']
            
            if self.debug:
                logger.info(f"Processing DK player: {dk_name} ({dk_player.get('Position')} - {dk_player.get('TeamAbbrev')})")
            
            # Step 1: Try to find player in centralized database
            db_player = self.db.find_player_by_name(dk_name, "draftkings")
            
            if db_player:
                # Player found in database - try to match with NFL data
                nfl_match = self._find_nfl_match_for_db_player(db_player, nfl_df)
                
                if nfl_match:
                    matches.append({
                        'dk_name': dk_name,
                        'nfl_name': nfl_match['player_name'],
                        'match_type': 'database',
                        'similarity': 1.0,
                        'dk_id': dk_player['ID'],
                        'nfl_id': nfl_match['player_id'],
                        'canonical_name': db_player['canonical_name'],
                        'confidence': db_player.get('confidence_score', 1.0),
                        'dk_position': dk_player.get('Position'),
                        'nfl_position': nfl_match.get('position'),
                        'dk_team': dk_player.get('TeamAbbrev'),
                        'nfl_team': nfl_match.get('recent_team'),
                        'position_match': True,
                        'team_match': True
                    })
                    self.matching_stats['database_matches'] += 1
                    continue
            
            # Step 2: Try exact match with NFL data
            exact_matches = [p for p in nfl_players if p['player_name'] == dk_name]
            if exact_matches:
                if len(exact_matches) == 1:
                    nfl_match = exact_matches[0]
                    matches.append({
                        'dk_name': dk_name,
                        'nfl_name': nfl_match['player_name'],
                        'match_type': 'exact',
                        'similarity': 1.0,
                        'dk_id': dk_player['ID'],
                        'nfl_id': nfl_match['player_id'],
                        'canonical_name': dk_name,
                        'confidence': 1.0,
                        'dk_position': dk_player.get('Position'),
                        'nfl_position': nfl_match.get('position'),
                        'dk_team': dk_player.get('TeamAbbrev'),
                        'nfl_team': nfl_match.get('recent_team'),
                        'position_match': True,
                        'team_match': True
                    })
                    self.matching_stats['exact_matches'] += 1
                    continue
                else:
                    # Multiple exact matches - need to disambiguate
                    ambiguous.append({
                        'dk_name': dk_name,
                        'dk_id': dk_player['ID'],
                        'dk_position': dk_player.get('Position'),
                        'dk_team': dk_player.get('TeamAbbrev'),
                        'nfl_matches': exact_matches
                    })
                    self.matching_stats['ambiguous'] += 1
                    continue
            
            # Step 3: Try context-enhanced fuzzy matching
            best_match, best_score = self._find_best_match_with_context(
                dk_player, nfl_players, similarity_threshold
            )
            
            if best_match:
                nfl_player = best_match['nfl_player']
                
                # Check if this creates ambiguity
                existing_matches = [m for m in matches if m['nfl_id'] == nfl_player['player_id']]
                if existing_matches:
                    ambiguous.append({
                        'dk_name': dk_name,
                        'dk_id': dk_player['ID'],
                        'dk_position': dk_player.get('Position'),
                        'dk_team': dk_player.get('TeamAbbrev'),
                        'nfl_name': nfl_player['player_name'],
                        'nfl_id': nfl_player['player_id'],
                        'similarity': best_score,
                        'conflict_with': existing_matches[0]['dk_name']
                    })
                    self.matching_stats['ambiguous'] += 1
                else:
                    match_type = 'position_team_match' if (best_match['position_match'] and best_match['team_match']) else 'fuzzy'
                    
                    matches.append({
                        'dk_name': dk_name,
                        'nfl_name': nfl_player['player_name'],
                        'match_type': match_type,
                        'similarity': best_score,
                        'dk_id': dk_player['ID'],
                        'nfl_id': nfl_player['player_id'],
                        'canonical_name': f"{dk_name} (context)",
                        'confidence': best_score,
                        'dk_position': dk_player.get('Position'),
                        'nfl_position': nfl_player.get('position'),
                        'dk_team': dk_player.get('TeamAbbrev'),
                        'nfl_team': nfl_player.get('recent_team'),
                        'position_match': best_match['position_match'],
                        'team_match': best_match['team_match'],
                        'name_similarity': best_match['name_similarity'],
                        'position_confidence': best_match['position_confidence'],
                        'team_confidence': best_match['team_confidence']
                    })
                    
                    if match_type == 'position_team_match':
                        self.matching_stats['position_team_matches'] += 1
                    else:
                        self.matching_stats['fuzzy_matches'] += 1
            else:
                unmatched.append({
                    'dk_name': dk_name,
                    'dk_id': dk_player['ID'],
                    'dk_position': dk_player.get('Position'),
                    'dk_team': dk_player.get('TeamAbbrev')
                })
                self.matching_stats['unmatched'] += 1
        
        # Create results dataframe
        if matches:
            results_df = pd.DataFrame(matches)
        else:
            results_df = pd.DataFrame(columns=['dk_name', 'nfl_name', 'match_type', 'similarity', 
                                             'dk_id', 'nfl_id', 'canonical_name', 'confidence'])
        
        # Log statistics
        logger.info(f"Matching complete:")
        logger.info(f"  Database matches: {self.matching_stats['database_matches']}")
        logger.info(f"  Exact matches: {self.matching_stats['exact_matches']}")
        logger.info(f"  Position+Team matches: {self.matching_stats['position_team_matches']}")
        logger.info(f"  Fuzzy matches: {self.matching_stats['fuzzy_matches']}")
        logger.info(f"  Unmatched: {self.matching_stats['unmatched']}")
        logger.info(f"  Ambiguous: {self.matching_stats['ambiguous']}")
        
        return results_df, {
            'matches': matches,
            'unmatched': unmatched,
            'ambiguous': ambiguous,
            'stats': self.matching_stats
        }
    
    def _find_nfl_match_for_db_player(self, db_player: Dict, nfl_df: pd.DataFrame) -> Optional[Dict]:
        """Find NFL data match for a player from the database"""
        try:
            # Get all aliases for this player
            aliases = self.db.get_all_aliases(db_player['id'])
            
            # Look for NFL API aliases
            for alias in aliases:
                if alias['source_name'] == 'nfl_api':
                    nfl_match = nfl_df[nfl_df['player_name'] == alias['alias_name']]
                    if not nfl_match.empty:
                        return nfl_match.iloc[0].to_dict()
            
            # If no NFL API alias, try fuzzy matching with canonical name
            best_match, best_score = self._find_best_match_with_context(
                {'Name': db_player['canonical_name']}, 
                nfl_df.to_dict('records'), 
                threshold=0.8
            )
            
            if best_match:
                return best_match['nfl_player']
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding NFL match for {db_player['canonical_name']}: {e}")
            return None
    
    def auto_populate_database(self, dk_df: pd.DataFrame, nfl_df: pd.DataFrame):
        """Automatically populate the database with players from both sources"""
        logger.info("Auto-populating centralized database...")
        
        # Process DraftKings players
        for _, row in dk_df.iterrows():
            dk_name = row['Name']
            dk_id = row['ID']
            position = row['Position']
            team = row['TeamAbbrev']
            
            # Check if player already exists
            existing_player = self.db.find_player_by_name(dk_name, "draftkings")
            
            if not existing_player:
                # Parse name into first/last
                name_parts = dk_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                else:
                    first_name = dk_name
                    last_name = ""
                
                # Add to database
                player_id = self.db.add_player(
                    canonical_name=dk_name,
                    first_name=first_name,
                    last_name=last_name,
                    position=position,
                    team=team
                )
                
                # Add DraftKings alias
                self.db.add_alias(player_id, dk_name, "draftkings", 1.0)
                
                # Add external ID
                self.db.add_external_id(player_id, "draftkings", str(dk_id), dk_name, 1.0)
        
        # Process NFL API players
        for _, row in nfl_df.iterrows():
            nfl_name = row['player_name']
            nfl_id = row['player_id']
            position = row.get('position')
            team = row.get('recent_team')
            
            # Check if player already exists
            existing_player = self.db.find_player_by_name(nfl_name, "nfl_api")
            
            if not existing_player:
                # Try to find by canonical name (remove abbreviation)
                if '.' in nfl_name:
                    # This is an abbreviated name like "J.Chase"
                    # We'll need to match it manually or leave it for now
                    continue
                
                # Add to database
                player_id = self.db.add_player(
                    canonical_name=nfl_name,
                    nfl_id=nfl_id,
                    position=position,
                    team=team
                )
                
                # Add NFL API alias
                self.db.add_alias(player_id, nfl_name, "nfl_api", 1.0)
                
                # Add external ID
                self.db.add_external_id(player_id, "nfl_api", str(nfl_id), nfl_name, 1.0)
        
        logger.info("Database population complete")
    
    def save_reports(self, results: Dict, output_dir: str = "reports"):
        """Save matching reports to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save matched players
        if results['matches']:
            matches_df = pd.DataFrame(results['matches'])
            matches_df.to_csv(f"{output_dir}/matched_players_v5.csv", index=False)
            logger.info(f"Saved {len(matches_df)} matches to {output_dir}/matched_players_v5.csv")
        
        # Save unmatched players
        if results['unmatched']:
            unmatched_df = pd.DataFrame(results['unmatched'])
            unmatched_df.to_csv(f"{output_dir}/unmatched_players_v5.csv", index=False)
            logger.info(f"Saved {len(unmatched_df)} unmatched to {output_dir}/unmatched_players_v5.csv")
        
        # Save ambiguous matches
        if results['ambiguous']:
            ambiguous_df = pd.DataFrame(results['ambiguous'])
            ambiguous_df.to_csv(f"{output_dir}/ambiguous_matches_v5.csv", index=False)
            logger.info(f"Saved {len(ambiguous_df)} ambiguous to {output_dir}/ambiguous_matches_v5.csv")
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
    
    def _detect_dynamic_team_changes(self, dk_team: str, nfl_team: str, dk_position: str) -> Tuple[bool, float]:
        """Dynamically detect potential team changes based on patterns and position"""
        
        # If teams are the same, no change
        if dk_team == nfl_team:
            return False, 0.0
        
        # Check for common team abbreviation variations
        team_variations = {
            'LA': 'LAR', 'LAR': 'LA',  # Rams abbreviation variations
            'LV': 'OAK', 'OAK': 'LV',  # Raiders move
            'WAS': 'WSH', 'WSH': 'WAS',  # Commanders variations
            'SF': 'SFO', 'SFO': 'SF',  # 49ers variations
            'KC': 'KCC', 'KCC': 'KC',  # Chiefs variations
            'GB': 'GNB', 'GNB': 'GB',  # Packers variations
            'TB': 'TBB', 'TBB': 'TB',  # Buccaneers variations
            'NE': 'NWE', 'NWE': 'NE',  # Patriots variations
            'NO': 'NOS', 'NOS': 'NO',  # Saints variations
            'IND': 'IND', 'IND': 'IND',  # Colts (same)
            'HOU': 'HST', 'HST': 'HOU',  # Texans variations
            'JAX': 'JAC', 'JAC': 'JAX',  # Jaguars variations
            'TEN': 'TEN', 'TEN': 'TEN',  # Titans (same)
            'CLE': 'CLE', 'CLE': 'CLE',  # Browns (same)
            'CIN': 'CIN', 'CIN': 'CIN',  # Bengals (same)
            'BAL': 'BAL', 'BAL': 'BAL',  # Ravens (same)
            'PIT': 'PIT', 'PIT': 'PIT',  # Steelers (same)
            'NYJ': 'NYJ', 'NYJ': 'NYJ',  # Jets (same)
            'NYG': 'NYG', 'NYG': 'NYG',  # Giants (same)
            'BUF': 'BUF', 'BUF': 'BUF',  # Bills (same)
            'MIA': 'MIA', 'MIA': 'MIA',  # Dolphins (same)
            'ATL': 'ATL', 'ATL': 'ATL',  # Falcons (same)
            'CAR': 'CAR', 'CAR': 'CAR',  # Panthers (same)
            'DET': 'DET', 'DET': 'DET',  # Lions (same)
            'MIN': 'MIN', 'MIN': 'MIN',  # Vikings (same)
            'CHI': 'CHI', 'CHI': 'CHI',  # Bears (same)
            'DAL': 'DAL', 'DAL': 'DAL',  # Cowboys (same)
            'PHI': 'PHI', 'PHI': 'PHI',  # Eagles (same)
            'ARI': 'ARI', 'ARI': 'ARI',  # Cardinals (same)
            'SEA': 'SEA', 'SEA': 'SEA',  # Seahawks (same)
            'DEN': 'DEN', 'DEN': 'DEN',  # Broncos (same)
            'LAC': 'LAC', 'LAC': 'LAC'   # Chargers (same)
        }
        
        # Check for abbreviation variations
        if dk_team in team_variations and team_variations[dk_team] == nfl_team:
            return True, 0.9  # High confidence for abbreviation variations
        
        # Check for reverse mapping
        if nfl_team in team_variations and team_variations[nfl_team] == dk_team:
            return True, 0.9  # High confidence for abbreviation variations
        
        # For skill positions, be more lenient about team mismatches
        if dk_position in ['QB', 'RB', 'WR', 'TE']:
            # These positions are more likely to be traded
            return True, 0.6  # Medium confidence for potential trades
        else:
            # For K, DST, etc., be more strict
            return False, 0.0
        
        return False, 0.0

def main():
    """Test the enhanced name matcher with context-aware matching"""
    print("🧪 TESTING ENHANCED NAME MATCHER V5 WITH CONTEXT-AWARE MATCHING")
    print("=" * 70)
    
    try:
        # Load data
        print("Loading DraftKings data...")
        dk_df = pd.read_csv("data/DKSalaries.csv")
        print(f"✓ Loaded {len(dk_df)} DK players")
        
        print("Loading NFL API data...")
        from nfl_data_py import import_weekly_data
        nfl_df = import_weekly_data([2024])
        print(f"✓ Loaded {len(nfl_df)} NFL records")
        
        # Initialize matcher with database
        matcher = EnhancedNameMatcherV5(debug=True)
        
        # Auto-populate database
        print("\n🏗️  Auto-populating centralized database...")
        matcher.auto_populate_database(dk_df, nfl_df)
        
        # Export database to CSV for review
        matcher.db.export_to_csv()
        
        # Perform context-enhanced matching
        print("\n🔍 Performing context-enhanced name matching...")
        results_df, results = matcher.match_players_with_context(dk_df, nfl_df, similarity_threshold=0.7)
        
        # Save reports
        print("\n💾 Saving reports...")
        matcher.save_reports(results)
        
        # Show summary
        print("\n📊 MATCHING SUMMARY:")
        print(f"Total DK players: {len(dk_df)}")
        print(f"Successfully matched: {len(results['matches'])}")
        print(f"Unmatched: {len(results['unmatched'])}")
        print(f"Ambiguous: {len(results['ambiguous'])}")
        
        # Show some examples
        if results['matches']:
            print("\n✅ SAMPLE MATCHES:")
            for match in results['matches'][:5]:
                print(f"  DK: {match['dk_name']} ({match.get('dk_position', 'N/A')} - {match.get('dk_team', 'N/A')})")
                print(f"     → NFL: {match['nfl_name']} ({match.get('nfl_position', 'N/A')} - {match.get('nfl_team', 'N/A')})")
                print(f"     Type: {match['match_type']}, Confidence: {match['similarity']:.2f}")
                if 'position_match' in match:
                    print(f"     Position match: {match['position_match']}, Team match: {match['team_match']}")
                print()
        
        if results['unmatched']:
            print(f"\n❌ SAMPLE UNMATCHED:")
            for player in results['unmatched'][:5]:
                print(f"  {player['dk_name']} ({player.get('dk_position', 'N/A')} - {player.get('dk_team', 'N/A')})")
        
        # Show matching statistics by type
        print("\n📈 MATCHING BREAKDOWN:")
        stats = results['stats']
        total_matched = sum([stats['database_matches'], stats['exact_matches'], 
                           stats['position_team_matches'], stats['fuzzy_matches']])
        
        print(f"  Database matches: {stats['database_matches']} ({stats['database_matches']/len(dk_df)*100:.1f}%)")
        print(f"  Exact matches: {stats['exact_matches']} ({stats['exact_matches']/len(dk_df)*100:.1f}%)")
        print(f"  Position+Team matches: {stats['position_team_matches']} ({stats['position_team_matches']/len(dk_df)*100:.1f}%)")
        print(f"  Fuzzy matches: {stats['fuzzy_matches']} ({stats['fuzzy_matches']/len(dk_df)*100:.1f}%)")
        print(f"  Total matched: {total_matched} ({total_matched/len(dk_df)*100:.1f}%)")
        print(f"  Unmatched: {stats['unmatched']} ({stats['unmatched']/len(dk_df)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'matcher' in locals():
            matcher.close()

if __name__ == "__main__":
    main()
