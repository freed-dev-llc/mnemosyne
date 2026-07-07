"""Pack discovery + manifest behavior (no Ollama/network needed)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from mnemosyne.config import Settings
from mnemosyne.loaders import SUPPORTED_SUFFIXES
from mnemosyne.packs import registry
from mnemosyne.packs.base import KnowledgePack
from mnemosyne.packs.general import GeneralPack
from mnemosyne.packs.registry import discover_packs, get_pack
from mnemosyne.pipeline import ingest


def test_ubiquiti_is_discovered_in_tree() -> None:
    packs = discover_packs()
    assert "ubiquiti" in packs
    # No pack.py subclass: the curated-only pack is manifest-driven by the base KnowledgePack.
    # The fetched help.ui.com harvest (and its Help Center title-cleanup override) was declined
    # on licensing grounds (ADR-0026).
    assert type(packs["ubiquiti"]) is KnowledgePack


def test_general_pack_is_discovered() -> None:
    packs = discover_packs()
    assert "general" in packs
    assert isinstance(packs["general"], GeneralPack)
    pack = packs["general"]
    files, _urls = pack.resolve_sources()
    assert any(f.name == "operating-principles.md" for f in files)


def test_pfsense_is_discovered_in_tree() -> None:
    packs = discover_packs()
    assert "pfsense" in packs
    # No pack.py subclass: the base KnowledgePack handles the local primers (ADR-0024).
    assert type(packs["pfsense"]) is KnowledgePack


def test_manifest_properties_resolve() -> None:
    pack = get_pack("ubiquiti")
    assert pack.name == "ubiquiti"
    assert "UniFi" in pack.title
    assert pack.embedding_model == "bge-m3"
    assert pack.chat_model == "qwen2.5:1.5b"
    assert pack.chunk_size == 500
    assert pack.chunk_overlap == 150
    assert pack.top_k == 5
    assert pack.system_prompt and "ONLY" in pack.system_prompt


def test_seed_corpus_is_resolved_and_loads() -> None:
    pack = get_pack("ubiquiti")
    files, _urls = pack.resolve_sources()
    assert any(f.name == "seed-unifi-concepts.md" for f in files)
    docs = pack.load()
    assert docs, "the seed corpus should make the pack ingestable out of the box"
    assert any("UniFi" in d.page_content for d in docs)


def test_local_only_load_skips_url_fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``load(local_only=True)`` indexes the local corpus and never touches the network."""
    sources = tmp_path / "sources"
    sources.mkdir(parents=True)
    (sources / "note.md").write_text("a local seed note", encoding="utf-8")
    (sources / "sources.yaml").write_text("urls:\n  - https://example.com/page\n", encoding="utf-8")

    calls: list[str] = []

    def _record(url: str, **_: object) -> Document:
        calls.append(url)
        return Document(page_content="REMOTE", metadata={"source": url})

    monkeypatch.setattr("mnemosyne.packs.base.load_url", _record)

    pack = KnowledgePack.from_directory(tmp_path)
    _files, urls = pack.resolve_sources()
    assert urls == ["https://example.com/page"]  # the fake pack really does declare a URL

    docs = pack.load(local_only=True)
    assert calls == []  # no fetch was even attempted
    assert len(docs) == 1
    assert "local seed note" in docs[0].page_content


def test_resolve_sources_folds_in_staged_files(tmp_path: Path) -> None:
    """A file dropped in ``staging_dir`` joins the corpus, same as ``sources/`` (issue #60)."""
    pack_dir = tmp_path / "pack"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "seed.md").write_text("seed content", encoding="utf-8")
    pack = KnowledgePack.from_directory(pack_dir)

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    (staging_dir / "staged.md").write_text("a manually staged page", encoding="utf-8")

    files, _urls = pack.resolve_sources(staging_dir=staging_dir)
    assert {f.name for f in files} == {"seed.md", "staged.md"}


def test_resolve_sources_missing_staging_dir_is_silent(tmp_path: Path) -> None:
    """A ``staging_dir`` that doesn't exist yet contributes zero files and raises no error."""
    pack_dir = tmp_path / "pack"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "seed.md").write_text("seed content", encoding="utf-8")
    pack = KnowledgePack.from_directory(pack_dir)

    files, _urls = pack.resolve_sources(staging_dir=tmp_path / "never-created")
    assert {f.name for f in files} == {"seed.md"}


def test_resolve_sources_and_load_with_no_staging_dir_arg_are_unaffected(tmp_path: Path) -> None:
    """Existing calls with no ``staging_dir`` argument keep working (additive signature)."""
    pack_dir = tmp_path / "pack"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "seed.md").write_text("seed content", encoding="utf-8")
    pack = KnowledgePack.from_directory(pack_dir)

    files, urls = pack.resolve_sources()
    assert {f.name for f in files} == {"seed.md"}
    assert urls == []

    docs = pack.load()
    assert len(docs) == 1
    assert "seed content" in docs[0].page_content


def test_resolve_sources_picks_up_every_supported_suffix(tmp_path: Path) -> None:
    """One file per suffix in ``loaders.SUPPORTED_SUFFIXES`` lands in the corpus, so a
    loader suffix added in ``loaders.py`` reaches pack scanning without a second edit."""
    sources = tmp_path / "sources"
    sources.mkdir(parents=True)
    for suffix in sorted(SUPPORTED_SUFFIXES):
        (sources / f"doc{suffix}").write_text("content", encoding="utf-8")

    pack = KnowledgePack.from_directory(tmp_path)
    files, _urls = pack.resolve_sources()
    assert {f.name for f in files} == {f"doc{suffix}" for suffix in SUPPORTED_SUFFIXES}


def test_local_only_load_still_folds_in_staged_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``local_only=True`` skips URL fetches but still folds in staged files: staging is not
    gated behind ``local_only``, since a staged file is already local."""
    pack_dir = tmp_path / "pack"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "sources.yaml").write_text(
        "urls:\n  - https://example.com/page\n", encoding="utf-8"
    )
    pack = KnowledgePack.from_directory(pack_dir)

    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()
    (staging_dir / "staged.md").write_text("a manually staged page", encoding="utf-8")

    calls: list[str] = []

    def _record(url: str, **_: object) -> Document:
        calls.append(url)
        return Document(page_content="REMOTE", metadata={"source": url})

    monkeypatch.setattr("mnemosyne.packs.base.load_url", _record)

    docs = pack.load(local_only=True, staging_dir=staging_dir)
    assert calls == []  # no fetch was even attempted
    assert len(docs) == 1
    assert "manually staged page" in docs[0].page_content


class _FakeEmbeddings(Embeddings):
    """Deterministic, offline stand-in for a real embedder (no Ollama, no network)."""

    _DIM = 32

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._DIM
        for token in text.lower().split():
            vec[sum(ord(c) for c in token) % self._DIM] += 1.0
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def test_ingest_scans_the_per_pack_staging_subdirectory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``pipeline.ingest()`` resolves ``<staging_dir>/<pack-name>/`` and a staged file's
    content reaches the built index (via ``IngestStats.documents``)."""
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss not installed (the mamba env or the `cpu` extra provides it)")

    pack_dir = tmp_path / "packs" / "demo"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "seed.md").write_text(
        "seed content about the demo pack", encoding="utf-8"
    )
    pack = KnowledgePack.from_directory(pack_dir)
    assert pack.name == "demo"

    staging_root = tmp_path / "staging"
    (staging_root / pack.name).mkdir(parents=True)
    (staging_root / pack.name / "staged.md").write_text(
        "a manually staged unifi help page", encoding="utf-8"
    )
    # A sibling pack's staged directory must not leak into this pack's corpus.
    (staging_root / "other-pack").mkdir(parents=True)
    (staging_root / "other-pack" / "other.md").write_text("not this pack", encoding="utf-8")

    settings = Settings(knowledge_dir=tmp_path / "knowledge", staging_dir=staging_root)
    monkeypatch.setattr(
        "mnemosyne.pipeline.get_embeddings", lambda model, settings: _FakeEmbeddings()
    )

    stats = ingest(pack, settings)
    assert stats.documents == 2  # seed.md + staged.md, not other-pack's file


def test_ingest_with_unset_staging_dir_is_unaffected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default ``staging_dir=None`` (always true in CI) contributes nothing extra."""
    if importlib.util.find_spec("faiss") is None:
        pytest.skip("faiss not installed (the mamba env or the `cpu` extra provides it)")

    pack_dir = tmp_path / "packs" / "demo"
    (pack_dir / "sources").mkdir(parents=True)
    (pack_dir / "sources" / "seed.md").write_text(
        "seed content about the demo pack", encoding="utf-8"
    )
    pack = KnowledgePack.from_directory(pack_dir)

    settings = Settings(knowledge_dir=tmp_path / "knowledge")
    assert settings.staging_dir is None
    monkeypatch.setattr(
        "mnemosyne.pipeline.get_embeddings", lambda model, settings: _FakeEmbeddings()
    )

    stats = ingest(pack, settings)
    assert stats.documents == 1


def test_entry_point_pack_is_discovered_out_of_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pack installed as a ``mnemosyne.knowledge_packs`` entry point is unioned with the
    in-tree packs, proving the out-of-tree discovery path an externally-packaged vendor pack
    would use (mirrors how Argus discovers vendor packs, ADR-0003)."""

    class _FakeEntryPoint:
        name = "dummy-entrypoint-pack"

        def load(self) -> KnowledgePack:
            return KnowledgePack(tmp_path, manifest={"name": "dummy-entrypoint-pack"})

    def _fake_entry_points(*, group: str) -> list[_FakeEntryPoint]:
        if group == registry.ENTRY_POINT_GROUP:
            return [_FakeEntryPoint()]
        return []

    monkeypatch.setattr("mnemosyne.packs.registry.entry_points", _fake_entry_points)

    packs = discover_packs()
    assert "dummy-entrypoint-pack" in packs
    assert "ubiquiti" in packs
    assert "general" in packs

    pack = get_pack("dummy-entrypoint-pack")
    assert isinstance(pack, KnowledgePack)


def test_unknown_pack_raises_with_options() -> None:
    try:
        get_pack("does-not-exist")
    except KeyError as exc:
        assert "ubiquiti" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError for unknown pack")
