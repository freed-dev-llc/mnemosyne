"""Index — build / save / load the FAISS vector store.

The saved index *is* the memory: a file you build once and reuse. Keeping it on disk
decouples ``ingest`` (slow, occasional) from ``ask`` (fast, frequent) and makes an index a
shippable artifact. Alongside it we write a small ``meta.json`` recording the embedding
model and chunk settings, so ``ask`` can reuse exactly what ``ingest`` produced.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .config import Settings, get_settings

META_FILE = "meta.json"

_log = logging.getLogger(__name__)


def index_dir(pack_name: str, settings: Settings | None = None) -> Path:
    """Directory holding the FAISS index + metadata for ``pack_name``."""
    settings = settings or get_settings()
    return settings.knowledge_dir / pack_name


def index_exists(path: Path) -> bool:
    """True if a built FAISS index is present at ``path``."""
    return (path / "index.faiss").exists()


def _all_finite(vector: list[float]) -> bool:
    """True if every component is a finite number (no NaN, no infinity)."""
    return all(math.isfinite(x) for x in vector)


def _describe_chunk(doc: Document) -> str:
    """A short, citable label for a chunk, for skip warnings: source, offset, preview."""
    meta = doc.metadata
    where = meta.get("start_index", meta.get("chunk", "?"))
    preview = " ".join(doc.page_content.split())[:60]
    return f"{meta.get('source', '?')} @ {where}: {preview!r}"


def _embed_chunks(
    chunks: list[Document], embeddings: Embeddings
) -> tuple[list[str], list[list[float]], list[dict[str, Any]]]:
    """Embed ``chunks``, dropping any the backend cannot embed, and return the survivors.

    Fast path: one batch ``embed_documents`` call; if it succeeds and every vector is finite,
    all chunks are kept. Slow path, taken only when the batch raises or returns a non-finite
    vector: re-embed chunk by chunk so a single un-embeddable chunk (e.g. a bge-m3/Ollama NaN,
    issue #40) is skipped with a warning instead of aborting the whole ingest (the same
    resilience the loader already gives an unreachable URL). Returns ``(texts, vectors,
    metadatas)`` positionally aligned over the kept chunks.
    """
    texts = [c.page_content for c in chunks]
    try:
        vectors = embeddings.embed_documents(texts)
        if all(_all_finite(v) for v in vectors):
            return texts, vectors, [c.metadata for c in chunks]
        _log.warning("Batch embedding returned a non-finite vector; isolating per chunk.")
    except Exception as exc:  # batch failed wholesale (e.g. one NaN fails the whole call)
        _log.warning("Batch embedding failed (%s); isolating per chunk.", exc)

    keep_texts: list[str] = []
    keep_vectors: list[list[float]] = []
    keep_metas: list[dict[str, Any]] = []
    skipped = 0
    for chunk in chunks:
        try:
            vector = embeddings.embed_query(chunk.page_content)
        except Exception as exc:
            skipped += 1
            _log.warning("Skipping chunk (embedding failed: %s): %s", exc, _describe_chunk(chunk))
            continue
        if not _all_finite(vector):
            skipped += 1
            _log.warning("Skipping chunk (embedding had NaN/Inf): %s", _describe_chunk(chunk))
            continue
        keep_texts.append(chunk.page_content)
        keep_vectors.append(vector)
        keep_metas.append(chunk.metadata)
    if skipped:
        _log.warning(
            "Skipped %d of %d chunk(s) the embedder could not embed.", skipped, len(chunks)
        )
    return keep_texts, keep_vectors, keep_metas


def build_index(
    chunks: list[Document], embeddings: Embeddings, path: Path, *, normalize: bool = False
) -> FAISS:
    """Embed ``chunks`` and persist a FAISS index to ``path``.

    A chunk the embedding backend cannot embed (it raises, or returns a NaN/Inf vector) is
    skipped with a warning rather than aborting the build (issue #40); every other chunk is
    indexed. Raises ``ValueError`` only when *no* chunk could be embedded.

    ``normalize=True`` unit-normalizes vectors so L2 ranks identically to cosine; it must be
    matched by :func:`load_index` at query time, so callers persist it in ``meta.json``.
    """
    texts, vectors, metadatas = _embed_chunks(chunks, embeddings)
    if not texts:
        raise ValueError(
            "No chunk could be embedded: the embedding backend failed or returned a non-finite "
            "vector for every chunk. Check that the embedding model is reachable and healthy."
        )
    store = FAISS.from_embeddings(
        text_embeddings=list(zip(texts, vectors, strict=True)),
        embedding=embeddings,
        metadatas=metadatas,
        normalize_L2=normalize,
    )
    path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(path))
    return store


def load_index(path: Path, embeddings: Embeddings, *, normalize: bool = False) -> FAISS:
    """Load a FAISS index previously written by :func:`build_index`.

    ``normalize`` must match the value the index was built with (recorded in ``meta.json``),
    so the query vector is normalized the same way the stored vectors were.
    """
    # The pickle here is one we wrote ourselves at ingest time.
    return FAISS.load_local(
        str(path), embeddings, allow_dangerous_deserialization=True, normalize_L2=normalize
    )


def write_meta(path: Path, meta: dict[str, Any]) -> None:
    """Record how the index was built (models, chunking, counts)."""
    path.mkdir(parents=True, exist_ok=True)
    (path / META_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_meta(path: Path) -> dict[str, Any] | None:
    """Read the build metadata for an index, or ``None`` if absent."""
    meta_path = path / META_FILE
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))
