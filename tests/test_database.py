
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

    assert row is not None
    assert row["name"] == "incidents"


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
            "SELECT service, category FROM incidents"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["service"] == "orders-api"
    assert rows[0]["category"] == "TIMEOUT"


def test_get_connection_surfaces_invalid_database_path(tmp_path):
    invalid_path = tmp_path / "missing_directory" / "test.db"

    with pytest.raises(sqlite3.OperationalError):
        get_connection(invalid_path)
