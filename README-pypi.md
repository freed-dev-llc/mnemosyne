# Mnemosyne

A local, teaching-first RAG pipeline (Ollama + LangChain + FAISS) that turns any model into
an instant expert on documents it has never seen, with no fine-tuning, no API keys, and
nothing leaving the box.

Point Mnemosyne at a corpus; it embeds and indexes it, and a small local model then answers
questions about it with inline citations. It ships a CLI, an MCP stdio server, and an HTTP
server. The full story (how RAG works, the design choices, the knowledge-pack model) is in
the [GitHub README](https://github.com/freed-dev-llc/mnemosyne#readme).

## Install

```bash
pip install "mnemosyne-rag[cpu]"
```

FAISS is not a core dependency. The `cpu` extra pulls `faiss-cpu` from PyPI; the preferred
path installs `faiss-cpu` or `faiss-gpu` from conda-forge (see `environment.yml` in the
repo). The distribution is `mnemosyne-rag`; the import package and CLI are `mnemosyne`.

## Quickstart

Requires [Ollama](https://ollama.com/download) running locally.

```bash
ollama pull bge-m3          # embeddings
ollama pull qwen2.5:1.5b    # tiny chat model

mnemosyne ingest ubiquiti                                 # build the index for a pack
mnemosyne ask ubiquiti "How do I adopt a UniFi switch?"   # grounded answer + citations
mnemosyne chat ubiquiti                                   # interactive, with history
mnemosyne packs                                           # list packs + index status
```

## Serve

```bash
mnemosyne-mcp    # MCP stdio server (list_packs / ask / search) for coding agents
mnemosyne-http   # FastAPI server on 127.0.0.1:8088 (GET /health, POST /ask, POST /search)
```

## Learn more

- [Full README](https://github.com/freed-dev-llc/mnemosyne#readme): the idea, how it works, technology choices
- [RAG-101](https://github.com/freed-dev-llc/mnemosyne/blob/main/docs/RAG-101.md): RAG from first principles
- [Knowledge packs](https://github.com/freed-dev-llc/mnemosyne/blob/main/docs/KNOWLEDGE_PACKS.md): build your own expert
- [Architecture](https://github.com/freed-dev-llc/mnemosyne/blob/main/docs/ARCHITECTURE.md): modules and data flow

## License

[Apache-2.0](https://github.com/freed-dev-llc/mnemosyne/blob/main/LICENSE).
