
import pytest

import app.semantic_retrieval as semantic


class FakeModel:
    def encode(
        self,
        texts,
        convert_to_tensor=True,
        normalize_embeddings=True,
    ):
        import torch

        # Simple deterministic embeddings for unit tests.
        if isinstance(texts, str):
            texts = [texts]

        vectors = []
        for text in texts:
            lower = text.lower()
            if "memory" in lower or "outofmemory" in lower:
                vectors.append([1.0, 0.0, 0.0])
            elif "timeout" in lower or "latency" in lower:
                vectors.append([0.0, 1.0, 0.0])
            elif "permission" in lower or "access denied" in lower:
                vectors.append([0.0, 0.0, 1.0])
            else:
                vectors.append([0.5, 0.5, 0.0])

        tensor = torch.tensor(vectors, dtype=torch.float32)
        return torch.nn.functional.normalize(tensor, p=2, dim=1)


def test_semantic_retrieval_ranks_relevant_runbook(monkeypatch, tmp_path):
    (tmp_path / "spark_memory.md").write_text(
        "Spark executor OutOfMemoryError memory failure",
        encoding="utf-8",
    )
    (tmp_path / "api_timeout.md").write_text(
        "API timeout and latency",
        encoding="utf-8",
    )

    monkeypatch.setattr(semantic, "load_runbooks", lambda: [
        {"source": "spark_memory.md",
         "content": "Spark executor OutOfMemoryError memory failure"},
        {"source": "api_timeout.md",
         "content": "API timeout and latency"},
    ])
    monkeypatch.setattr(semantic, "load_embedding_model", lambda: FakeModel())

    results = semantic.retrieve_semantic(
        "Spark memory OutOfMemoryError",
        top_k=2,
    )

    assert results
    assert results[0]["source"] == "spark_memory.md"
    assert -1.0 <= results[0]["score"] <= 1.0


def test_semantic_retrieval_returns_empty_for_blank_query():
    assert semantic.retrieve_semantic("   ") == []


def test_semantic_retrieval_rejects_invalid_top_k():
    with pytest.raises(ValueError):
        semantic.retrieve_semantic("memory failure", top_k=0)
