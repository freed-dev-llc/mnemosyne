# 2. Local RAG stack: Ollama + LangChain + FAISS

Date: 2026-06-23

## Status

Accepted

## Context

Mnemosyne needs to (a) embed and store a corpus, and (b) retrieve from it and generate
grounded answers — while being a *teaching* repo and a *local* family tool. Constraints:

- **Local-first / private.** It will hold and answer over potentially sensitive home/lab
  and vendor documentation. Nothing should require an API key or leave the machine.
- **Legible.** Every stage should be a small module a reader can open and understand.
- **Cheap to run** on a CPU-only or modest box.

Candidate axes: LLM+embeddings runtime (cloud APIs vs local Ollama vs llama.cpp), an
orchestration layer (LangChain vs LlamaIndex vs hand-rolled), and a vector store (FAISS vs
Chroma vs Qdrant/pgvector services).

## Decision

- **Ollama** for both generation and embeddings. One local runtime, no keys, trivially
  swappable models. Defaults follow the [rag_ollama](https://github.com/MariyaSha/rag_ollama)
  tutorial this project is based on (`bge-m3` embeddings, `qwen2.5:1.5b` chat) — tiny and
  CPU-friendly. It is already in the family's toolbox and matches the local-first goal.
- **LangChain** for orchestration. Its loaders, `RecursiveCharacterTextSplitter`,
  retrievers, and prompt plumbing are the scaffold that makes the pipeline short and the
  teaching obvious — without hiding the stages.
- **FAISS** as the vector store. File-based, no service to run, fast similarity search, and
  a one-line save/load. The index becomes a shippable artifact, which fits the
  knowledge-pack model.

## Consequences

- Zero external dependencies at query time beyond a running Ollama — fully offline-capable.
- The FAISS index is a file: ingest and ask are decoupled, and indices could ship with packs.
- LangChain is a heavy dependency with a fast-moving API; we pin it and keep our use to the
  stable, well-trodden surface. If it ever obscures more than it helps, the module
  boundaries (`loaders`/`chunking`/`index`/`pipeline`) let us drop it incrementally.
- FAISS is in-memory + flat by default; fine for home/lab corpora. Very large corpora would
  need an IVF/HNSW index or an external store — deferred until a pack actually needs it.
