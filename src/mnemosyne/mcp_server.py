"""FastMCP server exposing Mnemosyne retrieval to coding agents over stdio.

Lets any MCP client (e.g. Argus's coding agents) ground decisions in Mnemosyne's
knowledge packs via three tools: ``list_packs`` / ``ask`` / ``search``. It is the evidence
layer made callable, a thin wrapper over :mod:`mnemosyne.service`.

Run over stdio (register in an ``.mcp.json``):  ``mnemosyne-mcp``
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import service

mcp = FastMCP("mnemosyne")


def _error(exc: Exception) -> dict[str, Any]:
    return {"error": str(exc.args[0] if exc.args else exc)}


@mcp.tool()
def list_packs() -> list[dict[str, Any]]:
    """List Mnemosyne knowledge packs and whether each has a built index."""
    return service.list_packs()


@mcp.tool()
def ask(pack: str, question: str, k: int | None = None) -> dict[str, Any]:
    """Ask a knowledge pack a question; returns a grounded answer with cited sources.

    pack: pack name (from list_packs). question: a natural-language question.
    k: optional number of chunks to retrieve (defaults to the pack's setting).
    """
    try:
        return service.ask(pack, question, k)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        return _error(exc)


@mcp.tool()
def search(pack: str, query: str, k: int | None = None) -> dict[str, Any]:
    """Retrieve the top-k most relevant chunks from a pack (no generation).

    Use when you want the raw evidence to reason over yourself rather than a written answer.
    """
    try:
        return service.search(pack, query, k)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        return _error(exc)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
