"""Loaders must capture citable metadata and reject the unsupported."""

from __future__ import annotations

from pathlib import Path

import pytest

from mnemosyne.loaders import load_documents, load_file


def test_markdown_loads_with_metadata(tmp_path: Path) -> None:
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nbody text", encoding="utf-8")
    docs = load_file(f)
    assert len(docs) == 1
    assert "body text" in docs[0].page_content
    assert docs[0].metadata["source"] == str(f)
    assert docs[0].metadata["title"] == "note"


def test_html_is_stripped_to_text(tmp_path: Path) -> None:
    f = tmp_path / "page.html"
    f.write_text(
        "<html><head><title>Adopt</title><style>x{}</style></head>"
        "<body><p>Hello</p><script>bad()</script></body></html>",
        encoding="utf-8",
    )
    (doc,) = load_file(f)
    assert "Hello" in doc.page_content
    assert "bad()" not in doc.page_content
    assert doc.metadata["title"] == "Adopt"


def test_unsupported_suffix_raises(tmp_path: Path) -> None:
    f = tmp_path / "data.xyz"
    f.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_file(f)


def test_load_documents_flattens(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    b = tmp_path / "b.txt"
    a.write_text("alpha", encoding="utf-8")
    b.write_text("beta", encoding="utf-8")
    docs = load_documents([a, b])
    assert {d.page_content for d in docs} == {"alpha", "beta"}
