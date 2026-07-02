"""Generation: text to answer, via a selectable chat backend.

Kept deliberately thin: the *grounding* (use only the retrieved context, cite sources,
admit when the answer isn't there) lives in ``prompts.py``. This module just builds the
client. The chat backend is chosen by ``chat_provider``: the default ``ollama`` keeps the
local-first path, while ``openai`` targets any OpenAI-compatible server (vLLM, llama.cpp's
server, LM Studio). Embeddings are unaffected and stay on Ollama.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .config import Settings, get_settings


def get_chat_model(
    model: str | None = None,
    settings: Settings | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """Return a chat client for ``model`` (default: settings), per ``chat_provider``.

    ``ollama`` (default) builds a :class:`ChatOllama`; ``openai`` builds a
    :class:`ChatOpenAI` against ``openai_chat_base_url``. Selecting ``openai`` without that
    base URL raises :class:`ValueError`.
    """
    settings = settings or get_settings()
    resolved_temperature = settings.temperature if temperature is None else temperature

    if settings.chat_provider == "openai":
        if not settings.openai_chat_base_url:
            raise ValueError(
                "chat_provider='openai' requires MNEMOSYNE_OPENAI_CHAT_BASE_URL "
                "(the OpenAI-compatible chat endpoint, e.g. http://localhost:8000/v1)."
            )
        return ChatOpenAI(
            model=model or settings.chat_model,
            base_url=settings.openai_chat_base_url,
            api_key=SecretStr(settings.openai_api_key or "not-needed"),
            temperature=resolved_temperature,
        )

    return ChatOllama(
        model=model or settings.chat_model,
        base_url=settings.ollama_host,
        temperature=resolved_temperature,
    )
