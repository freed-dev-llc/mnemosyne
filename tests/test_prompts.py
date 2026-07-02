"""Prompt assembly: grounding, citations, and optional chat history."""

from __future__ import annotations

from langchain_core.documents import Document

from mnemosyne.prompts import DEFAULT_SYSTEM_PROMPT, build_messages, format_context


def test_format_context_numbers_and_labels_sources() -> None:
    docs = [
        Document(page_content="alpha", metadata={"title": "A"}),
        Document(page_content="beta", metadata={"title": "B", "page": 3}),
    ]
    out = format_context(docs)
    assert "[1] (source: A)" in out
    assert "[2] (source: B, p.3)" in out
    assert "alpha" in out and "beta" in out


def test_build_messages_uses_system_and_question() -> None:
    msgs = build_messages("be terse", "CTX", "what?")
    assert msgs[0].content == "be terse"
    assert "CTX" in msgs[1].content
    assert "what?" in msgs[1].content
    # No chat history requested -> the section is omitted.
    assert "Chat History" not in msgs[1].content


def test_build_messages_threads_chat_history() -> None:
    msgs = build_messages("", "CTX", "follow up?", chat_history="User: hi\n\nAssistant: hello")
    assert msgs[0].content == DEFAULT_SYSTEM_PROMPT  # empty persona falls back to default
    assert "Chat History" in msgs[1].content
    assert "hello" in msgs[1].content
