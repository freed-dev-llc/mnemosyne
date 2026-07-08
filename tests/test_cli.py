"""CLI surface: offline commands + the shared unknown-pack error path (no Ollama/network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from mnemosyne import __version__
from mnemosyne.cli import app
from mnemosyne.pipeline import RagAnswer, Source

runner = CliRunner()


def test_packs_lists_known_packs() -> None:
    result = runner.invoke(app, ["packs"])
    assert result.exit_code == 0
    assert "ubiquiti" in result.output
    assert "general" in result.output


def test_version_prints_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_matches_pyproject() -> None:
    """Guard the 0.6.0/0.6.1 drift: the runtime `__version__` must equal the version
    declared in pyproject.toml, so `mnemosyne version` and `/health` never report stale."""
    import tomllib
    from pathlib import Path

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = tomllib.loads(pyproject.read_text())["project"]["version"]
    assert __version__ == declared


def test_ingest_unknown_pack_dies() -> None:
    result = runner.invoke(app, ["ingest", "does-not-exist"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output


def test_ask_unknown_pack_dies() -> None:
    result = runner.invoke(app, ["ask", "does-not-exist", "hi"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output


def test_chat_unknown_pack_dies() -> None:
    result = runner.invoke(app, ["chat", "does-not-exist"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output


def test_eval_unknown_pack_dies() -> None:
    result = runner.invoke(app, ["eval", "does-not-exist"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output


def test_sweep_unknown_pack_dies() -> None:
    result = runner.invoke(app, ["sweep", "does-not-exist"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output


class _CitingPipeline:
    """A fake RagPipeline whose answer contains an inline ``[1]`` citation marker."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def ask(self, question: str, chat_history: str = "") -> RagAnswer:
        return RagAnswer(question=question, text="Enable tagging on the port [1].", sources=[])


def test_ask_preserves_citation_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inline ``[n]`` citations must survive to the terminal (rich must not eat them)."""
    monkeypatch.setattr("mnemosyne.cli.get_pack", lambda name: SimpleNamespace(name=name))
    monkeypatch.setattr("mnemosyne.cli.RagPipeline", _CitingPipeline)

    result = runner.invoke(app, ["ask", "fake", "hi"])
    assert result.exit_code == 0
    assert "[1]" in result.output


class _SourcedPipeline:
    """A fake RagPipeline whose one source title carries literal rich-markup brackets."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def ask(self, question: str, chat_history: str = "") -> RagAnswer:
        return RagAnswer(
            question=question,
            text="ok",
            sources=[Source(n=1, title="[UDM] setup", source="a.md")],
        )


def test_show_sources_keeps_bracketed_title(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bracketed source title must not be swallowed by rich markup in the sources table."""
    monkeypatch.setattr("mnemosyne.cli.get_pack", lambda name: SimpleNamespace(name=name))
    monkeypatch.setattr("mnemosyne.cli.RagPipeline", _SourcedPipeline)

    result = runner.invoke(app, ["ask", "fake", "hi", "--show-sources"])
    assert result.exit_code == 0
    assert "[UDM]" in result.output


def test_chat_preserves_citation_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chat loop keeps its styled prefix but must not drop ``[n]`` citations either."""
    monkeypatch.setattr("mnemosyne.cli.get_pack", lambda name: SimpleNamespace(name=name))
    monkeypatch.setattr("mnemosyne.cli.RagPipeline", _CitingPipeline)

    result = runner.invoke(app, ["chat", "fake"], input="hi\nexit\n")
    assert result.exit_code == 0
    assert "[1]" in result.output


def test_ingest_missing_local_file_reports_clean_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing ``local:`` source file yields a one-line error, not a raw traceback."""
    monkeypatch.setattr("mnemosyne.cli.get_pack", lambda name: SimpleNamespace(name=name))

    def _raise(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("/no/such/file.md")

    monkeypatch.setattr("mnemosyne.cli.ingest", _raise)

    result = runner.invoke(app, ["ingest", "fake"])
    assert result.exit_code == 1
    assert "/no/such/file.md" in result.output
    assert "Traceback" not in result.output
