"""Runtime settings, resolved from the environment and an optional ``.env`` file.

Resolution order for any knob is: explicit CLI flag → pack manifest → environment /
``.env`` (these settings) → built-in default. Env vars are prefixed ``MNEMOSYNE_``,
e.g. ``MNEMOSYNE_CHAT_MODEL=qwen2.5:7b``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global, pack-independent defaults."""

    model_config = SettingsConfigDict(
        env_prefix="MNEMOSYNE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama runtime (provides both embeddings and chat).
    # Defaults follow the rag_ollama tutorial this project is based on: a tiny chat model
    # and the bge-m3 embedder, both CPU-friendly.
    ollama_host: str = "http://localhost:11434"
    embedding_model: str = "bge-m3"
    chat_model: str = "qwen2.5:1.5b"
    temperature: float = 0.1

    # Chat backend selection. Default ``ollama`` keeps the local-first promise; ``openai``
    # points the *chat* model at any OpenAI-compatible server (vLLM, llama.cpp's server,
    # LM Studio). Only generation is affected: embeddings always come from Ollama.
    chat_provider: Literal["ollama", "openai"] = "ollama"
    # Required when ``chat_provider='openai'``: the OpenAI-compatible base URL, e.g.
    # ``http://localhost:8000/v1``. Empty by default so ``llm.get_chat_model`` raises a clear
    # error if ``openai`` is selected without it.
    openai_chat_base_url: str = ""
    # API key sent to that endpoint. Local OpenAI-compatible servers usually ignore it; a real
    # key (if your endpoint needs one) flows in via ``MNEMOSYNE_OPENAI_API_KEY`` / ``.env``.
    openai_api_key: str = ""
    # Reserved (design-only, NOT implemented this step): a future embedding-provider switch
    # mirroring the chat one would add ``embedding_provider`` and ``openai_embedding_base_url``
    # here. The names are reserved so the knob is discoverable; embeddings stay Ollama-only
    # because chunks and queries must use the same embedding model.

    # Where built FAISS indices live (gitignored, rebuilt by ``ingest``)
    knowledge_dir: Path = Path("knowledge")

    # A directory *outside* the repo where a contributor manually stages third-party docs
    # that must never enter git (issue #60): help.ui.com and similar sites can block a
    # server's IP, and some corpora aren't safe to hold in version control even
    # transiently. ``ingest`` looks under ``<staging_dir>/<pack-name>/`` and folds in any
    # supported file found there, same as ``sources/``. Default unset = no staging, zero
    # behavior change: this is the load-bearing default; do not default to a path.
    staging_dir: Path | None = None

    # Chunking + retrieval defaults (a pack may override these).
    chunk_size: int = 500
    chunk_overlap: int = 150
    top_k: int = 5

    # Normalize embeddings to unit length before indexing and at query time. bge-m3 is a
    # cosine-similarity model, and L2 over unit vectors ranks identically to cosine, so this
    # pairs the metric to the model. Default False keeps the historical L2-over-raw-vectors
    # behavior (and any index built before this knob existed); it must match at build and
    # query time, so an index records the value it was built with in meta.json.
    faiss_normalize: bool = False

    # Relevance floor: the maximum embedding distance (lower = more similar) a chunk may have
    # to still count as relevant. Retrieval drops any retrieved chunk beyond it, so a query
    # with no close-enough chunk returns nothing and `ask` answers "not in the knowledge base"
    # instead of feeding the model unrelated context. Units are the index's distance metric
    # (L2 over unit-norm bge-m3 vectors, range [0, 2]). The default 1.0 was tuned on the
    # ubiquiti eval set: it kept full in-domain recall (18/19, unchanged from no floor) while
    # rejecting 11/12 deliberately off-topic queries. Retune for a different embedding model or
    # corpus; set MNEMOSYNE_SCORE_FLOOR=none (synonyms: null, empty string) to disable and
    # restore the always-return-top-k behavior.
    score_floor: float | None = 1.0

    # Chat transcript budget, in characters of the rendered ``chat`` transcript (the format
    # ``build_messages`` receives). The interactive ``chat`` loop keeps the most recent turns
    # that fit within this many characters and drops older whole turns first, so a long session
    # cannot grow the prompt without bound. The most recent turn is always kept even if it alone
    # exceeds the budget: the model just produced that answer, so it fits the window, and keeping
    # it preserves the immediately-previous-turn reference that chat history exists for. 8000
    # chars measured 2213 tokens (3.6 chars/token) for the default qwen2.5:1.5b, counted via
    # Ollama ``prompt_eval_count`` over README-prose transcripts on 2026-07-09. That is a bit
    # over half of Ollama's default 4096-token context window (per the Ollama FAQ; ``llm.py``
    # does not set ``num_ctx``); the default retrieval payload (k=5 x chunk_size=500 = 2500
    # chars) measured 761 tokens, leaving roughly 1000 tokens for the system prompt, question,
    # and generation in the worst case. Set MNEMOSYNE_CHAT_HISTORY_BUDGET=none (synonyms: null,
    # empty string) to disable the bound and thread the full transcript (the pre-fix behavior).
    chat_history_budget: int | None = Field(default=8000, gt=0)

    @field_validator("score_floor", "chat_history_budget", mode="before")
    @classmethod
    def _none_words_to_none(cls, value: object) -> object:
        """Map the documented disable spellings to ``None`` before numeric parsing.

        Env vars are always strings, and pydantic's numeric parsers reject "none"/"null"
        (``float_parsing`` / ``int_parsing``), so without this hook the disable promised on
        ``score_floor`` and ``chat_history_budget`` was unreachable through the environment.
        Only the three none-words match; any other value passes through unchanged, so numeric
        strings still parse and garbage still raises ``ValidationError``.
        """
        if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
            return None
        return value

    # HTTP server (mnemosyne-http) bind address — for web UIs / services (e.g. an Argus
    # "ask the brain" box) that can't speak MCP.
    http_host: str = "127.0.0.1"
    http_port: int = 8088


def get_settings() -> Settings:
    """Return freshly-resolved settings (cheap; constructs from env each call)."""
    return Settings()
