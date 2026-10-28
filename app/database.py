
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "opspilot.db"


def get_connection(db_path: Path | str | None = None):
    """Open a SQLite connection, optionally using a specific database path."""
    path = Path(db_path) if db_path is not None else DB_PATH

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path | str | None = None):
    """Create the incidents table and safely migrate existing databases."""
    with get_connection(db_path) as connection:
        connection.execute(
            """
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
            """
        )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(incidents)"
            ).fetchall()
        }

        if "ai_explanation" not in columns:
            connection.execute(
                "ALTER TABLE incidents ADD COLUMN ai_explanation TEXT"
            )
