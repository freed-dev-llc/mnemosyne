"""The Ubiquiti / UniFi knowledge pack.

This is the in-tree worked example, mirroring Argus's in-tree UniFi *vendor* pack: Argus
discovers UniFi devices; Mnemosyne explains UniFi. Most behaviour is manifest-driven (see
``manifest.yaml``); the one override is title cleanup for fetched Help Center pages.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from ..base import KnowledgePack

# Separators a Help Center title may use before the site-name suffix: en-dash, em-dash, hyphen.
_DASHES = (chr(0x2013), chr(0x2014), "-")
_HELP_CENTER_SUFFIX = "Ubiquiti Help Center"


class UbiquitiPack(KnowledgePack):
    """Ubiquiti / UniFi networking expert.

    Fetched Help Center pages carry a "... Ubiquiti Help Center" title suffix; we strip it
    so citations read cleanly (e.g. ``[1] (source: UniFi - Device Adoption)``).
    """

    @staticmethod
    def _clean_title(title: str) -> str:
        text = title.strip()
        if not text.endswith(_HELP_CENTER_SUFFIX):
            return text
        head = text[: -len(_HELP_CENTER_SUFFIX)].rstrip()
        for dash in _DASHES:
            if head.endswith(dash):
                return head[: -len(dash)].rstrip()
        return head

    def load(
        self, *, local_only: bool = False, staging_dir: Path | str | None = None
    ) -> list[Document]:
        docs = super().load(local_only=local_only, staging_dir=staging_dir)
        for doc in docs:
            title = doc.metadata.get("title")
            if isinstance(title, str):
                doc.metadata["title"] = self._clean_title(title)
        return docs
