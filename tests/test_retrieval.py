

import pytest

import app.retrieval as retrieval


def test_loads_runbooks_and_preserves_source(monkeypatch, tmp_path):
    (tmp_path / "spark_memory.md").write_text(
        "# Spark Memory\nInvestigate executor memory and data skew.",
        encoding="utf-8",
    )
    monkeypatch.setattr(retrieval, "RUNBOOKS_DIR", tmp_path)

    documents = retrieval.load_runbooks()

    assert len(documents) == 1
    assert documents[0]["source"] == "spark_memory.md"


def test_retrieves_relevant_runbook(monkeypatch, tmp_path):
    (tmp_path / "spark_memory.md").write_text(
        "Spark executor memory out of memory data skew partitions",
        encoding="utf-8",
    )
    (tmp_path / "api_timeout.md").write_text(
        "API request latency timeout downstream service",
        encoding="utf-8",
    )
    monkeypatch.setattr(retrieval, "RUNBOOKS_DIR", tmp_path)

    results = retrieval.retrieve_runbooks(
        "Spark executor memory failure",
        top_k=2,
    )

    assert results
    assert results[0]["source"] == "spark_memory.md"
    assert results[0]["score"] > 0


def test_returns_empty_for_unmatched_query(monkeypatch, tmp_path):
    (tmp_path / "api_timeout.md").write_text(
        "API latency timeout downstream service",
        encoding="utf-8",
    )
    monkeypatch.setattr(retrieval, "RUNBOOKS_DIR", tmp_path)

    assert retrieval.retrieve_runbooks(
        "volcano astronomy telescope",
    ) == []


def test_rejects_invalid_chunk_settings():
    with pytest.raises(ValueError):
        retrieval.chunk_text("some words", chunk_size=10, overlap=10)


def test_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        retrieval.retrieve_runbooks("memory", top_k=0)


@pytest.mark.parametrize(
    ("query", "expected_source"),
    [
        (
            "MEMORY_ERROR Spark OutOfMemoryError executor memory",
            "spark_memory.md",
        ),
        (
            "TIMEOUT API request timed out latency",
            "api_timeout.md",
        ),
        (
            "PERMISSION_ERROR permission denied access denied",
            "permission_error.md",
        ),
    ],
)
def test_expected_runbook_ranks_first(
    monkeypatch,
    tmp_path,
    query,
    expected_source,
):
    runbooks = {
        "spark_memory.md": (
            "MEMORY_ERROR Spark OutOfMemoryError executor memory "
            "Java heap space data skew partitions"
        ),
        "api_timeout.md": (
            "TIMEOUT API request timed out latency "
            "deadline exceeded downstream service"
        ),
        "permission_error.md": (
            "PERMISSION_ERROR permission denied access denied "
            "unauthorized forbidden resource policy"
        ),
    }

    for filename, content in runbooks.items():
        (tmp_path / filename).write_text(content, encoding="utf-8")

    monkeypatch.setattr(retrieval, "RUNBOOKS_DIR", tmp_path)

    results = retrieval.retrieve_runbooks(query, top_k=3)

    assert results
    assert results[0]["source"] == expected_source


def recall_at_k(results, relevant_sources, k):
    """Fraction of relevant source documents retrieved in the top k."""
    if not relevant_sources:
        raise ValueError("relevant_sources must not be empty")

    retrieved_sources = {
        item["source"] for item in results[:k]
    }

    return len(retrieved_sources & relevant_sources) / len(relevant_sources)


def hit_rate_at_k(results, relevant_sources, k):
    """Return 1 if any relevant source appears in the top k; otherwise 0."""
    if not relevant_sources:
        raise ValueError("relevant_sources must not be empty")

    retrieved_sources = {
        item["source"] for item in results[:k]
    }

    return float(bool(retrieved_sources & relevant_sources))


def test_retrieval_metrics():
    results = [
        {"source": "spark_memory.md", "score": 0.9},
        {"source": "api_timeout.md", "score": 0.5},
    ]

    relevant_sources = {"spark_memory.md"}

    assert recall_at_k(results, relevant_sources, 1) == 1.0
    assert hit_rate_at_k(results, relevant_sources, 1) == 1.0
    assert recall_at_k(results, {"permission_error.md"}, 2) == 0.0
    assert hit_rate_at_k(results, {"permission_error.md"}, 2) == 0.0


def test_metrics_reject_empty_relevant_sources():
    with pytest.raises(ValueError):
        recall_at_k([], set(), 3)

    with pytest.raises(ValueError):
        hit_rate_at_k([], set(), 3)
