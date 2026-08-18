import sqlite3
from datetime import datetime, timezone

DB_NAME = "calculator.db"


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            joined_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            blocked INTEGER DEFAULT 0
        )
    """)

    connection.commit()
    connection.close()


def save_user(user):
    now = datetime.now(timezone.utc).isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO users (
            user_id,
            username,
            first_name,
            joined_at,
            last_seen,
            blocked
        )
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_seen = excluded.last_seen
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        now,
        now
    ))

    connection.commit()
    connection.close()


def get_active_users():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id
        FROM users
        WHERE blocked = 0
    """)

    users = [row["user_id"] for row in cursor.fetchall()]

    connection.close()

    return users


def mark_user_blocked(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET blocked = 1
        WHERE user_id = ?
    """, (user_id,))

    connection.commit()
    connection.close()


def get_statistics():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM users")
    total = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE blocked = 0
    """)
    active = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE blocked = 1
    """)
    blocked = cursor.fetchone()["count"]

    connection.close()

    return total, active, blocked
    
