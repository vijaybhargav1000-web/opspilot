

import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Give each test its own temporary database.
    test_db = tmp_path / "test_opspilot.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_and_retrieve_incident(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": (
                "Spark executor failed: Java heap space "
                "due to out-of-memory."
            ),
        },
    )

    assert response.status_code == 200
    created = response.json()

    assert created["category"] == "MEMORY_ERROR"
    assert created["incident_id"] is not None

    incident_id = created["incident_id"]
    retrieved = client.get(f"/incidents/{incident_id}")

    assert retrieved.status_code == 200
    saved = retrieved.json()
    assert saved["incident_id"] == incident_id
    assert saved["service"] == "customer-etl"
    assert saved["category"] == "MEMORY_ERROR"
    assert saved["status"] == "OPEN"
    assert "created_at" in saved
    assert "error_log" not in saved


def test_missing_incident_returns_404(client):
    response = client.get("/incidents/999999")

    assert response.status_code == 404


def test_timeout_classification(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "orders-api",
            "error_log": "Database request timed out after 30 seconds",
        },
    )

    assert response.status_code == 200
    assert response.json()["category"] == "TIMEOUT"


def test_unknown_error_classification(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "Unexpected processing failure occurred",
        },
    )

    assert response.status_code == 200
    assert response.json()["category"] == "UNKNOWN"


def test_rejects_short_error_log(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "bad",
        },
    )

    assert response.status_code == 422
