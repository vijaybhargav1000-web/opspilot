
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval import retrieve_runbooks
from app.semantic_retrieval import retrieve_semantic


TEST_CASES = [
    {
        "name": "Spark memory failure",
        "query": "Spark executor ran out of heap memory and crashed",
        "relevant": {"spark_memory.md"},
    },
    {
        "name": "API timeout",
        "query": "Requests to the downstream service are too slow and timing out",
        "relevant": {"api_timeout.md"},
    },
    {
        "name": "Permission failure",
        "query": "The application identity is forbidden from accessing a resource",
        "relevant": {"permission_error.md"},
    },
    {
        "name": "Java heap space",
        "query": "The Spark job failed because the Java heap was exhausted",
        "relevant": {"spark_memory.md"},
    },
    {
        "name": "Slow API response",
        "query": "An API request waits too long for the service response",
        "relevant": {"api_timeout.md"},
    },
    {
        "name": "Access denied",
        "query": "The service account does not have permission to read the file",
        "relevant": {"permission_error.md"},
    },
    {
        "name": "Executor memory pressure",
        "query": "Spark executors keep crashing during a large data transformation",
        "relevant": {"spark_memory.md"},
    },
    {
        "name": "Downstream latency",
        "query": "Calls to an external dependency exceed the request timeout",
        "relevant": {"api_timeout.md"},
    },
    {
        "name": "IAM authorization failure",
        "query": "An IAM role is missing access to an S3 resource",
        "relevant": {"permission_error.md"},
    },
]


def reciprocal_rank(results, relevant):
    """Return the reciprocal rank of the first relevant result."""
    for rank, result in enumerate(results, start=1):
        if result["source"] in relevant:
            return 1 / rank
    return 0.0


def evaluate_retriever(retrieve, diversify=False, k=3):
    """Calculate Hit@K, Recall@K and MRR over labelled queries."""
    hits = []
    recalls = []
    reciprocal_ranks = []

    for case in TEST_CASES:
        results = retrieve(
            case["query"],
            top_k=k,
            diversify=diversify,
        )
        relevant = case["relevant"]
        retrieved_sources = {item["source"] for item in results}
        relevant_found = retrieved_sources.intersection(relevant)

        hits.append(int(bool(relevant_found)))
        recalls.append(len(relevant_found) / len(relevant))
        reciprocal_ranks.append(reciprocal_rank(results, relevant))

    total = len(TEST_CASES)

    return {
        f"Hit@{k}": sum(hits) / total,
        f"Recall@{k}": sum(recalls) / total,
        "MRR": sum(reciprocal_ranks) / total,
    }


def main():
    configurations = [
        ("Keyword baseline", retrieve_runbooks, False),
        ("Keyword diversified", retrieve_runbooks, True),
        ("Semantic baseline", retrieve_semantic, False),
        ("Semantic diversified", retrieve_semantic, True),
    ]

    print(f"Evaluation queries: {len(TEST_CASES)}")
    print("Top K: 3")
    print("Metrics are averaged across labelled queries.")

    for case in TEST_CASES:
        print(f"\n=== {case['name']} ===")
        print(f"Query: {case['query']}")

        for label, retrieve, diversify in configurations:
            results = retrieve(
                case["query"],
                top_k=3,
                diversify=diversify,
            )

            rank = reciprocal_rank(results, case["relevant"])
            sources = [item["source"] for item in results]

            print(
                f"{label}: {sources} | "
                f"First relevant reciprocal rank={rank:.3f}"
            )

    print("\n=== Aggregate comparison ===")

    for label, retrieve, diversify in configurations:
        metrics = evaluate_retriever(retrieve, diversify=diversify, k=3)
        formatted = " | ".join(
            f"{name}={value:.3f}"
            for name, value in metrics.items()
        )
        print(f"{label}: {formatted}")


if __name__ == "__main__":
    main()
