
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNBOOKS_DIR = PROJECT_ROOT / "runbooks"


def load_runbooks() -> list[dict[str, str]]:
    """Load non-empty Markdown runbooks and preserve their filenames."""
    documents = []

    if not RUNBOOKS_DIR.exists():
        return documents

    for path in sorted(RUNBOOKS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8-sig").strip()

        if content:
            documents.append({
                "source": path.name,
                "content": content,
            })

    return documents


def tokenize(text: str) -> set[str]:
    """Convert text to lowercase searchable words."""
    return set(re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower()))


def chunk_text(
    text: str,
    chunk_size: int = 120,
    overlap: int = 20,
) -> list[str]:
    """Split text into overlapping word chunks."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")

    words = text.split()
    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_size])

        if chunk:
            chunks.append(chunk)

        if start + chunk_size >= len(words):
            break

    return chunks


def diversify_results(
    results: list[dict[str, str | int | float]],
    top_k: int,
) -> list[dict[str, str | int | float]]:
    """Prefer distinct runbook sources before repeating a source."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    selected = []
    deferred = []
    seen_sources = set()

    # First pass: select the highest-ranked chunk from each source.
    for result in results:
        source = str(result["source"])

        if source not in seen_sources:
            selected.append(result)
            seen_sources.add(source)
        else:
            deferred.append(result)

    # Fill remaining slots with repeated sources in original rank order.
    return (selected + deferred)[:top_k]


def retrieve_runbooks(
    query: str,
    top_k: int = 3,
    diversify: bool = False,
) -> list[dict[str, str | int | float]]:
    """Rank runbook chunks using a heuristic keyword score.

    Score = keyword overlap ratio + optional category bonus of 0.5.
    The overlap ratio is between 0 and 1; the total score can reach 1.5.
    Scores are ranking heuristics, not normalized similarity probabilities.

    Set diversify=True to prefer distinct runbook sources in the results.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query_terms = tokenize(query)

    if not query_terms:
        return []

    category_by_source = {
        "spark_memory.md": {"memory_error"},
        "api_timeout.md": {"timeout"},
        "permission_error.md": {"permission_error"},
    }

    results = []

    for document in load_runbooks():
        source = document["source"]
        expected_categories = category_by_source.get(source, set())

        for index, chunk in enumerate(chunk_text(document["content"])):
            chunk_terms = tokenize(chunk)
            matched_terms = query_terms & chunk_terms

            if not matched_terms:
                continue

            # Baseline keyword-overlap score.
            base_score = len(matched_terms) / len(query_terms)

            # Boost chunks from the matching category's runbook.
            category_match = bool(expected_categories & query_terms)

            score = round(
                base_score + (0.5 if category_match else 0.0),
                4,
            )

            results.append({
                "source": source,
                "chunk_id": index,
                "score": score,
                "content": chunk,
            })

    # Sort by descending score, then deterministic tie-breaking.
    results.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["source"]),
            int(item["chunk_id"]),
        )
    )

    if diversify:
        return diversify_results(results, top_k)

    return results[:top_k]
