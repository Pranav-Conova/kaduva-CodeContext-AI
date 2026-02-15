"""
Pure-Python vector store using NumPy cosine similarity.
No C++ build tools required — works out of the box on Windows.
Data is persisted to JSON files on disk, one per project.
"""

import json
import logging
import os
import numpy as np
from pathlib import Path

from app.config import settings

logger = logging.getLogger("codecontext.vectors")

# In-memory cache of loaded collections
_collections: dict[int, dict] = {}


def _collection_path(project_id: int) -> str:
    """Get the file path for a project's vector collection."""
    return os.path.join(settings.CHROMA_PERSIST_DIR, f"project_{project_id}.json")


def _load_collection(project_id: int) -> dict:
    """Load a collection from disk, or return empty one."""
    if project_id in _collections:
        return _collections[project_id]

    path = _collection_path(project_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _collections[project_id] = data
        return data

    empty = {"ids": [], "documents": [], "embeddings": [], "metadatas": []}
    _collections[project_id] = empty
    return empty


def _save_collection(project_id: int) -> None:
    """Persist a collection to disk."""
    path = _collection_path(project_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger.debug("Saving collection for project %d → %s", project_id, path)
    data = _collections.get(project_id, {})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def add_chunks(
    project_id: int,
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    """
    Store code chunks with their embeddings.

    Args:
        project_id: The project these chunks belong to.
        ids: Unique IDs for each chunk.
        documents: The raw code text for each chunk.
        embeddings: Pre-computed embedding vectors.
        metadatas: Metadata dicts (file_path, symbol, language, etc.).
    """
    collection = _load_collection(project_id)
    logger.info("Adding %d chunks to project %d vector store", len(ids), project_id)
    collection["ids"].extend(ids)
    collection["documents"].extend(documents)
    collection["embeddings"].extend(embeddings)
    collection["metadatas"].extend(metadatas)
    _save_collection(project_id)


def query_chunks(
    project_id: int,
    query_embedding: list[float],
    top_k: int = 20,
) -> dict:
    """
    Query the vector store for the most relevant chunks using cosine similarity.

    Returns dict with keys:
        ids, documents, metadatas, distances (each wrapped in an outer list for compatibility)
    """
    collection = _load_collection(project_id)

    if not collection["embeddings"]:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    # Compute cosine similarity
    query_vec = np.array(query_embedding, dtype=np.float32)
    stored_vecs = np.array(collection["embeddings"], dtype=np.float32)

    # Normalize
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    stored_norms = stored_vecs / (np.linalg.norm(stored_vecs, axis=1, keepdims=True) + 1e-10)

    # Cosine similarity (higher is better)
    similarities = stored_norms @ query_norm

    # Get top-K indices (highest similarity first)
    k = min(top_k, len(similarities))
    top_indices = np.argsort(similarities)[::-1][:k]
    logger.debug("Query returned top-%d results for project %d (best similarity: %.3f)", k, project_id, similarities[top_indices[0]])

    # Build result (use 1 - similarity as "distance" for compatibility)
    result_ids = [collection["ids"][i] for i in top_indices]
    result_docs = [collection["documents"][i] for i in top_indices]
    result_metas = [collection["metadatas"][i] for i in top_indices]
    result_distances = [float(1.0 - similarities[i]) for i in top_indices]

    return {
        "ids": [result_ids],
        "documents": [result_docs],
        "metadatas": [result_metas],
        "distances": [result_distances],
    }


def delete_collection(project_id: int) -> None:
    """Delete a project's entire vector collection."""
    path = _collection_path(project_id)
    if os.path.exists(path):
        os.remove(path)
        logger.info("Deleted vector collection for project %d", project_id)
    _collections.pop(project_id, None)
