"""Pipeline unit tests: citation extractor + retrieval score floor (no Ollama/network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from mnemosyne.pipeline import RagAnswer, RagPipeline, Source


def test_source_from_document_reads_loader_metadata() -> None:
    """The extractor maps the metadata the loaders captured into a numbered citation."""
    doc = Document(
        page_content="chunk text",
        metadata={"title": "UniFi Basics", "source": "docs/unifi.pdf", "page": 3},
    )
    assert Source.from_document(2, doc) == Source(
        n=2, title="UniFi Basics", source="docs/unifi.pdf", page=3
    )


def test_source_from_document_defaults_missing_metadata() -> None:
    """Missing title/source/page metadata default to '', '', None."""
    source = Source.from_document(1, Document(page_content="chunk with no metadata"))
    assert source == Source(n=1, title="", source="", page=None)


# --- retrieval score floor ----------------------------------------------------------------


class _FakeStore:
    """Minimal FAISS-store stand-in returning canned (doc, distance) pairs, nearest first."""

    def __init__(self, scored: list[tuple[Document, float]]) -> None:
        self._scored = scored

    def similarity_search(self, query: str, k: int) -> list[Document]:
        return [doc for doc, _ in self._scored[:k]]

    def similarity_search_with_score(self, query: str, k: int) -> list[tuple[Document, float]]:
        return self._scored[:k]


def _pipeline(store: _FakeStore, *, score_floor: float | None, top_k: int = 5) -> RagPipeline:
    """A RagPipeline wired to a fake store, bypassing the Ollama-touching ``__init__``."""
    pipe = RagPipeline.__new__(RagPipeline)
    pipe.store = store  # type: ignore[assignment]
    pipe.top_k = top_k
    pipe.score_floor = score_floor
    return pipe


def _docs(n: int) -> list[Document]:
    return [Document(page_content=f"chunk {i}") for i in range(n)]


def test_retrieve_without_floor_returns_all_topk() -> None:
    """``score_floor=None`` keeps the historical behavior: return the top-k however far."""
    docs = _docs(3)
    store = _FakeStore([(docs[0], 0.2), (docs[1], 0.9), (docs[2], 1.7)])
    assert _pipeline(store, score_floor=None).retrieve("q") == docs


def test_retrieve_with_floor_drops_distant_chunks() -> None:
    """A chunk past the floor is dropped; closer ones are kept."""
    docs = _docs(3)
    store = _FakeStore([(docs[0], 0.2), (docs[1], 0.9), (docs[2], 1.7)])
    assert _pipeline(store, score_floor=1.0).retrieve("q") == [docs[0], docs[1]]


def test_retrieve_floor_boundary_is_inclusive() -> None:
    """A chunk exactly at the floor distance is kept (``<=``, not ``<``)."""
    docs = _docs(1)
    store = _FakeStore([(docs[0], 1.0)])
    assert _pipeline(store, score_floor=1.0).retrieve("q") == docs


def test_retrieve_with_floor_returns_empty_when_nothing_close() -> None:
    """An off-topic query (every chunk past the floor) retrieves nothing."""
    store = _FakeStore([(d, 1.3) for d in _docs(2)])
    assert _pipeline(store, score_floor=1.0).retrieve("q") == []


@pytest.mark.parametrize("bad_k", [0, -3])
def test_retrieve_rejects_non_positive_k(bad_k: int) -> None:
    """``k < 1`` is a caller error (rejected), not a silent fallback to the default top-k."""
    store = _FakeStore([(d, 0.1) for d in _docs(3)])
    with pytest.raises(ValueError, match="k must be a positive integer"):
        _pipeline(store, score_floor=None).retrieve("q", k=bad_k)


def test_retrieve_none_k_uses_top_k() -> None:
    """``k=None`` still resolves to the configured top-k (unchanged default behavior)."""
    docs = _docs(4)
    store = _FakeStore([(d, 0.1) for d in docs])
    assert _pipeline(store, score_floor=None, top_k=2).retrieve("q") == docs[:2]


def test_ask_short_circuits_without_llm_on_empty_retrieval() -> None:
    """When the floor rejects everything, ``ask`` answers 'not in the knowledge base'
    without invoking the model."""
    store = _FakeStore([(_docs(1)[0], 1.6)])
    pipe = _pipeline(store, score_floor=1.0)

    class _BoomLLM:
        def invoke(self, messages: object) -> object:
            raise AssertionError("the LLM must not be called when nothing is retrieved")

    pipe.llm = _BoomLLM()  # type: ignore[assignment]
    pipe.pack = SimpleNamespace(system_prompt=None)  # type: ignore[assignment]

    answer = pipe.ask("what is the capital of France?")
    assert isinstance(answer, RagAnswer)
    assert answer.sources == []
    assert "knowledge base" in answer.text.lower()
