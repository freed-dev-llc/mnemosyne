# 5. Expose Mnemosyne over MCP

Date: 2026-06-24

## Status

Accepted

## Context

Mnemosyne's value is being the **evidence layer** other agents ground decisions against. The
CLI and library API serve humans and in-process callers, but coding agents (e.g. Argus's) are
**MCP clients** — they consume tools over the Model Context Protocol. To be callable by them,
Mnemosyne needs an MCP transport. This is roadmap v0.3 ("serve it").

[Argus](https://github.com/freed-dev-llc/argus) already exposes its tools via a `FastMCP`
stdio server (`argus-mcp`), so there is an established pattern to mirror.

## Decision

Ship an MCP **stdio** server (`mnemosyne-mcp`, `src/mnemosyne/mcp_server.py`) built on
`mcp.server.fastmcp.FastMCP`, mirroring Argus. It exposes three tools, thin wrappers over the
existing library:

- `list_packs()` — discoverable packs + whether each has a built index.
- `ask(pack, question, k?)` — a grounded answer with cited sources (full RAG).
- `search(pack, query, k?)` — the top-k raw chunks, for agents that want the evidence to
  reason over themselves.

A local `.mcp.json` registers the server (`command: mnemosyne-mcp`). Tool errors (unknown
pack, no index) are returned as `{"error": ...}` rather than raised, so a client gets a usable
message instead of a transport failure.

## Consequences

- Any MCP client can ground answers in Mnemosyne with one registration — the same way it adds
  Argus. Argus *discovers* a vendor; Mnemosyne *explains* it; an agent can call both.
- **The server needs `MNEMOSYNE_OLLAMA_HOST` in its environment.** MCP clients that spawn the
  server with a stripped environment must pass it through (an `env` block in their `.mcp.json`,
  or an inherited shell env). A local `.mcp.json` stays portable (defaults to
  `localhost:11434`); host-specific routing (e.g. a remote Ollama) is set in the environment.
- `mcp` is now a runtime dependency.
- Validated end-to-end over the real protocol (initialize → list_tools → call_tool) against a
  remote Ollama: `list_packs`, `ask`, and `search` all return correctly.
- HTTP/SSE transport and auth are deferred until a non-local consumer needs them.
