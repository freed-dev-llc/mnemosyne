"""Agent registry loader with profile support.

Reads config/agents.yaml and provides typed accessors for three profiles:
- local-only: All agents use local LLMs (Ollama, vLLM, llama.cpp)
- hybrid: Sage/Nova/Vera use cloud (Claude), Haiku uses local
- cloud-only: All agents use cloud APIs (Claude, Kimi, Codex, etc.)

Select profile via MNEMOSYNE_AGENT_PROFILE env var (default: hybrid).
Cached in memory and auto-reloaded when YAML mtime changes.

Usage::

    from config.agents import get_by_name, get_conductors, get_utility, get_active_profile

    profile = get_active_profile()  # e.g., "hybrid"
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
_profile_config: dict[str, Any] | None = None


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

    _cache = data
    _cache_mtime = mtime
    log.debug("Loaded agent registry from %s", _REGISTRY_PATH)
    return _cache


# =========================================================================
# Profile management
# =========================================================================


def get_active_profile() -> str:
    """Get the active profile name from env or registry default.

    Priority: MNEMOSYNE_AGENT_PROFILE env var → agents.yaml active_profile → "hybrid"
    """
    env_profile = os.environ.get("MNEMOSYNE_AGENT_PROFILE")
    if env_profile:
        return env_profile

    registry = _load_registry()
    return registry.get("active_profile", "hybrid")


def get_profile_config(profile: str | None = None) -> dict[str, Any]:
    """Get the configuration dict for a profile.

    Args:
        profile: Profile name (e.g., "hybrid"). Defaults to active profile.

    Returns:
        Profile dict with agent configs, or {} if not found.
    """
    if profile is None:
        profile = get_active_profile()

    registry = _load_registry()
    profiles = registry.get("profiles", {})
    return profiles.get(profile, {})


def list_profiles() -> list[str]:
    """List all available profiles."""
    registry = _load_registry()
    profiles = registry.get("profiles", {})
    return list(profiles.keys())


def get_profile_description(profile: str | None = None) -> str:
    """Get human-readable description of a profile."""
    if profile is None:
        profile = get_active_profile()

    config = get_profile_config(profile)
    return config.get("description", f"Profile: {profile}")


# =========================================================================
# Cloud provider reference
# =========================================================================


def get_cloud_providers() -> dict[str, dict]:
    """Get all cloud provider definitions."""
    registry = _load_registry()
    return registry.get("cloud_providers", {})


def get_cloud_provider(name: str) -> dict | None:
    """Get a single cloud provider definition."""
    providers = get_cloud_providers()
    return providers.get(name)


def list_cloud_providers() -> list[str]:
    """List all available cloud provider names."""
    return list(get_cloud_providers().keys())


# =========================================================================
# Local provider reference
# =========================================================================


def get_local_providers() -> dict[str, dict]:
    """Get all local provider definitions."""
    registry = _load_registry()
    return registry.get("local_providers", {})


def get_local_provider(name: str) -> dict | None:
    """Get a single local provider definition."""
    providers = get_local_providers()
    return providers.get(name)


def list_local_providers() -> list[str]:
    """List all available local provider names."""
    return list(get_local_providers().keys())


# =========================================================================
# Public accessors
# =========================================================================


def get_all() -> dict[str, dict]:
    """Return the full agent map {name: {...}} from registry definitions."""
    registry = _load_registry()
    return dict(registry.get("agents", {}))


def get_by_type(agent_type: str) -> list[dict]:
    """Return agents whose type matches agent_type."""
    return [a for a in get_all().values() if a.get("type") == agent_type]


def get_by_name(name: str, profile: str | None = None) -> dict | None:
    """Look up a single agent by name, with profile-specific endpoint override.

    Args:
        name: Agent name (e.g., "sage")
        profile: Profile name. Defaults to active profile.

    Returns:
        Agent dict with profile-specific endpoint, or None if not found.
    """
    if profile is None:
        profile = get_active_profile()

    # Get base agent definition
    base_agent = _load_registry().get("agents", {}).get(name)
    if not base_agent:
        return None

    # Get profile-specific overrides (endpoint, model, api_key_env, fallback)
    profile_config = get_profile_config(profile)
    agent_config = profile_config.get("agents", {}).get(name)

    if agent_config:
        # Merge profile config into base (profile overrides take precedence)
        merged = dict(base_agent)
        merged.update(agent_config)
        return merged

    # No profile override, return base
    return base_agent


def get_conductors(profile: str | None = None) -> list[dict]:
    """Return conductor agents (Sage, Nova, Vera) with profile-specific config."""
    if profile is None:
        profile = get_active_profile()

    return [
        get_by_name(name, profile)
        for name in ["sage", "nova", "vera"]
        if get_by_name(name, profile)
    ]


def get_utility(profile: str | None = None) -> dict | None:
    """Return the utility agent (Haiku) with profile-specific config."""
    if profile is None:
        profile = get_active_profile()
    return get_by_name("haiku", profile)


def get_by_role(role: str, profile: str | None = None) -> dict | None:
    """Look up an agent by role (e.g., 'planner', 'implementer', 'verifier')."""
    if profile is None:
        profile = get_active_profile()

    for name in ["sage", "nova", "vera", "haiku"]:
        agent = get_by_name(name, profile)
        if agent and agent.get("role") == role:
            return agent
    return None


# Backward-compat convenience exports
SAGE = lambda: get_by_name("sage")
NOVA = lambda: get_by_name("nova")
VERA = lambda: get_by_name("vera")
HAIKU = lambda: get_by_name("haiku")
