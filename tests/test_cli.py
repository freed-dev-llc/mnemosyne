"""CLI surface: offline commands + the shared unknown-pack error path (no Ollama/network)."""

from __future__ import annotations

from typer.testing import CliRunner

from mnemosyne import __version__
from mnemosyne.cli import app

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
