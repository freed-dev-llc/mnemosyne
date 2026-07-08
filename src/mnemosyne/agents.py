"""Mnemosyne agent orchestration.

Defines Sage (planner), Nova (implementer), Vera (verifier), and Haiku (utility)
as typed agent definitions with cost tiers and expertise markers. Provides utilities
for selecting the right agent for a task, switching profiles (local-only, hybrid, cloud-only),
and falling back to cheaper tiers when appropriate.

Practices:
- Use Sage for planning/architecture work (reads-only, deep analysis)
- Use Nova for implementation (code generation, testing, running build steps)
- Use Vera for verification (review, correctness checks, compliance)
- Use Haiku for routine tasks (classification, summarization, cheap Q&A)

Profiles:
- local-only: All agents use Ollama/vLLM/llama.cpp (zero cost, offline)
- hybrid: Sage/Nova/Vera use Claude, Haiku uses Ollama (balanced cost)
- cloud-only: All agents use cloud APIs (Claude, Kimi, Codex, etc.)

Cost optimization:
- Large multi-turn contexts: use Haiku for routine work, reserve Sage/Nova/Vera for decisions
- Long sessions: track token burn, fall back to Haiku when context exceeds threshold
- Fallback chain: task → preferred agent → Haiku (never fail, degrade gracefully)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

log = logging.getLogger("mnemosyne.agents")


@dataclass(frozen=True)
class Agent:
    """Agent definition with model, endpoint, provider, expertise, and cost tier."""

    name: str
    display_name: str
    role: Literal["planner", "implementer", "verifier", "default"]
    model: str
    endpoint: str
    provider: str  # e.g., "anthropic", "ollama", "kimi"
    api_key_env: str = ""
    personality: str = ""
    expertise: list[str] | None = None
    when_to_use: str = ""
    cost_tier: Literal["premium", "cheap"] = "cheap"
    timeout_s: float = 30.0
    fallback: dict | None = None  # Optional fallback endpoint


def _hydrate_agent(data: dict) -> Agent:
    """Convert agent registry dict to typed Agent."""
    expertise = data.get("expertise", [])
    if not expertise:
        expertise = None

    return Agent(
        name=data["name"],
        display_name=data["display_name"],
        role=data.get("role", "default"),
        model=data["model"],
        endpoint=data["endpoint"],
        provider=data.get("provider", ""),
        api_key_env=data.get("api_key_env", ""),
        personality=data.get("personality", ""),
        expertise=expertise,
        when_to_use=data.get("when_to_use", ""),
        cost_tier=_infer_cost_tier(data),
        timeout_s=data.get("timeout_s", 30.0),
        fallback=data.get("fallback"),
    )


def _infer_cost_tier(data: dict) -> Literal["premium", "cheap"]:
    """Infer cost tier from model name or explicit cost_tier field.

    Use model name (haiku = cheap, opus = premium) as primary signal,
    fall back to provider for ambiguous models.
    """
    explicit = data.get("cost_tier")
    if explicit in ("premium", "cheap"):
        return explicit

    model = data.get("model", "").lower()
    name = data.get("name", "").lower()

    # Model name takes precedence
    if "haiku" in model or "haiku" in name:
        return "cheap"
    if any(x in model for x in ("opus", "sonnet", "claude-3", "llama2:70b")):
        return "premium"
    if any(x in model for x in ("qwen", "tinyllama", "nano", "1.5b")):
        return "cheap"

    # Fall back to provider
    provider = data.get("provider", "").lower()
    if provider in ("ollama", "vllm", "llama_cpp"):
        return "cheap"
    if provider in ("anthropic", "kimi", "codex"):
        return "premium"

    return "cheap"  # Default to cheap


# Typed agent accessors
def get_sage(profile: str | None = None) -> Agent | None:
    """Return the planner agent.

    Args:
        profile: Profile name (local-only, hybrid, cloud-only). Defaults to active.
    """
    from config.agents import get_by_name

    data = get_by_name("sage", profile=profile)
    return _hydrate_agent(data) if data else None


def get_nova(profile: str | None = None) -> Agent | None:
    """Return the implementer agent.

    Args:
        profile: Profile name (local-only, hybrid, cloud-only). Defaults to active.
    """
    from config.agents import get_by_name

    data = get_by_name("nova", profile=profile)
    return _hydrate_agent(data) if data else None


def get_vera(profile: str | None = None) -> Agent | None:
    """Return the verifier agent.

    Args:
        profile: Profile name (local-only, hybrid, cloud-only). Defaults to active.
    """
    from config.agents import get_by_name

    data = get_by_name("vera", profile=profile)
    return _hydrate_agent(data) if data else None


def get_haiku(profile: str | None = None) -> Agent | None:
    """Return the utility/cheap agent.

    Args:
        profile: Profile name (local-only, hybrid, cloud-only). Defaults to active.
    """
    from config.agents import get_by_name

    data = get_by_name("haiku", profile=profile)
    return _hydrate_agent(data) if data else None


def get_agent_for_task(
    task: Literal["planning", "implementation", "verification", "routine"],
    prefer_cheap: bool = False,
    profile: str | None = None,
) -> Agent | None:
    """Select the best agent for a task, with optional cost optimization.

    Args:
        task: The kind of work (planning, implementation, verification, routine)
        prefer_cheap: If True, prefer Haiku for any task (cost optimization)
        profile: Profile name (local-only, hybrid, cloud-only). Defaults to active.

    Returns:
        Agent or None if not found
    """
    if prefer_cheap:
        return get_haiku(profile=profile)

    if task == "planning":
        return get_sage(profile=profile)
    elif task == "implementation":
        return get_nova(profile=profile)
    elif task == "verification":
        return get_vera(profile=profile)
    else:
        return get_haiku(profile=profile)


def get_api_key(agent: Agent) -> str | None:
    """Load API key from environment for an agent.

    Args:
        agent: Agent whose API key to retrieve

    Returns:
        API key string or None if not found
    """
    if not agent.api_key_env:
        return None
    return os.environ.get(agent.api_key_env)


# Conductor agents (premium tier)
CONDUCTORS = ["sage", "nova", "vera"]

# Utility agent (cheap tier)
UTILITY = "haiku"


# Cost optimization helpers


# Profile management
def get_active_profile() -> str:
    """Get the currently active profile (local-only, hybrid, or cloud-only)."""
    from config.agents import get_active_profile as config_get_active

    return config_get_active()


def list_available_profiles() -> list[str]:
    """List all available profiles."""
    from config.agents import list_profiles

    return list_profiles()


def get_profile_description(profile: str | None = None) -> str:
    """Get human-readable description of a profile."""
    from config.agents import get_profile_description as config_get_desc

    return config_get_desc(profile)


def list_cloud_providers() -> list[str]:
    """List all available cloud provider options (Claude, Kimi, Codex)."""
    from config.agents import list_cloud_providers

    return list_cloud_providers()


def list_local_providers() -> list[str]:
    """List all available local provider options (Ollama, vLLM, llama.cpp)."""
    from config.agents import list_local_providers

    return list_local_providers()


# Cost estimation
def estimate_token_cost(model: str, token_count: int, provider: str = "anthropic") -> float:
    """Estimate cost in USD for a model's token usage (rough guide).

    Based on 2025 pricing for various providers. Adjust as needed.

    Args:
        model: Model name
        token_count: Number of tokens
        provider: Provider name (anthropic, kimi, ollama, etc.)

    Returns:
        Estimated cost in USD
    """
    # Simplified pricing (input tokens; output typically ~3x)
    pricing = {
        # Anthropic (Claude)
        ("claude-opus-4-8", "anthropic"): 0.000015,  # $15/M input
        ("claude-haiku-4-5-20251001", "anthropic"): 0.00000080,  # $0.80/M input
        # Moonshot (Kimi)
        ("moonshot-v1-128k", "kimi"): 0.000010,  # ~$10/M estimate
        ("moonshot-v1-8k", "kimi"): 0.000005,  # ~$5/M estimate
        # Local providers (zero cost)
        ("llama2:70b", "ollama"): 0.0,
        ("llama2:13b", "ollama"): 0.0,
        ("qwen2.5:1.5b", "ollama"): 0.0,
    }

    key = (model, provider)
    rate = pricing.get(key)
    if rate is None:
        rate = 0.00001  # Default fallback
    return rate * token_count


def should_use_cheap_tier(
    total_tokens_this_session: int,
    cost_budget_usd: float = 0.10,
    profile: str | None = None,
) -> bool:
    """Decide whether to use cheap tier to stay within budget.

    Args:
        total_tokens_this_session: Tokens used so far in this session
        cost_budget_usd: Budget for the session
        profile: Profile to check (defaults to active)

    Returns:
        True if we should switch to cheap tier to conserve cost
    """
    if profile is None:
        profile = get_active_profile()

    haiku = get_haiku(profile=profile)
    if not haiku:
        return False

    # Estimate cost of premium agents
    sage = get_sage(profile=profile)
    if sage:
        current_cost = estimate_token_cost(
            sage.model, total_tokens_this_session, sage.provider
        )
    else:
        current_cost = estimate_token_cost(
            "claude-opus-4-8", total_tokens_this_session, "anthropic"
        )

    remaining_budget = cost_budget_usd - current_cost

    # If we've spent >70% of budget, switch to cheap tier
    return (cost_budget_usd - remaining_budget) / cost_budget_usd > 0.7
