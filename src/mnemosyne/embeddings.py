"""Embeddings — text → vectors of meaning, via Ollama.

The one iron rule of RAG: embed your chunks and your queries with the *same* model.
Mixing embedders makes similarity distances meaningless. The pipeline records the model
used at ingest time so ``ask`` can reuse it.
"""

from __future__ import annotations

from langchain_ollama import OllamaEmbeddings

from .config import Settings, get_settings


def get_embeddings(
    model: str | None = None,
    settings: Settings | None = None,
) -> OllamaEmbeddings:
    """Return an Ollama embedding client for ``model`` (default: settings)."""
    settings = settings or get_settings()
    return OllamaEmbeddings(
        model=model or settings.embedding_model,
        base_url=settings.ollama_host,
    )
