
import sqlite3

import pytest

from app.database import initialize_database, get_connection


def test_initialize_database_creates_incidents_table(tmp_path):
    db_path = tmp_path / "test_opspilot.db"

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'incidents'
            """
        ).fetchone()

        columns = {
            item["name"]
            for item in connection.execute(
                "PRAGMA table_info(incidents)"
            ).fetchall()
        }

    assert row is not None
    assert row["name"] == "incidents"
    assert "ai_explanation" in columns


def test_initialize_database_is_idempotent(tmp_path):
    db_path = tmp_path / "test_opspilot.db"

    initialize_database(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO incidents (
                service,
                error_log,
                category,
                likely_cause,
                recommended_steps
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "orders-api",
                "Request timed out after 30 seconds",
                "TIMEOUT",
                "Dependency may be slow",
                '["Check dependency health"]',
            ),
        )

    # Initializing again must not delete existing records.
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT service, category, ai_explanation FROM incidents"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["service"] == "orders-api"
    assert rows[0]["category"] == "TIMEOUT"
    assert rows[0]["ai_explanation"] is None


def test_initialize_database_migrates_existing_database(tmp_path):
    db_path = tmp_path / "existing_opspilot.db"

    # Simulate a database created by the older version of OpsPilot.
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE incidents (
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
        connection.execute(
            """
            INSERT INTO incidents (
                service, error_log, category,
                likely_cause, recommended_steps
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Spark",
                "Java heap space",
                "MEMORY_ERROR",
                "Memory pressure",
                '["Inspect executor metrics"]',
            ),
        )

    # Migration should add the new column without deleting the old row.
    initialize_database(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT service, category, ai_explanation
            FROM incidents
            """
        ).fetchone()

    assert row["service"] == "Spark"
    assert row["category"] == "MEMORY_ERROR"
    assert row["ai_explanation"] is None


def test_get_connection_surfaces_invalid_database_path(tmp_path):
    invalid_path = tmp_path / "missing_directory" / "test.db"

    with pytest.raises(sqlite3.OperationalError):
        get_connection(invalid_path)
