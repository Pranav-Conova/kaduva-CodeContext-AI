"""Retrieval service: query → embedding → top-K chunk retrieval."""

import logging
from dataclasses import dataclass

from app.services.embedding import embed_query
from app.services.vector_store import query_chunks
from app.config import settings

logger = logging.getLogger("codecontext.retrieval")


@dataclass
class RetrievedChunk:
    """A chunk retrieved from the vector store with relevance info."""
    file_path: str
    symbol: str
    code: str
    language: str
    distance: float
    start_line: int | None = None
    end_line: int | None = None


def retrieve(
    project_id: int,
    question: str,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve the most relevant code chunks for a given question.

    1. Embeds the question
    2. Queries ChromaDB for nearest neighbors
    3. Returns ranked RetrievedChunk objects
    """
    if top_k is None:
        top_k = settings.DEFAULT_TOP_K

    logger.info("Retrieving top-%d chunks for project %d: '%s...'", top_k, project_id, question[:80])
    query_emb = embed_query(question)
    results = query_chunks(project_id, query_emb, top_k=top_k)

    chunks: list[RetrievedChunk] = []

    if not results["ids"] or not results["ids"][0]:
        return chunks

    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
        code = results["documents"][0][i] if results["documents"][0] else ""
        distance = results["distances"][0][i] if results["distances"][0] else 1.0

        chunks.append(RetrievedChunk(
            file_path=meta.get("file_path", "unknown"),
            symbol=meta.get("symbol", "unknown"),
            code=code,
            language=meta.get("language", "unknown"),
            distance=distance,
            start_line=meta.get("start_line"),
            end_line=meta.get("end_line"),
        ))

    logger.info("Retrieved %d chunks for project %d", len(chunks), project_id)
    return chunks


def build_context_prompt(chunks: list[RetrievedChunk]) -> str:
    """Build a structured context string from retrieved chunks for the LLM."""
    if not chunks:
        return "No relevant code found in the repository."

    sections: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        location = chunk.file_path
        if chunk.start_line:
            location += f" (lines {chunk.start_line}-{chunk.end_line})"
        if chunk.symbol and chunk.symbol not in ("<file>", "<module>", "<imports>"):
            location += f" → {chunk.symbol}"

        sections.append(
            f"--- [{i}] {location} ({chunk.language}) ---\n{chunk.code}"
        )

    return "\n\n".join(sections)
