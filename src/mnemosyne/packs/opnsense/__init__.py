"""OPNsense firewall knowledge pack (in-tree; third vendor pack, ADR-0027).

Manifest-driven: the base ``KnowledgePack`` reads ``manifest.yaml`` and the ``sources/``
corpus, so this pack needs no Python. A sibling of the ``pfsense`` pack (ADR-0024); OPNsense
is a fork of pfSense but the corpus anchors on OPNsense-distinct facts (the os- plugin system,
Zenarmor, built-in Suricata, the Phalcon MVC GUI), not relabeled shared pf facts.
"""
