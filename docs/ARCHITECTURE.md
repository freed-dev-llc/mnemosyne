# Architecture

> Read [`RAG-101.md`](RAG-101.md) first for the *why*. This doc maps each stage to the
> module that owns it, and explains how the pieces fit together at runtime.

## Module map

Every box in the RAG pipeline is one small, single-purpose module under
`src/mnemosyne/`. They are deliberately thin and readable — this is a repo for *learning*
the pipeline, so each file should fit in your head.

| Module | Owns | Key surface |
| --- | --- | --- |
| `config.py` | Settings from env / `.env` | `Settings` (Ollama host, default models, paths) |
| `loaders.py` | Files → text + metadata | `load_documents(paths) -> list[Document]` |
| `chunking.py` | Text → retrievable chunks | `chunk_documents(docs, size, overlap)` |
| `embeddings.py` | Text → vectors (Ollama) | `get_embeddings(model)` |
| `index.py` | Build / save / load FAISS | `build_index`, `load_index`, `index_path` |
| `pipeline.py` | The RAG chain itself | `ingest(pack)`, `RagPipeline.ask(question)` |
| `prompts.py` | Expert system + RAG prompt | `build_prompt(pack, context, question)` |
| `llm.py` | Text → answer (Ollama or OpenAI-compatible chat) | `get_chat_model(model)` |
| `cli.py` | `mnemosyne` command surface | `ingest`, `ask`, `chat`, `packs` |
| `service.py` | Shared query service for the servers | `list_packs`, `ask`, `search` |
| `mcp_server.py` | FastMCP stdio server (`mnemosyne-mcp`) | `list_packs` / `ask` / `search` MCP tools |
| `http_server.py` | FastAPI server (`mnemosyne-http`) | `/health` · `/packs` · `/ask` · `/search` |
| `packs/` | Knowledge-pack framework | `KnowledgePack`, `registry`, in-tree `ubiquiti` |

## Data flow

### Ingest (offline)

```
KnowledgePack.manifest
        │ sources
        ▼
loaders.load_documents ─► chunking.chunk_documents ─► embeddings.get_embeddings
                                                              │
                                                              ▼
                                          index.build_index ─► knowledge/<pack>/index.faiss
```

`mnemosyne ingest <pack>` resolves the pack from the registry, loads its sources, chunks
and embeds them with the pack's configured models, and writes a FAISS index plus a small
`meta.json` (models used, chunk settings, doc count) next to it. Re-running rebuilds it.

### Ask (online)

```
question ─► embeddings (same model) ─► index.load_index.similarity_search(k)
                                                  │ top-k chunks (+ metadata)
                                                  ▼
                              prompts.build_prompt ─► llm.get_chat_model ─► answer + citations
```

`mnemosyne ask <pack> "<question>"` loads the saved index, retrieves the top-k chunks
(dropping any past the relevance floor, so an off-topic question retrieves nothing and is
answered "not in the knowledge base" without a generation call), builds a grounded prompt
from the pack's system persona, and streams an answer back with `[n]` citations resolved to
source documents.

## Why these boundaries

- **The pack owns *what*; the pipeline owns *how*.** A pack declares its corpus, models,
  chunking, and persona (data). The pipeline modules are generic machinery that work for
  *any* pack. Adding an expert never means editing the pipeline.
- **The index is an artifact, not a service.** FAISS writes a file. That keeps ingest and
  ask decoupled (rebuild the index without touching query code), makes indices shippable,
  and avoids running a vector database for a home/lab tool.
- **Ollama is the default runtime dependency.** One local service provides both embeddings and
  generation, so the default install needs no API keys and nothing leaves the machine. The
  chat backend is swappable: setting `chat_provider=openai` points generation at any
  OpenAI-compatible server (vLLM, llama.cpp, LM Studio) via `get_chat_model`, while embeddings
  stay on Ollama (ADR-0009).

## Configuration

Settings resolve in this order: explicit CLI flag → pack manifest → `.env` / environment →
built-in default. See [`.env.example`](../.env.example). The defaults
(`bge-m3`, `qwen2.5:1.5b`, `chunk_size=500 / chunk_overlap=150 / k=5`,
`OLLAMA_HOST=http://localhost:11434`) follow the
[rag_ollama](https://github.com/MariyaSha/rag_ollama) tutorial and run on a CPU-only box.
The environment itself is managed with mamba/conda so FAISS (CPU or GPU) comes from
conda-forge — see [ADR-0004](architecture/adr/0004-conda-mamba-environment.md). PDFs load
via LangChain's `PyPDFLoader` (one Document per page, with citable page numbers).

## Serving

Beyond the CLI, the same query logic is exposed to other services and agents. The shared
`service.py` (`list_packs` / `ask` / `search`) backs two shipped transports:

- **`mcp_server.py`** — a FastMCP stdio server (`mnemosyne-mcp`) exposing `list_packs` / `ask`
  / `search` so coding agents and other services can call Mnemosyne as an MCP tool (ADR-0005).
  It honors `MNEMOSYNE_OLLAMA_HOST` from its environment and is registered via a local `.mcp.json`.
- **`http_server.py`** — a FastAPI server (`mnemosyne-http`, default `127.0.0.1:8088`) serving
  `/health` · `/packs` · `/ask` · `/search`, for web UIs/services that can't speak MCP (e.g. an
  "ask the brain" box in the Argus dashboard), called server-to-server.

### Consuming it from another host

The MCP server speaks **stdio only**; it opens no network port (HTTP/SSE and auth are deferred
until a non-local consumer needs them, ADR-0005). To call it from another machine on an
overlay/mesh network (e.g. an Argus host), register a stdio MCP server whose command SSHes into
the Mnemosyne host and execs `mnemosyne-mcp`, piping MCP over the SSH connection. A local
`.mcp.json` uses this shape, SSHing to the Mnemosyne host's mesh address so the same registration
works unchanged from any mesh host:

```json
"mnemosyne": {
  "type": "stdio",
  "command": "ssh",
  "args": ["-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
           "-o", "StrictHostKeyChecking=accept-new", "<user>@<mnemosyne-host>",
           "cd /opt/mnemosyne && exec /opt/mnemosyne/.venv/bin/mnemosyne-mcp"]
}
```

The remote `cd` is load-bearing: `knowledge/` resolves relative to cwd, so the index is only found
from the install root. Two prerequisites on the calling host: key-based SSH (`BatchMode=yes` never
prompts, so a password would fail), and a pre-seeded host key
(`ssh-keyscan -H <mnemosyne-host> >> ~/.ssh/known_hosts`); a changed key under BatchMode surfaces
as a `-32000` reconnect failure. When the server runs on the Mnemosyne host, where Ollama is local,
the default `OLLAMA_HOST` is correct; an `env` block on the client does not cross SSH, so if Ollama
moves, set `MNEMOSYNE_OLLAMA_HOST` inside the remote command
(`exec env MNEMOSYNE_OLLAMA_HOST=... mnemosyne-mcp`). A caller that can't speak MCP uses the
`mnemosyne-http` server above instead.

## Where things will grow

- **`eval/` (v0.2)** — retrieval hit-rate + answer-faithfulness harness so pipeline changes
  are measurable.
- **More packs** — vendor-pack parity with Argus (see [ROADMAP.md](ROADMAP.md)).

Design decisions are recorded as ADRs in [`architecture/adr/`](architecture/adr/).
