import json
import os

import chromadb

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CHROMA_DIR = os.path.join(_BASE_DIR, "chroma_db")
_PATTERNS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure_patterns.json")
_COLLECTION_NAME = "failure_patterns"


def _get_client():
    return chromadb.PersistentClient(path=_CHROMA_DIR)


def init_knowledge_base() -> None:
    """Load failure patterns into ChromaDB. Skips if collection already populated."""
    client = _get_client()
    collection = client.get_or_create_collection(name=_COLLECTION_NAME)

    if collection.count() > 0:
        return

    with open(_PATTERNS_FILE, "r") as f:
        patterns = json.load(f)

    ids = []
    documents = []
    metadatas = []

    for pattern in patterns:
        doc_text = (
            f"{pattern['name']}: {pattern['description']} "
            f"Symptoms: {', '.join(pattern['symptoms'])}. "
            f"Root cause: {pattern['root_cause']}. "
            f"Resolution: {pattern['resolution']}"
        )
        ids.append(pattern["id"])
        documents.append(doc_text)
        metadatas.append({
            "name": pattern["name"],
            "root_cause": pattern["root_cause"],
            "resolution": pattern["resolution"],
            "symptoms": json.dumps(pattern["symptoms"]),
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)


def query_knowledge_base(query_text: str, n_results: int = 3) -> list[dict]:
    """Query ChromaDB for matching failure patterns. Returns top matches."""
    client = _get_client()
    collection = client.get_or_create_collection(name=_COLLECTION_NAME)

    if collection.count() == 0:
        init_knowledge_base()
        collection = client.get_or_create_collection(name=_COLLECTION_NAME)

    results = collection.query(query_texts=[query_text], n_results=n_results)

    patterns = []
    for i in range(len(results["ids"][0])):
        pattern = {
            "id": results["ids"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        }
        patterns.append(pattern)

    return patterns
