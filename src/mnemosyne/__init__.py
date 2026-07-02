"""Mnemosyne — a local, teaching-first RAG pipeline (Ollama + LangChain + FAISS).

Turn any model into an instant expert by giving it fast access to documents.
See ``docs/RAG-101.md`` for the concepts and ``docs/ARCHITECTURE.md`` for the wiring.
"""

from __future__ import annotations

__version__ = "0.3.1"

from .config import Settings, get_settings
from .pipeline import IngestStats, RagAnswer, RagPipeline, ingest

__all__ = [
    "IngestStats",
    "RagAnswer",
    "RagPipeline",
    "Settings",
    "__version__",
    "get_settings",
    "ingest",
]
