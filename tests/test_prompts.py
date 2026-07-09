"""Prompt assembly: grounding, citations, and optional chat history."""

from __future__ import annotations

from langchain_core.documents import Document

from mnemosyne.prompts import (
    DEFAULT_SYSTEM_PROMPT,
    build_messages,
    format_context,
    render_history,
)


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


def test_render_history_empty_turns() -> None:
    assert render_history([], budget=8000) == ("", False)


def test_render_history_none_budget_keeps_all() -> None:
    turns = [("q1", "a1"), ("q2", "a2")]
    text, truncated = render_history(turns, budget=None)
    assert truncated is False
    assert "q1" in text and "q2" in text


def test_render_history_under_budget_keeps_all() -> None:
    turns = [("q1", "a1"), ("q2", "a2")]
    text, truncated = render_history(turns, budget=8000)
    assert truncated is False
    assert text == "User: q1\n\nAssistant: a1\n\nUser: q2\n\nAssistant: a2"


def test_render_history_over_budget_drops_oldest() -> None:
    # Each rendered turn is 23 chars; a budget between one and two turns keeps only the newest.
    turns = [("q1", "a1"), ("q2", "a2")]
    text, truncated = render_history(turns, budget=30)
    assert truncated is True
    assert "q1" not in text
    assert text == "User: q2\n\nAssistant: a2"


def test_render_history_keeps_oversize_newest_turn() -> None:
    turns = [("q1", "a1"), ("q2", "a very long answer that alone exceeds the tiny budget")]
    text, truncated = render_history(turns, budget=5)
    assert truncated is True  # the older turn was dropped
    assert "q2" in text and "q1" not in text


def test_render_history_keeps_chronological_order() -> None:
    turns = [("q1", "a1"), ("q2", "a2"), ("q3", "a3")]
    # A budget wide enough for the two newest turns keeps them oldest-first.
    text, _ = render_history(turns, budget=50)
    assert text.index("q2") < text.index("q3")
    assert "q1" not in text
