"""RagPipeline caching in the shared query service (offline, no Ollama/network).

``service.RagPipeline`` is patched with a counting fake, following the monkeypatch idiom in
``tests/test_packs.py``, so these tests never construct a real embedder or FAISS store.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

import pytest

from mnemosyne import service
from mnemosyne.config import Settings
from mnemosyne.pipeline import RagAnswer


class _FakePack:
    """A minimal stand-in for ``KnowledgePack``: the cache only ever reads ``.name``."""

    def __init__(self, name: str) -> None:
        self.name = name


class _CountingRagPipeline:
    """Fake ``RagPipeline`` that counts constructions and mirrors the real "no index" error.

    ``instances`` records one entry per *successful* construction; ``construct_calls`` counts
    every attempt, successful or not, so a test can tell "never cached" apart from "never
    constructed".
    """

    instances: ClassVar[list[str]] = []
    construct_calls: ClassVar[int] = 0

    def __init__(self, pack: _FakePack, settings: Settings) -> None:
        _CountingRagPipeline.construct_calls += 1
        path = service.index_mod.index_dir(pack.name, settings)
        if not service.index_mod.index_exists(path):
            raise FileNotFoundError(f"No index for pack '{pack.name}'. Build it first.")
        self.pack = pack
        _CountingRagPipeline.instances.append(pack.name)

    def ask(self, question: str, k: int | None = None) -> RagAnswer:
        return RagAnswer(question=question, text=f"answer from {self.pack.name}", sources=[])

    def retrieve(self, question: str, k: int | None = None) -> list[object]:
        return []


@pytest.fixture(autouse=True)
def _reset_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with an empty cache and a zeroed construction counter."""
    monkeypatch.setattr(service, "_pipeline_cache", {})
    _CountingRagPipeline.instances = []
    _CountingRagPipeline.construct_calls = 0


def _build_index_dir(tmp_path: Path, pack_name: str) -> Path:
    """A fake built index: only ``index.faiss``'s existence/mtime matter to the cache."""
    path = tmp_path / pack_name
    path.mkdir(parents=True)
    (path / "index.faiss").write_bytes(b"fake-index")
    return path


def _wire(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Patch the service module's ``RagPipeline``, ``get_pack``, and ``get_settings``."""
    monkeypatch.setattr(service, "RagPipeline", _CountingRagPipeline)
    monkeypatch.setattr(service, "get_pack", lambda name: _FakePack(name))
    monkeypatch.setattr(service, "get_settings", lambda: Settings(knowledge_dir=tmp_path))


def test_repeated_ask_reuses_one_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _build_index_dir(tmp_path, "pack1")
    _wire(monkeypatch, tmp_path)

    service.ask("pack1", "question one")
    service.ask("pack1", "question two")

    assert _CountingRagPipeline.instances == ["pack1"]
    assert _CountingRagPipeline.construct_calls == 1


def test_repeated_search_reuses_one_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_index_dir(tmp_path, "pack1")
    _wire(monkeypatch, tmp_path)

    service.search("pack1", "query one")
    service.search("pack1", "query two")

    assert _CountingRagPipeline.instances == ["pack1"]
    assert _CountingRagPipeline.construct_calls == 1


def test_fingerprint_bump_forces_a_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _build_index_dir(tmp_path, "pack1")
    _wire(monkeypatch, tmp_path)

    service.ask("pack1", "question one")

    # Simulate a re-ingest rewriting index.faiss: bump the mtime forward explicitly so the
    # change is detected regardless of the filesystem's timestamp resolution.
    index_file = path / "index.faiss"
    bumped_ns = index_file.stat().st_mtime_ns + 1_000_000
    os.utime(index_file, ns=(bumped_ns, bumped_ns))

    service.ask("pack1", "question two")

    assert _CountingRagPipeline.instances == ["pack1", "pack1"]
    assert _CountingRagPipeline.construct_calls == 2


def test_unchanged_index_is_not_rebuilt_on_stat_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cache hit still stats the file (cheap) but must not reconstruct the pipeline."""
    _build_index_dir(tmp_path, "pack1")
    _wire(monkeypatch, tmp_path)

    for _ in range(3):
        service.ask("pack1", "same question every time")

    assert _CountingRagPipeline.construct_calls == 1


def test_independent_packs_get_independent_cache_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_index_dir(tmp_path, "pack1")
    _build_index_dir(tmp_path, "pack2")
    _wire(monkeypatch, tmp_path)

    service.ask("pack1", "q")
    service.ask("pack2", "q")
    service.ask("pack1", "q again")
    service.ask("pack2", "q again")

    assert _CountingRagPipeline.construct_calls == 2
    assert set(_CountingRagPipeline.instances) == {"pack1", "pack2"}


def test_index_deleted_between_check_and_stat_raises_clean_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent re-ingest deleting index.faiss after the existence check must surface the
    clean "No index for pack" error, not a raw FileNotFoundError from stat()."""
    path = _build_index_dir(tmp_path, "pack1")
    _wire(monkeypatch, tmp_path)

    real_index_exists = service.index_mod.index_exists

    def racing_index_exists(p: Path) -> bool:
        result = real_index_exists(p)
        if result:
            (path / "index.faiss").unlink()  # the race: gone before stat()
        return result

    monkeypatch.setattr(service.index_mod, "index_exists", racing_index_exists)

    with pytest.raises(FileNotFoundError, match="No index for pack"):
        service.ask("pack1", "q")

    assert _CountingRagPipeline.construct_calls == 1
    assert _CountingRagPipeline.instances == []
    assert "pack1" not in service._pipeline_cache


def test_unbuilt_pack_never_caches_and_raises_every_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _wire(monkeypatch, tmp_path)  # tmp_path has no "no-index" subdirectory at all

    with pytest.raises(FileNotFoundError):
        service.ask("no-index", "q1")
    with pytest.raises(FileNotFoundError):
        service.ask("no-index", "q2")

    assert _CountingRagPipeline.instances == []
    assert _CountingRagPipeline.construct_calls == 2  # constructed fresh both times, never cached
    assert "no-index" not in service._pipeline_cache
