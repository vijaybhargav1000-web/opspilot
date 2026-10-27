
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
    import pytest

    with pytest.raises(ValueError):
        retrieval.chunk_text("some words", chunk_size=10, overlap=10)


def test_rejects_invalid_top_k():
    import pytest

    with pytest.raises(ValueError):
        retrieval.retrieve_runbooks("memory", top_k=0)
