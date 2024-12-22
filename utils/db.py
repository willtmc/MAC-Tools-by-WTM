"""Database utilities for tracking application state."""
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class Database:
    """SQLite database manager."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Optional path to database file. If None, uses default path.
        """
        if not db_path:
            # Use data directory in project root
            root_dir = Path(os.path.dirname(os.path.dirname(__file__)))
            data_dir = root_dir / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'app.db')
            
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create letters_sent table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS letters_sent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auction_code TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    creative_id TEXT NOT NULL,
                    num_addresses INTEGER NOT NULL,
                    campaign_name TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    error TEXT
                )
            ''')
            
            conn.commit()
    
    def log_letter_send(self, 
                       auction_code: str,
                       campaign_id: str,
                       creative_id: str,
                       num_addresses: int,
                       campaign_name: Optional[str] = None,
                       status: str = 'pending',
                       error: Optional[str] = None) -> int:
        """
        Log a letter send event.
        
        Args:
            auction_code: Auction identifier
            campaign_id: Lob campaign ID
            creative_id: Lob creative ID
            num_addresses: Number of addresses in campaign
            campaign_name: Optional campaign name
            status: Current status (default: 'pending')
            error: Optional error message
            
        Returns:
            int: ID of the new record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO letters_sent (
                    auction_code,
                    campaign_id,
                    creative_id,
                    num_addresses,
                    campaign_name,
                    status,
                    error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                auction_code,
                campaign_id,
                creative_id,
                num_addresses,
                campaign_name,
                status,
                error
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_send_status(self, campaign_id: str, status: str, error: Optional[str] = None):
        """
        Update status of a letter send.
        
        Args:
            campaign_id: Lob campaign ID
            status: New status
            error: Optional error message
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE letters_sent
                SET status = ?, error = ?, sent_at = CURRENT_TIMESTAMP
                WHERE campaign_id = ?
            ''', (status, error, campaign_id))
            
            conn.commit()
    
    def get_send_history(self, auction_code: Optional[str] = None) -> List[Dict]:
        """
        Get history of letter sends.
        
        Args:
            auction_code: Optional auction code to filter by
            
        Returns:
            List[Dict]: List of send records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if auction_code:
                cursor.execute('''
                    SELECT * FROM letters_sent
                    WHERE auction_code = ?
                    ORDER BY sent_at DESC
                ''', (auction_code,))
            else:
                cursor.execute('''
                    SELECT * FROM letters_sent
                    ORDER BY sent_at DESC
                ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_send_stats(self) -> Dict:
        """
        Get statistics about letter sends.
        
        Returns:
            Dict: Statistics about letter sends
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_campaigns,
                    SUM(num_addresses) as total_letters,
                    COUNT(DISTINCT auction_code) as unique_auctions,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_campaigns,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_campaigns
                FROM letters_sent
            ''')
            
            stats = dict(cursor.fetchone())
            
            # Get recent activity
            cursor.execute('''
                SELECT auction_code, campaign_name, sent_at, status
                FROM letters_sent
                ORDER BY sent_at DESC
                LIMIT 5
            ''')
            
            stats['recent_activity'] = [dict(row) for row in cursor.fetchall()]
            
            return stats
