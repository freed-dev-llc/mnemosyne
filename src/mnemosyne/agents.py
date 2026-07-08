"""Mnemosyne agent orchestration.

Defines Sage (planner), Nova (implementer), Vera (verifier), and Haiku (utility)
as typed agent definitions with cost tiers and expertise markers. Provides utilities
for selecting the right agent for a task and falling back to cheaper tiers when appropriate.

Practices:
- Use Sage for planning/architecture work (reads-only, deep analysis)
- Use Nova for implementation (code generation, testing, running build steps)
- Use Vera for verification (review, correctness checks, compliance)
- Use Haiku for routine tasks (classification, summarization, cheap Q&A)

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
    """Agent definition with model, endpoint, expertise, and cost tier."""

    name: str
    display_name: str
    role: Literal["planner", "implementer", "verifier", "default"]
    model: str
    endpoint: str
    api_key_env: str
    personality: str
    expertise: list[str]
    when_to_use: str
    cost_tier: Literal["premium", "cheap"]
    timeout_s: float


def _hydrate_agent(data: dict) -> Agent:
    """Convert agent registry dict to typed Agent."""
    return Agent(
        name=data["name"],
        display_name=data["display_name"],
        role=data.get("role", "default"),
        model=data["model"],
        endpoint=data["endpoint"],
        api_key_env=data["api_key_env"],
        personality=data.get("personality", ""),
        expertise=data.get("expertise", []),
        when_to_use=data.get("when_to_use", ""),
        cost_tier=data.get("cost_tier", "cheap"),
        timeout_s=data.get("timeout_s", 30.0),
    )


# Lazy import to avoid circular dependency with config module
_agents_cache: dict[str, Agent] | None = None


def _load_agents() -> dict[str, Agent]:
    """Load agents from registry, caching the result."""
    global _agents_cache
    if _agents_cache is not None:
        return _agents_cache

    try:
        from config.agents import get_all

        registry = get_all()
        _agents_cache = {name: _hydrate_agent(data) for name, data in registry.items()}
        return _agents_cache
    except ImportError:
        log.warning("config.agents not available; using fallback definitions")
        return {}


# Typed agent accessors
def get_sage() -> Agent | None:
    """Return the planner agent."""
    from config.agents import get_by_name

    data = get_by_name("sage")
    return _hydrate_agent(data) if data else None


def get_nova() -> Agent | None:
    """Return the implementer agent."""
    from config.agents import get_by_name

    data = get_by_name("nova")
    return _hydrate_agent(data) if data else None


def get_vera() -> Agent | None:
    """Return the verifier agent."""
    from config.agents import get_by_name

    data = get_by_name("vera")
    return _hydrate_agent(data) if data else None


def get_haiku() -> Agent | None:
    """Return the utility/cheap agent."""
    from config.agents import get_by_name

    data = get_by_name("haiku")
    return _hydrate_agent(data) if data else None


def get_agent_for_task(
    task: Literal["planning", "implementation", "verification", "routine"],
    prefer_cheap: bool = False,
) -> Agent | None:
    """Select the best agent for a task, with optional cost optimization.

    Args:
        task: The kind of work (planning, implementation, verification, routine)
        prefer_cheap: If True, prefer Haiku for any task (cost optimization)

    Returns:
        Agent or None if not found
    """
    if prefer_cheap:
        return get_haiku()

    if task == "planning":
        return get_sage()
    elif task == "implementation":
        return get_nova()
    elif task == "verification":
        return get_vera()
    else:
        return get_haiku()


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


def estimate_token_cost(model: str, token_count: int) -> float:
    """Estimate cost in USD for a model's token usage (rough guide).

    Based on 2025 Claude pricing. Adjust as needed.
    """
    # Simplified pricing (input tokens; output ~3x)
    pricing = {
        "claude-opus-4-8": 0.000015,  # $15/M input
        "claude-haiku-4-5-20251001": 0.00000080,  # $0.80/M input
    }
    return pricing.get(model, 0.00001) * token_count


def should_use_cheap_tier(
    total_tokens_this_session: int,
    cost_budget_usd: float = 0.10,
) -> bool:
    """Decide whether to use cheap tier (Haiku) to stay within budget.

    Args:
        total_tokens_this_session: Tokens used so far in this session
        cost_budget_usd: Budget for the session

    Returns:
        True if we should switch to cheap tier to conserve cost
    """
    haiku = get_haiku()
    if not haiku:
        return False

    current_cost = estimate_token_cost("claude-opus-4-8", total_tokens_this_session)
    remaining_budget = cost_budget_usd - current_cost

    # If we've spent >70% of budget, switch to cheap tier
    return (cost_budget_usd - remaining_budget) / cost_budget_usd > 0.7
