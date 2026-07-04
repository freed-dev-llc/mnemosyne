"""The RAG chain itself — ingest (build the memory) and ask (retrieve + generate).

This module wires together the single-purpose stages (loaders → chunking → embeddings →
index → prompts → llm). It is the only place that knows the *order* of the pipeline; the
stages themselves stay independent and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import index as index_mod
from .chunking import chunk_documents
from .config import Settings, get_settings
from .embeddings import get_embeddings
from .llm import get_chat_model
from .prompts import DEFAULT_SYSTEM_PROMPT, build_messages, format_context

if TYPE_CHECKING:
    from langchain_core.documents import Document

    from .packs.base import KnowledgePack


@dataclass
class IngestStats:
    """Summary returned by :func:`ingest`."""

    pack: str
    documents: int
    chunks: int
    embedding_model: str
    index_path: str


@dataclass
class Source:
    """A single cited source behind an answer."""

    n: int
    title: str
    source: str
    page: int | None = None

    @classmethod
    def from_document(cls, n: int, doc: Document) -> Source:
        """The citation for a retrieved chunk, read from the metadata the loaders captured."""
        return cls(
            n=n,
            title=doc.metadata.get("title", ""),
            source=doc.metadata.get("source", ""),
            page=doc.metadata.get("page"),
        )


@dataclass
class RagAnswer:
    """An answer plus the sources it was grounded in."""

    question: str
    text: str
    sources: list[Source]


def _first_int(*values: int | None) -> int:
    """First non-None int (CLI flag → pack → settings precedence)."""
    for value in values:
        if value is not None:
            return value
    raise ValueError("no integer value provided")


def _first_str(*values: str | None) -> str:
    """First non-None string (CLI flag → pack → settings precedence)."""
    for value in values:
        if value is not None:
            return value
    raise ValueError("no string value provided")


def ingest(
    pack: KnowledgePack,
    settings: Settings | None = None,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    embedding_model: str | None = None,
    local_only: bool = False,
) -> IngestStats:
    """Build (or rebuild) the FAISS index for ``pack``.

    Loads the pack's corpus, chunks and embeds it, and writes the index + metadata under
    ``knowledge/<pack>/``. ``local_only=True`` indexes only the local corpus (no URL
    fetches), for a deterministic, offline build.
    """
    settings = settings or get_settings()

    staging_dir = (settings.staging_dir / pack.name) if settings.staging_dir else None
    docs = pack.load(local_only=local_only, staging_dir=staging_dir)
    if not docs:
        raise ValueError(
            f"No documents found for pack '{pack.name}'. Add files under "
            f"{pack.directory / 'sources'}, list URLs in its sources.yaml, or drop staged "
            "files under MNEMOSYNE_STAGING_DIR. Mnemosyne ships no third-party docs — you "
            "populate the corpus locally."
        )

    size = _first_int(chunk_size, pack.chunk_size, settings.chunk_size)
    overlap = _first_int(chunk_overlap, pack.chunk_overlap, settings.chunk_overlap)
    chunks = chunk_documents(docs, size, overlap)

    emb_model = _first_str(embedding_model, pack.embedding_model, settings.embedding_model)
    embeddings = get_embeddings(emb_model, settings)

    normalize = settings.faiss_normalize
    path = index_mod.index_dir(pack.name, settings)
    store = index_mod.build_index(chunks, embeddings, path, normalize=normalize)
    # Report what was actually embedded and indexed: build_index skips any chunk the embedder
    # cannot embed (issue #40), so this can be < len(chunks); it equals it on a clean run.
    indexed = int(store.index.ntotal)
    index_mod.write_meta(
        path,
        {
            "pack": pack.name,
            "documents": len(docs),
            "chunks": indexed,
            "embedding_model": emb_model,
            "chunk_size": size,
            "chunk_overlap": overlap,
            "normalize": normalize,
        },
    )
    return IngestStats(
        pack=pack.name,
        documents=len(docs),
        chunks=indexed,
        embedding_model=emb_model,
        index_path=str(path),
    )


class RagPipeline:
    """Loads a built index and answers questions grounded in it."""

    def __init__(
        self,
        pack: KnowledgePack,
        settings: Settings | None = None,
        *,
        chat_model: str | None = None,
        top_k: int | None = None,
    ) -> None:
        self.pack = pack
        self.settings = settings or get_settings()

        path = index_mod.index_dir(pack.name, self.settings)
        if not index_mod.index_exists(path):
            raise FileNotFoundError(
                f"No index for pack '{pack.name}'. Build it first: mnemosyne ingest {pack.name}"
            )

        # Reuse the exact embedding model + normalization recorded at ingest time, so queries
        # are embedded and scored the same way the stored vectors were. An index built before
        # the ``normalize`` knob existed has no key, defaulting to the historical False.
        meta = index_mod.read_meta(path) or {}
        emb_model = (
            meta.get("embedding_model") or pack.embedding_model or self.settings.embedding_model
        )
        self.embeddings = get_embeddings(emb_model, self.settings)
        self.store = index_mod.load_index(
            path, self.embeddings, normalize=bool(meta.get("normalize", False))
        )

        self.top_k = _first_int(top_k, pack.top_k, self.settings.top_k)
        model = _first_str(chat_model, pack.chat_model, self.settings.chat_model)
        self.llm = get_chat_model(model, self.settings)

    def retrieve(self, question: str, k: int | None = None) -> list[Document]:
        """Return the top-k chunks most relevant to ``question``."""
        return self.store.similarity_search(question, k=k or self.top_k)

    def ask(self, question: str, k: int | None = None, chat_history: str = "") -> RagAnswer:
        """Retrieve relevant context and generate a grounded, cited answer.

        ``chat_history`` is an optional running transcript for multi-turn sessions; the
        ``chat`` CLI accumulates and threads it. Single ``ask`` calls leave it empty.
        """
        docs = self.retrieve(question, k)
        context = format_context(docs)
        messages = build_messages(
            self.pack.system_prompt or DEFAULT_SYSTEM_PROMPT, context, question, chat_history
        )
        response = self.llm.invoke(messages)
        text = response.content if hasattr(response, "content") else str(response)
        sources = [Source.from_document(i, doc) for i, doc in enumerate(docs, 1)]
        return RagAnswer(question=question, text=str(text), sources=sources)
