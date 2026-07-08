"""``KnowledgePack`` — a corpus plus the config to make it a cited expert.

Most packs need no Python: the base class reads ``manifest.yaml`` and the ``sources/``
directory. Override :meth:`load` only when a corpus needs custom handling (a bespoke
loader, a cleanup pass, custom scraping).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from langchain_core.documents import Document

from ..loaders import SUPPORTED_SUFFIXES, load_documents, load_url

_log = logging.getLogger(__name__)


def _supported_files(directory: Path) -> list[Path]:
    """Loadable files directly inside ``directory``, sorted for a deterministic corpus."""
    return [
        child
        for child in sorted(directory.iterdir())
        if child.is_file() and child.suffix.lower() in SUPPORTED_SUFFIXES
    ]


class KnowledgePack:
    """A discoverable, manifest-driven expert over one corpus."""

    def __init__(self, directory: str | Path, manifest: dict[str, Any] | None = None) -> None:
        self.directory = Path(directory)
        self.manifest: dict[str, Any] = manifest or {}

    @classmethod
    def from_directory(cls, directory: str | Path) -> KnowledgePack:
        """Build a pack from a directory containing a ``manifest.yaml``."""
        directory = Path(directory)
        manifest: dict[str, Any] = {}
        manifest_path = directory / "manifest.yaml"
        if manifest_path.exists():
            loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError(
                    f"{manifest_path} must be a YAML mapping of manifest fields, "
                    f"got {type(loaded).__name__}"
                )
            manifest = loaded
        return cls(directory, manifest)

    # --- manifest-backed properties (None means "fall back to settings") ---

    @property
    def name(self) -> str:
        return self.manifest.get("name") or self.directory.name

    @property
    def title(self) -> str:
        return self.manifest.get("title") or self.name.title()

    @property
    def description(self) -> str:
        return self.manifest.get("description", "")

    @property
    def embedding_model(self) -> str | None:
        return self.manifest.get("embedding_model")

    @property
    def chat_model(self) -> str | None:
        return self.manifest.get("chat_model")

    @property
    def chunk_size(self) -> int | None:
        return self.manifest.get("chunk_size")

    @property
    def chunk_overlap(self) -> int | None:
        return self.manifest.get("chunk_overlap")

    @property
    def top_k(self) -> int | None:
        return self.manifest.get("top_k")

    @property
    def system_prompt(self) -> str | None:
        return self.manifest.get("system_prompt")

    # --- corpus resolution ---

    def _sources_spec(self) -> dict[str, Any]:
        spec_path = self.directory / "sources" / "sources.yaml"
        if spec_path.exists():
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
            if not isinstance(spec, dict):
                raise ValueError(
                    f"{spec_path} must be a YAML mapping (local:/urls:), got {type(spec).__name__}"
                )
            return spec
        return {}

    def resolve_sources(
        self, *, staging_dir: Path | str | None = None
    ) -> tuple[list[Path], list[str]]:
        """Return ``(local_files, urls)`` that make up the corpus.

        Local files = any supported file dropped in ``sources/`` plus explicit ``local:``
        entries in ``sources.yaml``, plus (if ``staging_dir`` is given and exists) any
        supported file dropped there (a manually-fetched, network-free substitute for a
        blocked ``urls:`` fetch, issue #60). URLs come from the ``urls:`` list.
        """
        sources_dir = self.directory / "sources"
        spec = self._sources_spec()

        files: list[Path] = []
        if sources_dir.exists():
            files.extend(_supported_files(sources_dir))
        for rel in spec.get("local", []) or []:
            candidate = (self.directory / rel).resolve()
            if candidate not in {f.resolve() for f in files}:
                files.append(candidate)

        if staging_dir is not None:
            staging_dir = Path(staging_dir)
            if staging_dir.exists():
                files.extend(_supported_files(staging_dir))

        urls = list(spec.get("urls", []) or [])
        return files, urls

    def load(
        self, *, local_only: bool = False, staging_dir: Path | str | None = None
    ) -> list[Document]:
        """Load the full corpus into documents (local files + fetched URLs).

        A URL that fails to fetch is logged and skipped — one unreachable source must not
        abort the whole ingest.

        ``local_only=True`` skips URL resolution entirely (zero network), so ingest is
        deterministic from the local corpus alone — used by CI's retrieval gate so the
        indexed corpus is byte-stable and matches what the floor was measured against.
        ``staging_dir``, if given, is folded into the local corpus by ``resolve_sources``
        regardless of ``local_only``: staged files are already local.
        """
        files, urls = self.resolve_sources(staging_dir=staging_dir)
        docs = load_documents(files)  # type: ignore[arg-type]
        if local_only:
            return docs
        for url in urls:
            try:
                docs.append(load_url(url))
            except Exception as exc:
                _log.warning("Skipping source URL (fetch failed: %s): %s", exc, url)
        return docs
