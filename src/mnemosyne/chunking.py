"""Chunk — cut documents into retrievable units.

Chunking is the single highest-leverage knob in RAG (see ``docs/RAG-101.md``). Too small
and a chunk loses context; too big and its embedding becomes a blurry average and
retrieval gets noisy. We use LangChain's recursive splitter, which prefers natural
boundaries (paragraphs → sentences) before a hard cut, with a little overlap so a sentence
split across a boundary still lands whole somewhere.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 150,
) -> list[Document]:
    """Split ``docs`` into overlapping chunks, preserving + numbering metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk"] = i
    return chunks
