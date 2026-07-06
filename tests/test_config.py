"""score_floor env parsing: the documented disable spelling must actually work.

Env vars are always strings, so ``MNEMOSYNE_SCORE_FLOOR=none`` (synonyms: ``null``, empty
string; case-insensitive, stripped) must resolve to ``None`` (floor disabled), while numeric
strings keep parsing as floats and garbage keeps failing validation. Every construction
passes ``_env_file=None`` and goes through ``monkeypatch`` so a developer's local ``.env``
cannot flip results. Offline: no Ollama, no network.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mnemosyne.config import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, floor: str | None) -> Settings:
    """Build Settings from a controlled environment: no ``.env``, floor set (or absent)."""
    monkeypatch.delenv("MNEMOSYNE_SCORE_FLOOR", raising=False)
    if floor is not None:
        monkeypatch.setenv("MNEMOSYNE_SCORE_FLOOR", floor)
    return Settings(_env_file=None)


@pytest.mark.parametrize("spelling", ["none", "null", "NONE", " none ", ""])
def test_none_words_disable_the_floor(monkeypatch: pytest.MonkeyPatch, spelling: str) -> None:
    assert _settings(monkeypatch, spelling).score_floor is None


def test_numeric_string_still_parses_as_float(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, "1.5").score_floor == 1.5


def test_unset_env_keeps_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _settings(monkeypatch, None).score_floor == 1.0


def test_garbage_still_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        _settings(monkeypatch, "bogus")


def test_programmatic_none_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pre-existing Python-side disable is untouched by the env-parsing hook."""
    monkeypatch.delenv("MNEMOSYNE_SCORE_FLOOR", raising=False)
    assert Settings(_env_file=None, score_floor=None).score_floor is None
