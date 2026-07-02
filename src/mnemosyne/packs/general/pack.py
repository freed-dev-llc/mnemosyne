"""The general operating & decision-knowledge pack.

Project-agnostic counterpart to the vendor packs: where ``ubiquiti`` answers "how does this
technology work?", ``general`` answers "how should I make this call?". Behaviour is
manifest-driven; this class exists for discovery and as the extension point if the corpus
ever needs custom preprocessing.
"""

from __future__ import annotations

from ..base import KnowledgePack


class GeneralPack(KnowledgePack):
    """A curated, growing corpus for grounding decisions (how to decide, not how tech works)."""
