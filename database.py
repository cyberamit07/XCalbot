import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class Database:
    """Database manager for XCalbot"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database tables"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language_code TEXT,
                        is_bot INTEGER DEFAULT 0,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        blocked INTEGER DEFAULT 0,
                        total_expressions INTEGER DEFAULT 0
                    )
                ''')
                
                # Create indexes
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def update_user(self, user_data: Dict) -> None:
        """Update or create user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute(
                    'SELECT user_id FROM users WHERE user_id = ?',
                    (user_data['user_id'],)
                )
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing user
                    cursor.execute('''
                        UPDATE users SET
                            username = ?,
                            first_name = ?,
                            last_name = ?,
                            language_code = ?,
                            is_bot = ?,
                            last_seen = CURRENT_TIMESTAMP,
                            total_expressions = total_expressions + 1
                        WHERE user_id = ?
                    ''', (
                        user_data.get('username', ''),
                        user_data.get('first_name', ''),
                        user_data.get('last_name', ''),
                        user_data.get('language_code', ''),
                        1 if user_data.get('is_bot', False) else 0,
                        user_data['user_id']
                    ))
                else:
                    # Insert new user
                    cursor.execute('''
                        INSERT INTO users (
                            user_id, username, first_name, last_name,
                            language_code, is_bot, joined_at, last_seen
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (
                        user_data['user_id'],
                        user_data.get('username', ''),
                        user_data.get('first_name', ''),
                        user_data.get('last_name', ''),
                        user_data.get('language_code', ''),
                        1 if user_data.get('is_bot', False) else 0
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update user {user_data.get('user_id')}: {e}")
    
    def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        """Set user blocked status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET blocked = ? WHERE user_id = ?',
                    (1 if blocked else 0, user_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to set blocked status for {user_id}: {e}")
    
    def get_active_users(self) -> List[Dict]:
        """Get non-blocked users"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name
                    FROM users
                    WHERE blocked = 0
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return []
    
    def get_users(self, limit: int = 100) -> List[Dict]:
        """Get users"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, joined_at, last_seen, blocked
                    FROM users
                    ORDER BY joined_at DESC
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Get user statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total users
                cursor.execute('SELECT COUNT(*) FROM users')
                total = cursor.fetchone()[0]
                
                # Blocked users
                cursor.execute('SELECT COUNT(*) FROM users WHERE blocked = 1')
                blocked = cursor.fetchone()[0]
                
                # Active users (not blocked)
                active = total - blocked
                
                # Active today
                today = datetime.now().date()
                today_start = datetime.combine(today, datetime.min.time())
                cursor.execute(
                    'SELECT COUNT(*) FROM users WHERE last_seen >= ?',
                    (today_start,)
                )
                active_today = cursor.fetchone()[0]
                
                # Joined today
                cursor.execute(
                    'SELECT COUNT(*) FROM users WHERE joined_at >= ?',
                    (today_start,)
                )
                joined_today = cursor.fetchone()[0]
                
                return {
                    'total': total,
                    'blocked': blocked,
                    'active': active,
                    'active_today': active_today,
                    'joined_today': joined_today
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total': 0,
                'blocked': 0,
                'active': 0,
                'active_today': 0,
                'joined_today': 0
            }
    
    def close(self) -> None:
        """Close database connection"""
        # SQLite connections are closed automatically with context managers
        pass
