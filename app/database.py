
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "opspilot.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                error_log TEXT NOT NULL,
                category TEXT NOT NULL,
                likely_cause TEXT NOT NULL,
                recommended_steps TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
