"""Knowledge packs — the unit of expertise.

A pack bundles a corpus with the config for turning it into a cited expert (models,
chunking, persona). Packs are discovered in-tree (subpackages here with a
``manifest.yaml``) or out-of-tree (a ``mnemosyne.knowledge_packs`` entry point). See
``docs/KNOWLEDGE_PACKS.md`` and ADR-0003.
"""

from __future__ import annotations

from .base import KnowledgePack
from .registry import discover_packs, get_pack

__all__ = ["KnowledgePack", "discover_packs", "get_pack"]
