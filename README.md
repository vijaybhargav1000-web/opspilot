# OpsPilot — AI-Powered Production Incident Assistant

OpsPilot is a local-first incident-support application that classifies operational errors, retrieves relevant troubleshooting runbooks, generates evidence-grounded explanations using a local large language model (LLM), and stores incident reports for later retrieval.

The project demonstrates practical concepts in **FastAPI, Python, SQLite, retrieval-augmented generation (RAG), semantic search, local LLM integration, automated testing, and incident troubleshooting**.

> **Project status:** Working local prototype with a verified end-to-end incident flow and automated tests. It is not yet a fully production-hardened incident management platform.

## Key Features

- **Incident analysis API:** Accepts service names and error logs and classifies known incident patterns.
- **Runbook retrieval:** Retrieves relevant Markdown troubleshooting guidance using keyword-based ranking.
- **Semantic retrieval:** Uses sentence embeddings to find semantically relevant runbook content.
- **Local LLM integration:** Uses Ollama to generate incident explanations without requiring a paid hosted LLM API.
- **Evidence-aware explanations:** Supplies retrieved runbook evidence and incident details to the LLM.
- **Persistent incident history:** Stores incident reports and AI explanations in SQLite.
- **Graceful AI fallback:** Preserves rule-based incident analysis when AI generation is unavailable.
- **Human-review safeguard:** Marks incident recommendations as requiring human review.
- **Automated tests:** Covers API behavior, database operations, retrieval, ranking, and failure handling.

## Architecture

```text
                    User / API Client
                           |
                           v
                     FastAPI API
                           |
                           v
                   Incident Classifier
                           |
                           v
                   Runbook Retrieval
                    /            \
                   v              v
             Keyword Search   Semantic Search
                    \            /
                     v          v
                  Retrieved Evidence
                           |
                           v
                    Local Ollama LLM
                           |
                           v
                  Incident Explanation
                           |
                           v
                      SQLite DB
                           |
                           v
                 Incident Report Response
```

The application uses deterministic rules for initial classification. Retrieved runbook evidence provides troubleshooting context for the local LLM. The LLM's explanation is advisory; it does not independently authorize production changes.

## Technology Stack

| Area | Technology |
|---|---|
| API | Python, FastAPI |
| Request validation | Pydantic |
| Database | SQLite |
| Retrieval | Keyword matching and semantic embeddings |
| Embedding model | `all-MiniLM-L6-v2` via Sentence Transformers |
| Local LLM | Ollama with `llama3.2:3b` |
| HTTP integration | Requests |
| Testing | Pytest |
| Development | Git and GitHub |

## Project Structure

```text
OpsPilot/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── retrieval.py
│   ├── semantic_retrieval.py
│   └── ollama_client.py
├── runbooks/
│   ├── spark_memory.md
│   ├── api_timeout.md
│   └── permission_error.md
├── tests/
│   ├── test_database.py
│   ├── test_incident.py
│   ├── test_retrieval.py
│   └── test_semantic_retrieval.py
├── scripts/
│   └── compare_retrieval.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python installed
- Git
- Ollama installed locally
- The `llama3.2:3b` model downloaded through Ollama

The semantic retrieval component may download its embedding model the first time it runs. Internet access may be required for that initial download.

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/vijaybhargav1000-web/opspilot.git
cd OpsPilot
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start Ollama

Download the model if it is not already installed:

```powershell
ollama pull llama3.2:3b
```

Ensure Ollama is running and the model is available:

```powershell
ollama list
```

### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload --port 8001
```

Open the interactive API documentation at:

`http://127.0.0.1:8001/docs`

Check the health endpoint at:

`http://127.0.0.1:8001/health`

## Example: Analyze an Incident

Send a `POST` request to `/incidents/analyze` with a JSON body such as:

```json
{
  "service": "payment-api",
  "error_log": "ERROR: OutOfMemoryError while processing payment requests. Worker memory usage exceeded available capacity."
}
```

PowerShell example:

```powershell
$body = @{
    service = "payment-api"
    error_log = "ERROR: OutOfMemoryError while processing payment requests. Worker memory usage exceeded available capacity."
} | ConvertTo-Json

$result = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8001/incidents/analyze" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$result | ConvertTo-Json -Depth 8
```

The response includes the incident classification, likely cause, recommended diagnostic steps, human-review requirement, incident ID, retrieved evidence, and AI explanation when available.

### Retrieve a Saved Incident

Use the ID returned by the analysis endpoint:

```powershell
$id = $result.incident_id

Invoke-RestMethod "http://127.0.0.1:8001/incidents/$id" |
    ConvertTo-Json -Depth 8
```

## Run Tests

Run the full test suite from the repository root:

```powershell
python -m pytest -v
```

The current development suite has **38 passing tests**. Run the tests again after making changes to verify the current checkout.

## Retrieval Evaluation

The project includes a small labelled query set for comparing retrieval behavior with metrics such as:

- **Hit@K:** Whether at least one relevant source appears in the top K results.
- **Recall@K:** The fraction of relevant sources retrieved in the top K results.
- **Mean Reciprocal Rank (MRR):** How highly the first relevant result is ranked.

The evaluation set is small and intended for development. Its results should not be interpreted as proof of performance on real-world production traffic.

## Reliability and Safety

- AI explanations are advisory and may be unavailable if the local model is stopped or a request times out.
- Rule-based incident classification is separate from the LLM-generated explanation.
- Retrieved evidence provides context but does not guarantee that a diagnosis is correct.
- Incident recommendations require human review before production changes.
- Logs and runbook content should be treated as untrusted input.
- Production deployment would require further validation of authentication, authorization, sensitive-data handling, observability, concurrency, resource limits, and recovery procedures.

## Current Limitations

- Classification rules cover a limited set of incident patterns.
- The runbook collection is small.
- Retrieval quality needs evaluation against a larger, representative dataset.
- SQLite is suitable for this local prototype but may not be the appropriate database for a larger multi-user deployment.
- The local LLM's latency and output quality depend on available hardware and model behavior.
- Docker deployment, cloud hosting, and production operational controls have not been established as part of the current verified workflow.

## Future Improvements

- Expand runbooks and incident categories.
- Improve retrieval relevance and reduce unrelated evidence.
- Add structured output validation and stronger evaluation for LLM responses.
- Introduce authentication, role-based access, audit logging, and sensitive-log redaction.
- Add metrics, tracing, health monitoring, and controlled retries.
- Add containerized deployment after checking local hardware constraints.
- Evaluate against a larger labelled incident dataset.

