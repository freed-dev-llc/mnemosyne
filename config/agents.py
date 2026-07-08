"""Agent registry loader.

Reads config/agents.yaml (repo root) and provides typed accessors
for conductor (Sage, Nova, Vera) and utility (Haiku) agents.
Cached in memory and auto-reloaded when YAML mtime changes.

Usage::

    from config.agents import get_by_name, get_conductors, get_utility

    sage = get_by_name("sage")
    conductors = get_conductors()  # [Sage, Nova, Vera]
    haiku = get_utility()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("config.agents")

# Resolve config directory — agents.yaml is in the same directory as this file
_REGISTRY_PATH = Path(__file__).parent / "agents.yaml"

# Cache by mtime for reload safety
_cache: dict[str, Any] | None = None
_cache_mtime: float = 0.0


def _load_registry() -> dict[str, Any]:
    """Load (or reload) the agent registry YAML, caching by mtime."""
    global _cache, _cache_mtime

    try:
        mtime = os.path.getmtime(_REGISTRY_PATH)
    except OSError:
        log.warning("agents.yaml not found at %s", _REGISTRY_PATH)
        return {}

    if _cache is not None and mtime == _cache_mtime:
        return _cache

    with open(_REGISTRY_PATH) as fh:
        data = yaml.safe_load(fh)

    agents = data.get("agents", {})
    _cache = agents
    _cache_mtime = mtime
    log.debug("Loaded %d agents from %s", len(agents), _REGISTRY_PATH)
    return agents


# =========================================================================
# Public accessors
# =========================================================================


def get_all() -> dict[str, dict]:
    """Return the full agent map {name: {...}}."""
    return dict(_load_registry())


def get_by_type(agent_type: str) -> list[dict]:
    """Return agents whose type matches agent_type."""
    return [a for a in _load_registry().values() if a.get("type") == agent_type]


def get_by_name(name: str) -> dict | None:
    """Look up a single agent by name. Returns None if not found."""
    return _load_registry().get(name)


def get_conductors() -> list[dict]:
    """Return conductor agents (Sage, Nova, Vera)."""
    return get_by_type("conductor")


def get_utility() -> dict | None:
    """Return the utility agent (Haiku). Returns the first utility agent."""
    utilities = get_by_type("utility")
    return utilities[0] if utilities else None


def get_by_role(role: str) -> dict | None:
    """Look up an agent by role (e.g., 'planner', 'implementer', 'verifier')."""
    for agent in _load_registry().values():
        if agent.get("role") == role:
            return agent
    return None


# Backward-compat convenience exports
SAGE = lambda: get_by_name("sage")
NOVA = lambda: get_by_name("nova")
VERA = lambda: get_by_name("vera")
HAIKU = lambda: get_by_name("haiku")
