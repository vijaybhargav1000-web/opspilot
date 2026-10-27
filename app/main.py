
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection, initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="OpsPilot",
    description="Production Incident Resolution Assistant",
    version="0.3.0",
    lifespan=lifespan,
)


class IncidentRequest(BaseModel):
    service: str = Field(min_length=1, max_length=100)
    error_log: str = Field(min_length=10, max_length=12000)


class IncidentReport(BaseModel):
    service: str
    category: str
    likely_cause: str
    recommended_steps: list[str]
    human_review_required: bool
    incident_id: int | None = None


def classify_incident(
    service: str,
    error_log: str,
) -> IncidentReport:
    log = error_log.lower()

    if "out of memory" in log or "java heap space" in log:
        category = "MEMORY_ERROR"
        cause = (
            "The Spark process may have exceeded "
            "available memory."
        )
        steps = [
            "Inspect executor memory usage and failed task logs.",
            "Check partition sizes and possible data skew.",
            "Review recent changes before adjusting memory settings.",
        ]

    elif "timeout" in log or "timed out" in log:
        category = "TIMEOUT"
        cause = (
            "A request or processing operation exceeded "
            "its time limit."
        )
        steps = [
            "Identify the component that timed out.",
            "Check service health, latency, and dependency logs.",
            "Retry only if the operation is safe and idempotent.",
        ]

    elif "permission denied" in log or "access denied" in log:
        category = "PERMISSION_ERROR"
        cause = (
            "The service may lack permission to access a resource."
        )
        steps = [
            "Identify the exact resource and denied operation.",
            "Check the service identity and applicable permissions.",
            "Request the minimum required permission; "
            "do not bypass access controls.",
        ]

    else:
        category = "UNKNOWN"
        cause = (
            "The available log does not match a known rule."
        )
        steps = [
            "Collect surrounding logs and the full error traceback.",
            "Check recent deployments and dependency health.",
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

    # Avoid returning the raw error log from this endpoint.
    incident.pop("error_log", None)

    return incident
