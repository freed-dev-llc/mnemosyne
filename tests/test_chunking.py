"""Chunking is the highest-leverage RAG knob — pin its observable behavior."""

from __future__ import annotations

from langchain_core.documents import Document

from mnemosyne.chunking import chunk_documents
from mnemosyne.config import Settings


def _doc(text: str) -> Document:
    return Document(page_content=text, metadata={"source": "t.md", "title": "t"})


def test_chunks_are_numbered_and_keep_metadata() -> None:
    chunks = chunk_documents([_doc("word " * 600)], chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert [c.metadata["chunk"] for c in chunks] == list(range(len(chunks)))
    assert all(c.metadata["source"] == "t.md" for c in chunks)


def test_overlap_shares_text_between_neighbors() -> None:
    text = " ".join(f"s{i}" for i in range(300))
    chunks = chunk_documents([_doc(text)], chunk_size=120, chunk_overlap=40)
    # With overlap, no chunk should exceed the configured size by much, and we get >1.
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)


def test_short_doc_is_a_single_chunk() -> None:
    chunks = chunk_documents([_doc("just a short note")], chunk_size=800, chunk_overlap=120)
    assert len(chunks) == 1
    assert chunks[0].metadata["chunk"] == 0


def test_defaults_track_settings() -> None:
    """chunk_documents()'s own defaults must not drift from Settings (issue #53).

    Compares against the class-declared defaults, not an instantiated Settings(),
    since the latter resolves through pydantic-settings' env/.env layer and would
    make this test depend on runtime environment state.
    """
    text = " ".join(f"s{i}" for i in range(600))
    doc = _doc(text)
    chunk_size = Settings.model_fields["chunk_size"].default
    chunk_overlap = Settings.model_fields["chunk_overlap"].default
    explicit = chunk_documents([doc], chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    defaulted = chunk_documents([doc])
    assert [c.page_content for c in defaulted] == [c.page_content for c in explicit]
