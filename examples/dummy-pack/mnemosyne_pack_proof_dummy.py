"""Throwaway proof-of-packaging fixture for issue #61 Candidate Step B.

Not a real knowledge pack: no corpus, never ingested, never asked. It exists only to
prove that a knowledge pack packaged and pip-installed as its own distribution registers
itself with Mnemosyne through a real ``mnemosyne.knowledge_packs`` entry point, exercising
the unpatched ``importlib.metadata.entry_points()`` call inside
``mnemosyne.packs.registry.discover_packs()`` end to end.
"""

from __future__ import annotations

from mnemosyne.packs.base import KnowledgePack


class DummyProofPack(KnowledgePack):
    """A throwaway pack proving out-of-tree entry-point discovery works for real.

    Registered under the ``dummy-installed-pack`` entry point declared in this package's
    own ``pyproject.toml``. Deliberately adds nothing beyond the base ``KnowledgePack``:
    it is never ingested and never asked.
    """
