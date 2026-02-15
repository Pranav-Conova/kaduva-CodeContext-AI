"""Embedding service using sentence-transformers (all-MiniLM-L6-v2)."""

import logging
import time
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger("codecontext.embedding")

# Lazy-loaded singleton
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model (cached after first call)."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s...", settings.EMBEDDING_MODEL)
        t0 = time.time()
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Model loaded in %.1fs", time.time() - t0)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text strings.
    Returns a list of float vectors (384-dimensional for MiniLM).
    """
    model = _get_model()
    logger.info("Embedding %d texts (batch_size=%d)...", len(texts), settings.EMBEDDING_BATCH_SIZE)
    t0 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=settings.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    elapsed = time.time() - t0
    logger.info("Embedded %d texts in %.1fs (%.0f texts/s)", len(texts), elapsed, len(texts) / max(elapsed, 0.01))
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Generate an embedding for a single query string."""
    model = _get_model()
    embedding = model.encode(
        query,
        normalize_embeddings=True,
    )
    return embedding.tolist()
