#!/usr/bin/env python
"""Example: Using Sage, Nova, Vera, and Haiku for cost-optimized workflows.

This demonstrates how to select agents based on task type and optimize
for token burn in multi-turn sessions.
"""

import sys
from pathlib import Path

# Add repo root to path so config module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from mnemosyne.agents import (
    get_agent_for_task,
    get_api_key,
    get_haiku,
    get_nova,
    get_sage,
    get_vera,
    should_use_cheap_tier,
)


def example_planning_workflow():
    """Plan a task with Sage (premium, read-only analysis)."""
    print("\n=== Planning Workflow ===")
    sage = get_sage()
    print(f"Using {sage.display_name} for planning")
    print(f"  Model: {sage.model}")
    print(f"  Expertise: {', '.join(sage.expertise)}")
    print(f"  When to use: {sage.when_to_use}")
    print(f"  Cost tier: {sage.cost_tier}")


def example_implementation_workflow():
    """Implement a task with Nova (premium, code generation)."""
    print("\n=== Implementation Workflow ===")
    nova = get_nova()
    print(f"Using {nova.display_name} for implementation")
    print(f"  Model: {nova.model}")
    print(f"  Expertise: {', '.join(nova.expertise)}")
    print(f"  When to use: {nova.when_to_use}")
    print(f"  Cost tier: {nova.cost_tier}")


def example_verification_workflow():
    """Verify a task with Vera (premium, review and testing)."""
    print("\n=== Verification Workflow ===")
    vera = get_vera()
    print(f"Using {vera.display_name} for verification")
    print(f"  Model: {vera.model}")
    print(f"  Expertise: {', '.join(vera.expertise)}")
    print(f"  When to use: {vera.when_to_use}")
    print(f"  Cost tier: {vera.cost_tier}")


def example_token_burn_reduction():
    """Reduce token burn by switching to Haiku for routine work."""
    print("\n=== Token Burn Reduction ===")

    # Simulate a multi-turn session that's accumulated tokens
    total_tokens = 150_000
    budget_usd = 0.10

    should_cheap = should_use_cheap_tier(total_tokens, budget_usd)
    print(f"Session tokens so far: {total_tokens:,}")
    print(f"Budget remaining: ${budget_usd:.2f}")
    print(f"Switch to cheap tier? {should_cheap}")

    # Select agent based on token load
    agent = get_agent_for_task("planning", prefer_cheap=should_cheap)
    print(f"Selected agent: {agent.display_name} ({agent.cost_tier} tier)")


def example_task_routing():
    """Route different task types to appropriate agents."""
    print("\n=== Task Routing ===")

    tasks = [
        ("planning", False),  # Premium
        ("implementation", False),  # Premium
        ("verification", False),  # Premium
        ("routine", True),  # Cheap
        ("planning", True),  # Force cheap for budget reasons
    ]

    for task_type, prefer_cheap in tasks:
        agent = get_agent_for_task(task_type, prefer_cheap=prefer_cheap)
        tier = f"({agent.cost_tier} tier)"
        cheap_note = " [forced cheap]" if prefer_cheap else ""
        print(f"  {task_type:16} → {agent.display_name:8} {tier:15} {cheap_note}")


def example_fallback_handling():
    """Show how to implement fallback chains."""
    print("\n=== Fallback Handling ===")

    # Try premium agents first, fall back to Haiku
    sage = get_sage()
    if sage and sage.cost_tier == "premium":
        print(f"Primary agent: {sage.display_name} (premium)")
    else:
        print(f"Fallback agent: {get_haiku().display_name} (cheap)")

    # Same pattern for other tasks
    nova = get_nova()
    if nova and nova.cost_tier == "premium":
        print(f"Primary agent: {nova.display_name} (premium)")
    else:
        print(f"Fallback agent: {get_haiku().display_name} (cheap)")


if __name__ == "__main__":
    print("Mnemosyne Agent Examples: Sage, Nova, Vera, Haiku")

    example_planning_workflow()
    example_implementation_workflow()
    example_verification_workflow()
    example_task_routing()
    example_token_burn_reduction()
    example_fallback_handling()

    print("\n✓ All examples complete")
