"""Offline tests for the chat-model factory (``llm.get_chat_model``).

No Ollama, no network: constructing a LangChain chat client does not open a connection, so
we assert on the resolved client type and its configured attributes directly. Attribute
names are the ones the installed clients actually expose (verified against langchain-ollama
and langchain-openai 1.x): ``ChatOllama.model`` / ``base_url`` vs ``ChatOpenAI.model_name``
/ ``openai_api_base``.
"""

from __future__ import annotations

import pytest
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from mnemosyne.config import Settings
from mnemosyne.llm import get_chat_model


def test_defaults_to_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """No provider set -> the default ``ollama`` path builds a ChatOllama."""
    monkeypatch.delenv("MNEMOSYNE_CHAT_PROVIDER", raising=False)
    settings = Settings(_env_file=None)  # ignore any developer .env for a clean default
    assert settings.chat_provider == "ollama"

    model = get_chat_model(settings=settings)
    assert isinstance(model, ChatOllama)
    assert model.model == settings.chat_model
    assert model.base_url == settings.ollama_host

    # A temperature override flows through to the default ollama client.
    overridden = get_chat_model(settings=settings, temperature=0.5)
    assert overridden.temperature == 0.5


def test_openai_provider_builds_chatopenai() -> None:
    """``openai`` with a base URL builds a ChatOpenAI pointed at that endpoint."""
    settings = Settings(
        chat_provider="openai",
        openai_chat_base_url="http://localhost:8000/v1",
        openai_api_key="sk-test",
    )
    model = get_chat_model(model="qwen2.5:7b", settings=settings, temperature=0.0)
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "qwen2.5:7b"
    assert model.openai_api_base == "http://localhost:8000/v1"
    assert model.temperature == 0.0

    # The API key round-trips as a SecretStr carrying the configured value.
    assert isinstance(model.openai_api_key, SecretStr)
    assert model.openai_api_key.get_secret_value() == "sk-test"


def test_openai_provider_empty_key_falls_back_to_placeholder() -> None:
    """An unset API key becomes the keyless-local placeholder at the call site."""
    settings = Settings(
        chat_provider="openai",
        openai_chat_base_url="http://localhost:8000/v1",
        openai_api_key="",
    )
    model = get_chat_model(settings=settings)
    assert isinstance(model, ChatOpenAI)
    assert isinstance(model.openai_api_key, SecretStr)
    assert model.openai_api_key.get_secret_value() == "not-needed"


def test_openai_provider_without_base_url_raises() -> None:
    """``openai`` selected with no base URL fails fast, naming the env var to set."""
    settings = Settings(chat_provider="openai", openai_chat_base_url="")
    with pytest.raises(ValueError, match="MNEMOSYNE_OPENAI_CHAT_BASE_URL"):
        get_chat_model(settings=settings)
