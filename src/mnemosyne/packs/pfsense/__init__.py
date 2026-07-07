"""pfSense firewall knowledge pack (in-tree; second vendor pack, ADR-0024).

Manifest-driven: the base ``KnowledgePack`` reads ``manifest.yaml`` and the ``sources/``
corpus, so this pack needs no Python. A ``pack.py`` subclass is only warranted once fetched
vendor pages need title cleanup (a later roadmap step).
"""
