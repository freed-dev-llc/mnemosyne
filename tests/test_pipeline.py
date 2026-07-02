"""Pipeline dataclasses: the shared citation extractor (no Ollama/network needed)."""

from __future__ import annotations

from langchain_core.documents import Document

from mnemosyne.pipeline import Source


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
