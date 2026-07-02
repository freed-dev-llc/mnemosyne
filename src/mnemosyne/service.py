"""Transport-agnostic query service — the shared logic behind every transport.

Both the MCP server (``mcp_server.py``, for agents) and the HTTP server
(``http_server.py``, for web UIs/services) are thin wrappers over these three functions.
They return plain JSON-able dicts and raise on bad input (unknown pack → ``KeyError``,
no built index → ``FileNotFoundError``); each transport maps those to its own error shape.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from . import index as index_mod
from .config import Settings, get_settings
from .packs.registry import discover_packs, get_pack
from .pipeline import RagPipeline, Source

if TYPE_CHECKING:
    from .packs.base import KnowledgePack

# One RagPipeline per pack, keyed by pack name, alongside the index.faiss mtime it was built
# from. `ask`/`search` back a long-running server (mnemosyne-http, mnemosyne-mcp) that would
# otherwise reload the FAISS index and rebuild the Ollama clients on every single call. The
# fingerprint invalidates the entry the moment a re-ingest rewrites index.faiss, so a running
# server picks up a fresh `mnemosyne ingest` on the very next request, no restart required.
_pipeline_cache: dict[str, tuple[int, RagPipeline]] = {}
_cache_lock = threading.Lock()


def _get_pipeline(pack: KnowledgePack, settings: Settings) -> RagPipeline:
    """A cached ``RagPipeline`` for ``pack``, rebuilt only when its index changes.

    A pack with no built index is never cached: it's constructed directly so its
    ``FileNotFoundError`` propagates unchanged on every call (there is nothing to cache).
    Otherwise the check-fingerprint/build-if-stale/store sequence runs under a single lock so
    two concurrent cold-start requests for the same pack can't race and build twice.
    """
    path = index_mod.index_dir(pack.name, settings)
    if not index_mod.index_exists(path):
        return RagPipeline(pack, settings)

    with _cache_lock:
        fingerprint = (path / "index.faiss").stat().st_mtime_ns
        cached = _pipeline_cache.get(pack.name)
        if cached is not None and cached[0] == fingerprint:
            return cached[1]
        pipeline = RagPipeline(pack, settings)
        _pipeline_cache[pack.name] = (fingerprint, pipeline)
        return pipeline


def list_packs() -> list[dict[str, Any]]:
    """All discoverable packs with title, description, and index status."""
    settings = get_settings()
    packs: list[dict[str, Any]] = []
    for name, pack in sorted(discover_packs().items()):
        path = index_mod.index_dir(name, settings)
        meta = index_mod.read_meta(path) or {}
        packs.append(
            {
                "name": name,
                "title": pack.title,
                "description": pack.description,
                "built": index_mod.index_exists(path),
                "chunks": meta.get("chunks"),
                "embedding_model": meta.get("embedding_model"),
            }
        )
    return packs


def ask(pack: str, question: str, k: int | None = None) -> dict[str, Any]:
    """A grounded answer with cited sources, from ``pack``."""
    pipeline = _get_pipeline(get_pack(pack), get_settings())
    answer = pipeline.ask(question, k=k)
    return {
        "pack": pack,
        "question": question,
        "answer": answer.text,
        "sources": [
            {"n": s.n, "title": s.title, "source": s.source, "page": s.page} for s in answer.sources
        ],
    }


def search(pack: str, query: str, k: int | None = None) -> dict[str, Any]:
    """The top-k raw chunks from ``pack`` (retrieval only, no generation)."""
    pipeline = _get_pipeline(get_pack(pack), get_settings())
    docs = pipeline.retrieve(query, k=k)
    results = []
    for i, doc in enumerate(docs, 1):
        source = Source.from_document(i, doc)
        results.append(
            {
                "n": source.n,
                "title": source.title,
                "source": source.source,
                "page": source.page,
                "text": doc.page_content,
            }
        )
    return {"pack": pack, "query": query, "results": results}
