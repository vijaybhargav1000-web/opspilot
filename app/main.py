
import json
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection, initialize_database
from app.ollama_client import explain_incident
from app.retrieval import retrieve_runbooks


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="OpsPilot",
    description="Production Incident Resolution Assistant",
    version="0.7.0",
    lifespan=lifespan,
)


class IncidentRequest(BaseModel):
    service: str = Field(min_length=1, max_length=100)
    error_log: str = Field(min_length=10, max_length=12000)


class RetrievedEvidence(BaseModel):
    source: str
    chunk_id: int
    score: float
    content: str


class IncidentReport(BaseModel):
    service: str
    category: str
    likely_cause: str
    ai_explanation: str | None = None
    recommended_steps: list[str]
    human_review_required: bool
    incident_id: int | None = None
    retrieved_evidence: list[RetrievedEvidence] = Field(
        default_factory=list
    )


def classify_incident(
    service: str,
    error_log: str,
) -> IncidentReport:
    log = error_log.lower()

    memory_terms = (
        "outofmemoryerror",
        "out of memory",
        "out-of-memory",
        "java heap space",
        "memoryerror",
        "executor lost",
    )

    timeout_terms = (
        "timeout",
        "timed out",
        "deadline exceeded",
        "read timed out",
        "connection timed out",
    )

    permission_terms = (
        "permission denied",
        "access denied",
        "unauthorized",
        "forbidden",
        "accessdenied",
    )

    if any(term in log for term in memory_terms):
        category = "MEMORY_ERROR"
        cause = (
            "The process may have exceeded available memory, "
            "encountered memory pressure, or lost a Spark executor."
        )
        steps = [
            "Inspect executor memory metrics and failed task logs.",
            "Check partition sizes, data skew, and recent data-volume changes.",
            "Review recent code and configuration changes before tuning memory.",
            "Validate any proposed change in a safe environment before rollout.",
        ]

    elif any(term in log for term in timeout_terms):
        category = "TIMEOUT"
        cause = (
            "A request or processing operation may have exceeded "
            "its time limit or waited too long for a dependency."
        )
        steps = [
            "Identify the component and dependency that timed out.",
            "Check service health, latency metrics, and dependency logs.",
            "Inspect connection pools, resource saturation, and recent changes.",
            "Retry only when the operation is safe and idempotent.",
        ]

    elif any(term in log for term in permission_terms):
        category = "PERMISSION_ERROR"
        cause = (
            "The service identity may lack permission to access "
            "a resource or perform the requested operation."
        )
        steps = [
            "Identify the exact resource and denied operation.",
            "Check the service identity, role, policy, and resource policy.",
            "Request only the minimum permissions required.",
            "Never bypass access controls or expose credentials in logs.",
        ]

    else:
        category = "UNKNOWN"
        cause = "The available log does not match a known classification rule."
        steps = [
            "Collect surrounding logs, the full traceback, and a request identifier.",
            "Check recent deployments, configuration changes, and dependency health.",
            "Compare the failure with known incidents and runbooks.",
            "Escalate for human investigation if the cause remains unclear.",
        ]

    return IncidentReport(
        service=service,
        category=category,
        likely_cause=cause,
        recommended_steps=steps,
        human_review_required=True,
    )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "OpsPilot",
    }


@app.post("/incidents/analyze", response_model=IncidentReport)
def analyze_incident(incident: IncidentRequest):
    report = classify_incident(
        incident.service,
        incident.error_log,
    )

    # Retrieve runbook evidence. Retrieval failures should not prevent
    # deterministic incident analysis.
    try:
        raw_evidence = retrieve_runbooks(
            f"{report.category} {incident.service} {incident.error_log}",
            top_k=3,
        )
        evidence = [
            RetrievedEvidence.model_validate(item)
            for item in raw_evidence
        ]
    except OSError:
        logger.warning(
            "Runbook retrieval failed due to an OS-level error",
            exc_info=True,
        )
        evidence = []

    report = report.model_copy(
        update={"retrieved_evidence": evidence}
    )

    # Save the deterministic incident first so the incident is retained
    # even if Ollama is unavailable.
    try:
        with get_connection() as connection:
            cursor = connection.execute(
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
                    report.service,
                    incident.error_log,
                    report.category,
                    report.likely_cause,
                    json.dumps(report.recommended_steps),
                ),
            )
            incident_id = cursor.lastrowid

    except sqlite3.Error:
        logger.exception("Failed to persist incident to the database")
        raise HTTPException(
            status_code=500,
            detail="Unable to save incident. Please retry later.",
        ) from None

    except RuntimeError:
        logger.exception("Unexpected failure while saving incident")
        raise HTTPException(
            status_code=500,
            detail="Unable to save incident. Please retry later.",
        ) from None

    # Generate an optional explanation using local Ollama.
    # The helper returns None when Ollama is unavailable.
    ai_explanation = explain_incident(
        category=report.category,
        service=report.service,
        likely_cause=report.likely_cause,
        recommended_steps=report.recommended_steps,
        evidence=[
            item.model_dump()
            for item in report.retrieved_evidence
        ],
    )

    # Persist the explanation separately. Failure to save this optional
    # field should not discard the incident or its deterministic report.
    if ai_explanation is not None:
        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    UPDATE incidents
                    SET ai_explanation = ?
                    WHERE incident_id = ?
                    """,
                    (ai_explanation, incident_id),
                )
        except sqlite3.Error:
            logger.exception(
                "Failed to persist AI explanation for incident %s",
                incident_id,
            )
            ai_explanation = None

    return report.model_copy(
        update={
            "incident_id": incident_id,
            "ai_explanation": ai_explanation,
            "human_review_required": True,
        }
    )


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM incidents
                WHERE incident_id = ?
                """,
                (incident_id,),
            ).fetchone()

    except sqlite3.Error:
        logger.exception("Failed to retrieve incident from the database")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve incident. Please retry later.",
        ) from None

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    incident = dict(row)
    incident["recommended_steps"] = json.loads(
        incident["recommended_steps"]
    )
    incident.pop("error_log", None)

    return incident
