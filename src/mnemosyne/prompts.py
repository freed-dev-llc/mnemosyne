"""Generate, part 1 — turn retrieved chunks into a grounded, citable prompt.

Two properties keep RAG honest and live here, not in the model:
  * **Grounding** — answer using ONLY the retrieved context, and admit when it isn't there.
  * **Citations** — each chunk carries its source metadata, so the answer can point back
    at exactly which document it came from.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

DEFAULT_SYSTEM_PROMPT = (
    "You are a precise expert assistant. Answer the user's question using ONLY the "
    "context provided below. Cite the sources you use inline as [n], matching the "
    "numbered context entries. If the context does not contain the answer, say so "
    "plainly — do not invent facts or steps."
)


def format_context(docs: list[Document]) -> str:
    """Render retrieved chunks as a numbered, citable context block."""
    parts: list[str] = []
    for i, doc in enumerate(docs, 1):
        title = doc.metadata.get("title") or doc.metadata.get("source") or "unknown"
        page = doc.metadata.get("page")
        label = f"{title}, p.{page}" if page else title
        parts.append(f"[{i}] (source: {label})\n{doc.page_content}")
    return "\n\n".join(parts)


def build_messages(
    system_prompt: str,
    context: str,
    question: str,
    chat_history: str = "",
) -> list[BaseMessage]:
    """Assemble the system + human messages for a grounded RAG turn.

    ``chat_history`` (optional) is a plain-text running transcript threaded back into the
    prompt so multi-turn ``chat`` sessions stay coherent — there is no automatic memory.
    """
    parts: list[str] = []
    if chat_history.strip():
        parts.append(f"Chat History:\n{chat_history.strip()}\n")
    parts.append(f"Context:\n{context}\n")
    parts.append(f"Question: {question}\n")
    parts.append("Answer using only the context above, with inline [n] citations.")
    return [
        SystemMessage(content=system_prompt or DEFAULT_SYSTEM_PROMPT),
        HumanMessage(content="\n".join(parts)),
    ]
