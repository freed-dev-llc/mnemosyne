# 9. Selectable chat backend (Ollama or OpenAI-compatible)

Date: 2026-06-28

## Status

Accepted

## Context

Mnemosyne generates answers through one local Ollama chat model (ADR-0002). Some users
already run an OpenAI-compatible inference server (vLLM, llama.cpp's server, LM Studio) and
want Mnemosyne to talk to it for chat instead of standing up Ollama as a second runtime.
Ollama stays the default and the local-first baseline; the goal is not to force it on people
who have already chosen a different OpenAI-API-speaking backend for generation.

Two shapes were considered:

- A full provider abstraction covering both chat and embeddings, with a registry and
  per-provider clients.
- A narrow chat-only switch that branches between two LangChain clients and leaves
  embeddings untouched.

## Decision

- Add a `chat_provider` setting (`ollama` | `openai`, default `ollama`).
  `llm.get_chat_model` branches on it: `openai` returns a `langchain_openai.ChatOpenAI`
  pointed at `openai_chat_base_url` with `openai_api_key`; otherwise it returns the existing
  `ChatOllama`. The factory return type widens to `BaseChatModel` so callers stay
  client-agnostic (they already use the common chat interface, so no call site changes).
- `langchain-openai` becomes a **core** dependency, not an optional extra. The chat backend
  is a first-class runtime choice and `get_chat_model` imports the client unconditionally;
  putting it behind an extra would let a default install fail with an `ImportError` the
  moment someone set `chat_provider=openai`. (FAISS stays an extra for a separate reason in
  ADR-0004: it comes from conda-forge, not PyPI.)
- Selecting `openai` with no `openai_chat_base_url` raises a `ValueError` naming the env var
  `MNEMOSYNE_OPENAI_CHAT_BASE_URL`, so a misconfiguration fails fast with the fix in the
  message.
- Embeddings are out of scope. They stay Ollama-only. The mirror knob names
  (`embedding_provider`, `openai_embedding_base_url`) are reserved in `config.py` comments
  only: the design intent is recorded, no behaviour is added. A split embedding backend is a
  larger, separate change because chunks and queries must use the same embedding model.

## Consequences

- A user with an OpenAI-compatible chat server sets three env vars
  (`MNEMOSYNE_CHAT_PROVIDER=openai`, `MNEMOSYNE_OPENAI_CHAT_BASE_URL`,
  `MNEMOSYNE_OPENAI_API_KEY`) and keeps Ollama only for embeddings. The default install and
  default behaviour are unchanged.
- The default dependency set grows by `langchain-openai` and its `openai` / `tiktoken`
  transitive packages. That is the accepted cost of making the chat backend swappable out of
  the box.
- Mixing an OpenAI chat model with Ollama embeddings is fine because the two stages are
  independent. A future embedding-provider switch will be its own ADR.
