"""Mnemosyne — a local, teaching-first RAG pipeline (Ollama + LangChain + FAISS).

Turn any model into an instant expert by giving it fast access to documents.
See ``docs/RAG-101.md`` for the concepts and ``docs/ARCHITECTURE.md`` for the wiring.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

# Single source of truth is pyproject.toml: read the version from installed package
# metadata so `mnemosyne version` and the HTTP `/health` endpoint can't drift from the
# released version (they did through 0.6.0/0.6.1, reporting a stale hardcoded string).
# The fallback covers importing from a source tree that was never installed.
try:
    __version__ = _pkg_version("mnemosyne-rag")
except PackageNotFoundError:  # pragma: no cover - source checkout without an install
    __version__ = "0.0.0+unknown"

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
