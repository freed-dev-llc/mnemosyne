"""Index path + metadata helpers (the parts that don't need an embedder).

The final test builds a *real* FAISS index (imports faiss) with a deterministic in-process
fake embedder, so the path/build/load/search round trip is exercised offline.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from mnemosyne.config import Settings
from mnemosyne.index import (
    build_index,
    index_dir,
    index_exists,
    load_index,
    read_meta,
    write_meta,
)


def test_index_dir_is_under_knowledge_dir(tmp_path: Path) -> None:
    settings = Settings(knowledge_dir=tmp_path)
    assert index_dir("ubiquiti", settings) == tmp_path / "ubiquiti"


def test_index_exists_is_false_before_build(tmp_path: Path) -> None:
    assert index_exists(tmp_path / "ubiquiti") is False


def test_meta_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "ubiquiti"
    meta = {"pack": "ubiquiti", "chunks": 12, "embedding_model": "nomic-embed-text"}
    write_meta(path, meta)
    assert read_meta(path) == meta


def test_read_meta_missing_returns_none(tmp_path: Path) -> None:
    assert read_meta(tmp_path / "nope") is None


class _CountingEmbeddings(Embeddings):
    """Deterministic, offline stand-in for a real embedder (no Ollama, no network).

    Maps text to a fixed-dimension bag-of-words vector. The test queries with a document's
    exact text, so its vector matches that document's exactly (distance 0) and
    ``similarity_search`` is guaranteed to return that chunk.
    """

    _DIM = 64

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._DIM
        for token in text.lower().split():
            vec[sum(ord(c) for c in token) % self._DIM] += 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def test_real_faiss_index_build_load_search(tmp_path: Path) -> None:
    """Regression guard: build, persist, load, and search a real FAISS index end to end.

    This imports faiss for real, so it would have caught the oneMKL link break (a broken
    ``import faiss``). It skips ONLY when faiss is genuinely absent (a pip-only dev without
    the ``cpu`` extra); it deliberately does NOT use ``pytest.importorskip``, which would
    also skip on an installed-but-broken faiss and re-hide exactly that regression.
    """
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss not installed (the mamba env or the `cpu` extra provides it)")

    docs = [
        Document(page_content="device adoption brings a unifi device under controller management"),
        Document(page_content="a vlan tags traffic to segment a switch network"),
        Document(page_content="the firewall blocks inbound wan traffic by default"),
    ]
    path = tmp_path / "tiny"
    build_index(docs, _CountingEmbeddings(), path)

    assert index_exists(path)
    hits = load_index(path, _CountingEmbeddings()).similarity_search(docs[0].page_content, k=1)
    assert hits and hits[0].page_content == docs[0].page_content


class _PoisonEmbeddings(Embeddings):
    """Offline embedder that cannot embed one 'poison' text (mirrors a bge-m3/Ollama NaN).

    Good texts get a deterministic finite bag-of-words vector. The poison text yields a NaN
    vector from ``embed_query``; ``embed_documents`` either raises (``batch='raise'``, the real
    Ollama-500-on-the-batch case) or returns the NaN inline (``batch='nan'``), so both batch
    failure modes route into ``build_index``'s per-chunk fallback.
    """

    _DIM = 64

    def __init__(self, poison: str, *, batch: str = "raise") -> None:
        self._poison = poison
        self._batch = batch

    def _vector(self, text: str) -> list[float]:
        if text == self._poison:
            return [float("nan")] * self._DIM
        vec = [0.0] * self._DIM
        for token in text.lower().split():
            vec[sum(ord(c) for c in token) % self._DIM] += 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._batch == "raise" and self._poison in texts:
            raise RuntimeError("simulated backend 500: json: unsupported value: NaN")
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.mark.parametrize("batch", ["raise", "nan"])
def test_build_index_skips_unembeddable_chunk(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, batch: str
) -> None:
    """A chunk the embedder can't embed is skipped with a warning; the rest are indexed (#40)."""
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss not installed (the mamba env or the `cpu` extra provides it)")

    good1 = "device adoption brings a unifi device under controller management"
    poison = "a reference vlan layout separates infrastructure from untrusted devices"
    good2 = "the firewall blocks inbound wan traffic by default"
    docs = [
        Document(page_content=good1, metadata={"source": "s.md", "start_index": 7}),
        Document(page_content=poison, metadata={"source": "s.md", "start_index": 99}),
        Document(page_content=good2, metadata={"source": "s.md", "start_index": 200}),
    ]
    path = tmp_path / "tiny"
    with caplog.at_level(logging.WARNING):
        store = build_index(docs, _PoisonEmbeddings(poison, batch=batch), path)

    assert int(store.index.ntotal) == 2  # poison dropped, two survivors indexed
    assert any("Skipping chunk" in r.message for r in caplog.records)
    hits = load_index(path, _PoisonEmbeddings(poison, batch=batch)).similarity_search(good1, k=3)
    contents = {h.page_content for h in hits}
    assert good1 in contents and poison not in contents


def test_build_index_all_unembeddable_raises(tmp_path: Path) -> None:
    """If no chunk can be embedded, the build fails loudly rather than writing an empty index."""
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss not installed (the mamba env or the `cpu` extra provides it)")

    poison = "every chunk here is poison"
    docs = [Document(page_content=poison, metadata={"source": "s.md"})]
    with pytest.raises(ValueError, match="No chunk could be embedded"):
        build_index(docs, _PoisonEmbeddings(poison, batch="nan"), tmp_path / "x")
