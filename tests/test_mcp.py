"""MCP server: tool registration + offline list_packs (no Ollama/network)."""

from __future__ import annotations

import asyncio

from mnemosyne import mcp_server, service


def test_list_packs_reports_known_packs() -> None:
    packs = service.list_packs()
    names = {p["name"] for p in packs}
    assert {"ubiquiti", "general"} <= names
    for p in packs:
        assert {"name", "title", "built"} <= p.keys()
        assert isinstance(p["built"], bool)


def test_tools_are_registered() -> None:
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"list_packs", "ask", "search"} <= names


def test_ask_unknown_pack_returns_error_not_raise() -> None:
    out = mcp_server.ask("does-not-exist", "anything")
    assert "error" in out and "does-not-exist" in out["error"]
