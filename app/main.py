
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection, initialize_database
from app.retrieval import retrieve_runbooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="OpsPilot",
    description="Production Incident Resolution Assistant",
    version="0.5.0",
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

    # Memory-related failures, including common JVM and Spark messages.
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

    # Retrieval is supplemental. A missing or unreadable runbook
    # must not prevent basic incident analysis.
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
        evidence = []

    report = report.model_copy(
        update={"retrieved_evidence": evidence}
    )

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

    return report.model_copy(
        update={"incident_id": incident_id}
    )


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

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
