"""Ubiquiti / UniFi knowledge pack (in-tree worked example).

Manifest-driven: the base ``KnowledgePack`` reads ``manifest.yaml`` and the ``sources/``
corpus, so this pack needs no Python. The ``pack.py`` title-cleanup subclass was removed
when the fetched help.ui.com harvest was declined on licensing grounds (ADR-0026): with a
curated-only corpus there are no fetched Help Center page titles to clean up.
"""
