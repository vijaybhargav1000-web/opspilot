
from functools import lru_cache

from sentence_transformers import SentenceTransformer, util

from app.retrieval import (
    chunk_text,
    diversify_results,
    load_runbooks,
)


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    """Load the local embedding model once per Python process."""
    return SentenceTransformer(MODEL_NAME)


def retrieve_semantic(
    query: str,
    top_k: int = 3,
    diversify: bool = False,
) -> list[dict[str, str | int | float]]:
    """Retrieve runbook chunks using semantic similarity.

    Set diversify=True to prefer distinct runbook sources in the results.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if not query or not query.strip():
        return []

    documents = load_runbooks()
    chunks = []

    for document in documents:
        for chunk_id, chunk in enumerate(chunk_text(document["content"])):
            chunks.append({
                "source": document["source"],
                "chunk_id": chunk_id,
                "content": chunk,
            })

    if not chunks:
        return []

    model = load_embedding_model()

    query_embedding = model.encode(
        query,
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    chunk_embeddings = model.encode(
        [item["content"] for item in chunks],
        convert_to_tensor=True,
        normalize_embeddings=True,
    )

    similarities = util.cos_sim(query_embedding, chunk_embeddings)[0]
    ranked_indices = similarities.argsort(descending=True).tolist()

    results = []

    for index in ranked_indices:
        item = chunks[index]
        results.append({
            **item,
            "score": round(float(similarities[index].item()), 4),
        })

    if diversify:
        return diversify_results(results, top_k)

    return results[:top_k]
