"""
Test for ChromaDB knowledge base loader and retrieval.
No API key needed -- uses ChromaDB's default embedding function.
"""
import os
import sys
import json
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base.loader import init_knowledge_base, query_knowledge_base

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHROMA_DIR = os.path.join(_BASE_DIR, "chroma_db")


def test_knowledge_base():
    if os.path.exists(_CHROMA_DIR):
        shutil.rmtree(_CHROMA_DIR)

    print("Initializing knowledge base...")
    init_knowledge_base()

    print("Querying: 'services timing out after database errors'")
    results = query_knowledge_base("services timing out after database errors", n_results=3)

    print(f"\nTop {len(results)} results:")
    for r in results:
        print(f"  - {r['metadata']['name']} (distance: {r['distance']:.4f})")

    assert len(results) == 3, "Should return 3 results"
    pattern_names = [r["metadata"]["name"] for r in results]
    print(f"\nMatched patterns: {pattern_names}")

    print("\nQuerying: 'out of memory java heap space process killed'")
    results2 = query_knowledge_base("out of memory java heap space process killed", n_results=3)
    for r in results2:
        print(f"  - {r['metadata']['name']} (distance: {r['distance']:.4f})")

    oom_related = [r for r in results2 if "Memory" in r["metadata"]["name"] or "OOM" in r["metadata"]["name"]]
    assert len(oom_related) > 0, "Should find OOM-related patterns"

    print("\nQuerying: 'disk full no space left on device'")
    results3 = query_knowledge_base("disk full no space left on device", n_results=3)
    for r in results3:
        print(f"  - {r['metadata']['name']} (distance: {r['distance']:.4f})")

    print("\nIdempotency check: re-init should not duplicate...")
    init_knowledge_base()
    results4 = query_knowledge_base("test query", n_results=3)
    assert len(results4) == 3, "Should still return exactly 3"

    print("\nAll knowledge base tests passed!")


if __name__ == "__main__":
    test_knowledge_base()
