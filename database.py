import sqlite3
from datetime import datetime

DB_NAME = "calculator.db"


def connect():
    return sqlite3.connect(DB_NAME)


def init_db():
    db = connect()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            last_seen TEXT,
            is_blocked INTEGER DEFAULT 0
        )
    """)

    db.commit()
    db.close()


def add_user(user_id, username, first_name):
    now = datetime.now().isoformat()

    db = connect()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO users
        (user_id, username, first_name, joined_at, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_seen=excluded.last_seen
    """, (
        user_id,
        username,
        first_name,
        now,
        now
    ))

    db.commit()
    db.close()


def get_all_users():
    db = connect()
    cur = db.cursor()

    cur.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    users = [row[0] for row in cur.fetchall()]

    db.close()
    return users


def mark_blocked(user_id):
    db = connect()
    cur = db.cursor()

    cur.execute(
        "UPDATE users SET is_blocked = 1 WHERE user_id = ?",
        (user_id,)
    )

    db.commit()
    db.close()


def get_stats():
    db = connect()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    blocked = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0")
    active = cur.fetchone()[0]

    db.close()

    return total, active, blocked
