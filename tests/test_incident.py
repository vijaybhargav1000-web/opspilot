
import pytest
from fastapi.testclient import TestClient

import app.database as database
import app.main as main
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Give each test its own temporary database.
    test_db = tmp_path / "test_opspilot.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)

    # Keep normal API tests fast and deterministic.
    # AI-specific tests can override this mock when needed.
    monkeypatch.setattr(
        main,
        "explain_incident",
        lambda **kwargs: None,
    )

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
    assert "retrieved_evidence" in created

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


def test_analyze_returns_retrieved_evidence(monkeypatch, client):
    monkeypatch.setattr(
        main,
        "retrieve_runbooks",
        lambda query, top_k=3: [
            {
                "source": "spark_memory.md",
                "chunk_id": 0,
                "score": 0.75,
                "content": "Inspect executor memory and data skew.",
            }
        ],
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "Executor failed with OutOfMemoryError",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_evidence"][0]["source"] == "spark_memory.md"
    assert body["retrieved_evidence"][0]["score"] == 0.75


def test_analyze_continues_when_runbook_directory_is_unavailable(
    monkeypatch, client
):
    def unavailable_retriever(query, top_k=3):
        raise OSError("Runbook storage unavailable")

    monkeypatch.setattr(
        main,
        "retrieve_runbooks",
        unavailable_retriever,
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "Executor failed with OutOfMemoryError",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "MEMORY_ERROR"
    assert body["retrieved_evidence"] == []


def test_analyze_returns_500_when_database_write_fails(monkeypatch, client):
    class FailingConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, *args, **kwargs):
            raise RuntimeError("simulated database failure")

    monkeypatch.setattr(
        main,
        "get_connection",
        lambda: FailingConnection(),
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "orders-api",
            "error_log": "Database request timed out after 30 seconds",
        },
    )

    assert response.status_code == 500
    assert "simulated database failure" not in response.text


def test_rejects_empty_service(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "",
            "error_log": "Request timed out while calling database",
        },
    )

    assert response.status_code == 422


def test_rejects_error_log_over_maximum_length(client):
    response = client.post(
        "/incidents/analyze",
        json={
            "service": "orders-api",
            "error_log": "x" * 12001,
        },
    )

    assert response.status_code == 422


def test_ai_explanation_is_persisted_and_retrievable(
    monkeypatch, client
):
    monkeypatch.setattr(
        main,
        "explain_incident",
        lambda **kwargs: (
            "The Spark job may have exceeded executor memory. "
            "Check partition sizes and data skew."
        ),
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "Spark executor failed with Java heap space",
        },
    )

    assert response.status_code == 200
    created = response.json()
    incident_id = created["incident_id"]

    assert created["ai_explanation"] is not None
    assert "executor memory" in created["ai_explanation"]
    assert created["human_review_required"] is True

    retrieved = client.get(f"/incidents/{incident_id}")

    assert retrieved.status_code == 200
    saved = retrieved.json()
    assert saved["ai_explanation"] == created["ai_explanation"]


def test_ollama_unavailable_preserves_rule_based_report(
    monkeypatch, client
):
    monkeypatch.setattr(
        main,
        "explain_incident",
        lambda **kwargs: None,
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "orders-api",
            "error_log": "Database request timed out after 30 seconds",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["category"] == "TIMEOUT"
    assert body["ai_explanation"] is None
    assert body["recommended_steps"]
    assert body["human_review_required"] is True

    incident_id = body["incident_id"]
    retrieved = client.get(f"/incidents/{incident_id}")

    assert retrieved.status_code == 200
    assert retrieved.json()["ai_explanation"] is None


def test_empty_ai_explanation_is_not_persisted(
    monkeypatch, client
):
    monkeypatch.setattr(
        main,
        "explain_incident",
        lambda **kwargs: None,
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": "Unexpected processing failure occurred",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["category"] == "UNKNOWN"
    assert body["ai_explanation"] is None

    retrieved = client.get(
        f"/incidents/{body['incident_id']}"
    )

    assert retrieved.status_code == 200
    assert retrieved.json()["ai_explanation"] is None

def test_ai_explanation_uses_clear_incident_sections(monkeypatch, client):
    import app.main as main

    expected_explanation = (
        "Assessment:\n"
        "The memory error is confirmed, but the root cause is not.\n\n"
        "Next checks:\n"
        "Inspect executor logs and partition sizes.\n\n"
        "Safety:\n"
        "Human review is required before remediation."
    )

    monkeypatch.setattr(
        main,
        "explain_incident",
        lambda **kwargs: expected_explanation,
    )

    response = client.post(
        "/incidents/analyze",
        json={
            "service": "customer-etl",
            "error_log": (
                "Spark executor failed with Java heap space"
            ),
        },
    )

    assert response.status_code == 200
    explanation = response.json()["ai_explanation"]

    assert explanation is not None
    assert "Assessment:" in explanation
    assert "Next checks:" in explanation
    assert "Safety:" in explanation
    assert response.json()["human_review_required"] is True
