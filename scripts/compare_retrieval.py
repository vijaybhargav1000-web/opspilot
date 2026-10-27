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
        "expected": "spark_memory.md",
    },
    {
        "name": "API timeout",
        "query": "Requests to the downstream service are too slow and timing out",
        "expected": "api_timeout.md",
    },
    {
        "name": "Permission failure",
        "query": "The application identity is forbidden from accessing a resource",
        "expected": "permission_error.md",
    },
]


def main():
    for case in TEST_CASES:
        print(f"\n=== {case['name']} ===")
        print(f"Query: {case['query']}")
        print(f"Expected: {case['expected']}")

        for label, retrieve in (
            ("Keyword", retrieve_runbooks),
            ("Semantic", retrieve_semantic),
        ):
            results = retrieve(case["query"], top_k=3)

            print(f"\n{label} results:")
            for rank, result in enumerate(results, start=1):
                print(
                    f"  {rank}. {result['source']} "
                    f"(score={result['score']})"
                )

            hit_at_3 = any(
                result["source"] == case["expected"]
                for result in results[:3]
            )
            hit_at_1 = (
                bool(results)
                and results[0]["source"] == case["expected"]
            )

            print(f"  Hit@3: {int(hit_at_3)}")
            print(f"  Hit@1: {int(hit_at_1)}")


if __name__ == "__main__":
    main()
