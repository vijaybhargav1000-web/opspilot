# OpsPilot — AI-Powered Incident Resolution Assistant

OpsPilot is a developer-focused project that analyzes application and data-pipeline errors, classifies incidents, recommends troubleshooting steps, and stores incident records for later investigation.

The project is being developed incrementally, starting with a local API and rule-based classification, with retrieval-augmented generation (RAG) and LLM-assisted analysis planned as future capabilities.

## Problem Statement

When a production service fails, engineers need to identify the likely cause, find relevant troubleshooting guidance, and respond consistently.

OpsPilot aims to streamline this workflow by providing a structured incident-analysis API and a foundation for evidence-grounded troubleshooting assistance.

## Current Features

- **REST API:** Built with FastAPI.
- **Incident classification:** Rule-based detection of memory errors, timeouts, permission errors, and unknown errors.
- **Incident persistence:** Stores incident details and recommendations in SQLite.
- **Incident retrieval:** Retrieves saved incidents by ID.
- **Input validation:** Uses Pydantic models to validate requests.
- **Automated tests:** Uses pytest and FastAPI's test client to validate core behavior.
- **Interactive API documentation:** Available through Swagger UI.

## Architecture

```text
Client / API Consumer
        |
        v
    FastAPI API
        |
        v
 Request Validation
      (Pydantic)
        |
        v
 Incident Classifier
    (Rule-Based)
        |
        v
 Recommendation Logic
        |
        v
 SQLite Database
        |
        v
 Incident Response
```

### Current Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| Request validation | Pydantic |
| Database | SQLite |
| Testing | pytest |
| API documentation | Swagger UI |
| Version control | Git and GitHub |

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check application health |
| POST | `/incidents/analyze` | Analyze an error and create an incident record |
| GET | `/incidents/{incident_id}` | Retrieve a previously saved incident |

### Example: Analyze an Incident

Request:

```json
{
  "service": "customer-etl",
  "error_log": "Executor lost due to java.lang.OutOfMemoryError"
}
```

Example response structure:

```json
{
  "service": "customer-etl",
  "category": "MEMORY_ERROR",
  "likely_cause": "The Spark process may have exceeded available memory.",
  "recommended_steps": [
    "Inspect executor memory usage and Spark UI metrics.",
    "Check for data skew and oversized partitions.",
    "Review join strategies and unnecessary data caching."
  ],
  "human_review_required": true,
  "incident_id": 1
}
```

The response is illustrative. Actual recommendation text depends on the current application implementation.

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/vijaybhargav1000-web/opspilot.git
cd opspilot
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the API

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 5. Open the API documentation

- Swagger UI: http://127.0.0.1:8001/docs
- Health check: http://127.0.0.1:8001/health

Keep the terminal running while testing the API.

## Run Tests

In a separate terminal, activate the virtual environment and run:

```powershell
python -m pytest -v
```

The initial test suite covers health checks, incident creation and retrieval, missing incident IDs, classification behavior, and input validation.

## Roadmap

The following capabilities are planned, not yet claimed as implemented:

- Local runbook ingestion and document parsing.
- Retrieval-augmented generation (RAG) for troubleshooting guidance.
- Hybrid retrieval and reranking where appropriate.
- LLM-assisted incident explanations grounded in retrieved evidence.
- Source citations and confidence-aware responses.
- Structured logging, improved error handling, and observability.
- Evaluation tests for retrieval quality and answer correctness.
- Containerization and CI automation.
- Optional cloud deployment when appropriate.

## Design Principles

- **Evidence before recommendations:** Future AI-generated guidance should be grounded in relevant runbooks and logs.
- **Human oversight:** Recommendations should be reviewed before executing potentially risky remediation actions.
- **Safe defaults:** Do not automatically execute destructive production operations.
- **Testability:** Core API behavior should be covered by automated tests.
- **Incremental engineering:** Clearly distinguish implemented capabilities from planned improvements.

## Project Status

**Stage 1 — Local API foundation**

The current implementation provides a rule-based incident-analysis API, SQLite persistence, incident retrieval, and automated tests.

RAG, external LLM integration, production deployment, and production-scale reliability have not yet been established.

## License

No license has been selected yet. All rights and reuse permissions remain subject to the repository owner's rights until a license is added.
