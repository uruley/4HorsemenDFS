#!/usr/bin/env python3
"""
Centralized Player Database System
Handles multiple data sources with different identifier systems
"""
import pandas as pd
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CentralizedPlayerDatabase:
    """
    Centralized database for managing player identities across multiple data sources
    """
    
    def __init__(self, db_path: str = "data/player_database.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with proper schema"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create players table (master player records)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_name TEXT UNIQUE NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    position TEXT,
                    team TEXT,
                    nfl_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create external_ids table (mappings to external systems)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS external_ids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    source_name TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    external_name TEXT,
                    confidence_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id),
                    UNIQUE(source_name, external_id)
                )
            ''')
            
            # Create aliases table (name variations)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    alias_name TEXT NOT NULL,
                    source_name TEXT,
                    confidence_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id),
                    UNIQUE(alias_name, source_name)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_canonical ON players(canonical_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_external_ids_source ON external_ids(source_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_aliases_name ON aliases(alias_name)')
            
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def add_player(self, canonical_name: str, first_name: str = None, 
                   last_name: str = None, position: str = None, team: str = None,
                   nfl_id: str = None) -> int:
        """Add a new player to the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO players 
                (canonical_name, first_name, last_name, position, team, nfl_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (canonical_name, first_name, last_name, position, team, nfl_id))
            
            player_id = cursor.lastrowid
            self.conn.commit()
            logger.info(f"Added player: {canonical_name} (ID: {player_id})")
            return player_id
            
        except Exception as e:
            logger.error(f"Error adding player {canonical_name}: {e}")
            raise
    
    def add_external_id(self, player_id: int, source_name: str, external_id: str,
                        external_name: str = None, confidence_score: float = 1.0):
        """Add an external ID mapping for a player"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO external_ids 
                (player_id, source_name, external_id, external_name, confidence_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (player_id, source_name, external_id, external_name, confidence_score))
            
            self.conn.commit()
            logger.info(f"Added external ID: {source_name}:{external_id} for player {player_id}")
            
        except Exception as e:
            logger.error(f"Error adding external ID: {e}")
            raise
    
    def add_alias(self, player_id: int, alias_name: str, source_name: str = None,
                  confidence_score: float = 1.0):
        """Add a name alias for a player"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO aliases 
                (player_id, alias_name, source_name, confidence_score)
                VALUES (?, ?, ?, ?)
            ''', (player_id, alias_name, source_name, confidence_score))
            
            self.conn.commit()
            logger.info(f"Added alias: {alias_name} for player {player_id}")
            
        except Exception as e:
            logger.error(f"Error adding alias: {e}")
            raise
    
    def find_player_by_external_id(self, source_name: str, external_id: str) -> Optional[Dict]:
        """Find a player by their external ID from a specific source"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT p.*, e.external_name, e.confidence_score
                FROM players p
                JOIN external_ids e ON p.id = e.player_id
                WHERE e.source_name = ? AND e.external_id = ?
            ''', (source_name, str(external_id)))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            logger.error(f"Error finding player by external ID: {e}")
            return None
    
    def find_player_by_name(self, name: str, source_name: str = None) -> Optional[Dict]:
        """Find a player by name (canonical or alias)"""
        try:
            cursor = self.conn.cursor()
            
            # First try canonical name
            cursor.execute('SELECT * FROM players WHERE canonical_name = ?', (name,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            # Then try aliases
            if source_name:
                cursor.execute('''
                    SELECT p.*, a.confidence_score
                    FROM players p
                    JOIN aliases a ON p.id = a.player_id
                    WHERE a.alias_name = ? AND (a.source_name = ? OR a.source_name IS NULL)
                    ORDER BY a.confidence_score DESC
                ''', (name, source_name))
            else:
                cursor.execute('''
                    SELECT p.*, a.confidence_score
                    FROM players p
                    JOIN aliases a ON p.id = a.player_id
                    WHERE a.alias_name = ?
                    ORDER BY a.confidence_score DESC
                ''', (name,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding player by name: {e}")
            return None
    
    def get_all_external_ids(self, player_id: int) -> List[Dict]:
        """Get all external IDs for a player"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT source_name, external_id, external_name, confidence_score
                FROM external_ids
                WHERE player_id = ?
                ORDER BY confidence_score DESC
            ''', (player_id,))
            
            rows = cursor.fetchall()
            columns = ['source_name', 'external_id', 'external_name', 'confidence_score']
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting external IDs: {e}")
            return []
    
    def get_all_aliases(self, player_id: int) -> List[Dict]:
        """Get all aliases for a player"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT alias_name, source_name, confidence_score
                FROM aliases
                WHERE player_id = ?
                ORDER BY confidence_score DESC
            ''', (player_id,))
            
            rows = cursor.fetchall()
            columns = ['alias_name', 'source_name', 'confidence_score']
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting aliases: {e}")
            return []
    
    def search_players(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for players by name (fuzzy search)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT DISTINCT p.*, 
                       COALESCE(a.confidence_score, 1.0) as search_score
                FROM players p
                LEFT JOIN aliases a ON p.id = a.player_id
                WHERE p.canonical_name LIKE ? 
                   OR p.first_name LIKE ? 
                   OR p.last_name LIKE ?
                   OR a.alias_name LIKE ?
                ORDER BY search_score DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error searching players: {e}")
            return []
    
    def export_to_csv(self, output_dir: str = "data"):
        """Export database tables to CSV files"""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Export players
            players_df = pd.read_sql_query("SELECT * FROM players", self.conn)
            players_df.to_csv(f"{output_dir}/players_master.csv", index=False)
            
            # Export external IDs
            external_ids_df = pd.read_sql_query("SELECT * FROM external_ids", self.conn)
            external_ids_df.to_csv(f"{output_dir}/external_ids.csv", index=False)
            
            # Export aliases
            aliases_df = pd.read_sql_query("SELECT * FROM aliases", self.conn)
            aliases_df.to_csv(f"{output_dir}/aliases.csv", index=False)
            
            logger.info(f"Exported database to {output_dir}/")
            
        except Exception as e:
            logger.error(f"Error exporting database: {e}")
    
    def import_from_csv(self, players_file: str, external_ids_file: str, aliases_file: str):
        """Import database from CSV files"""
        try:
            # Import players
            players_df = pd.read_csv(players_file)
            for _, row in players_df.iterrows():
                self.add_player(
                    canonical_name=row['canonical_name'],
                    first_name=row.get('first_name'),
                    last_name=row.get('last_name'),
                    position=row.get('position'),
                    team=row.get('team'),
                    nfl_id=row.get('nfl_id')
                )
            
            # Import external IDs
            external_ids_df = pd.read_csv(external_ids_file)
            for _, row in external_ids_df.iterrows():
                self.add_external_id(
                    player_id=row['player_id'],
                    source_name=row['source_name'],
                    external_id=row['external_id'],
                    external_name=row.get('external_name'),
                    confidence_score=row.get('confidence_score', 1.0)
                )
            
            # Import aliases
            aliases_df = pd.read_csv(aliases_file)
            for _, row in aliases_df.iterrows():
                self.add_alias(
                    player_id=row['player_id'],
                    alias_name=row['alias_name'],
                    source_name=row.get('source_name'),
                    confidence_score=row.get('confidence_score', 1.0)
                )
            
            logger.info("Database imported from CSV files")
            
        except Exception as e:
            logger.error(f"Error importing database: {e}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def create_initial_database():
    """Create initial database with some common players"""
    db = CentralizedPlayerDatabase()
    
    # Add some high-profile players as examples
    players = [
        ("Patrick Mahomes", "Patrick", "Mahomes", "QB", "KC"),
        ("Christian McCaffrey", "Christian", "McCaffrey", "RB", "SF"),
        ("Tyreek Hill", "Tyreek", "Hill", "WR", "MIA"),
        ("Travis Kelce", "Travis", "Kelce", "TE", "KC"),
        ("Ja'Marr Chase", "Ja'Marr", "Chase", "WR", "CIN"),
        ("Bijan Robinson", "Bijan", "Robinson", "RB", "ATL"),
        ("Jahmyr Gibbs", "Jahmyr", "Gibbs", "RB", "DET"),
        ("Puka Nacua", "Puka", "Nacua", "WR", "LAR"),
        ("Nico Collins", "Nico", "Collins", "WR", "HOU"),
        ("Joe Burrow", "Joe", "Burrow", "QB", "CIN"),
    ]
    
    for canonical_name, first_name, last_name, position, team in players:
        player_id = db.add_player(canonical_name, first_name, last_name, position, team)
        
        # Add DraftKings aliases (these would come from your actual data)
        db.add_alias(player_id, canonical_name, "draftkings", 1.0)
        
        # Add NFL API aliases (abbreviated versions)
        if first_name and last_name:
            abbreviated = f"{first_name[0]}.{last_name}"
            db.add_alias(player_id, abbreviated, "nfl_api", 0.9)
    
    # Export to CSV for review
    db.export_to_csv()
    db.close()
    
    print("✅ Initial database created with sample players")
    print("📁 Check data/players_master.csv, external_ids.csv, and aliases.csv")

if __name__ == "__main__":
    create_initial_database()
