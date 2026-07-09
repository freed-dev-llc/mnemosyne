"""Env parsing for the none-words disable knobs: the documented spellings must actually work.

Env vars are always strings, so ``MNEMOSYNE_SCORE_FLOOR=none`` and
``MNEMOSYNE_CHAT_HISTORY_BUDGET=none`` (synonyms: ``null``, empty string; case-insensitive,
stripped) must resolve to ``None`` (knob disabled), while numeric strings keep parsing and
garbage keeps failing validation. Every construction passes ``_env_file=None`` and goes through
``monkeypatch`` so a developer's local ``.env`` cannot flip results. Offline: no Ollama, no
network.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mnemosyne.config import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, field: str, value: str | None) -> Settings:
    """Build Settings from a controlled environment: no ``.env``, one field set (or absent)."""
    env_var = f"MNEMOSYNE_{field.upper()}"
    monkeypatch.delenv(env_var, raising=False)
    if value is not None:
        monkeypatch.setenv(env_var, value)
    return Settings(_env_file=None)


@pytest.mark.parametrize("spelling", ["none", "null", "NONE", " none ", ""])
def test_none_words_disable_the_floor(monkeypatch: pytest.MonkeyPatch, spelling: str) -> None:
    assert _settings(monkeypatch, "score_floor", spelling).score_floor is None


def test_numeric_string_still_parses_as_float(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "score_floor", "1.5").score_floor == 1.5


def test_unset_env_keeps_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "score_floor", None).score_floor == 1.0


def test_garbage_still_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, "score_floor", "bogus")


def test_programmatic_none_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pre-existing Python-side disable is untouched by the env-parsing hook."""
    monkeypatch.delenv("MNEMOSYNE_SCORE_FLOOR", raising=False)
    assert Settings(_env_file=None, score_floor=None).score_floor is None


@pytest.mark.parametrize("spelling", ["none", "null", "NONE", " none ", ""])
def test_none_words_disable_the_history_budget(
    monkeypatch: pytest.MonkeyPatch, spelling: str
) -> None:
    assert _settings(monkeypatch, "chat_history_budget", spelling).chat_history_budget is None


def test_history_budget_numeric_string_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "chat_history_budget", "4000").chat_history_budget == 4000


def test_history_budget_unset_env_keeps_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "chat_history_budget", None).chat_history_budget == 8000


@pytest.mark.parametrize("bad", ["0", "-1", "bogus"])
def test_history_budget_rejects_nonpositive_and_garbage(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, "chat_history_budget", bad)
