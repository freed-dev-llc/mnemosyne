#!/usr/bin/env python
"""Demo: Agent profiles (local-only, hybrid, cloud-only) and provider options.

Shows how to switch between profiles and select specific cloud/local providers.
"""

import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mnemosyne.agents import (
    get_active_profile,
    get_agent_for_task,
    get_haiku,
    get_nova,
    get_sage,
    get_vera,
    list_available_profiles,
    list_cloud_providers,
    list_local_providers,
)


def demo_profiles():
    """Show available profiles and current selection."""
    print("\n=== Available Profiles ===")
    profiles = list_available_profiles()
    for profile in profiles:
        print(f"  • {profile}")

    active = get_active_profile()
    print(f"\nActive profile: {active}")


def demo_profile_comparison():
    """Compare agents across profiles."""
    print("\n=== Agent Configuration by Profile ===\n")

    for profile in list_available_profiles():
        print(f"Profile: {profile.upper()}")
        print("-" * 70)

        sage = get_sage(profile=profile)
        haiku = get_haiku(profile=profile)

        if sage:
            print(f"  Sage (planner):")
            print(f"    Model:    {sage.model}")
            print(f"    Provider: {sage.provider}")
            print(f"    Endpoint: {sage.endpoint}")
            if sage.fallback:
                print(f"    Fallback: {sage.fallback.get('model')} ({sage.fallback.get('provider')})")

        print()

        if haiku:
            print(f"  Haiku (utility):")
            print(f"    Model:    {haiku.model}")
            print(f"    Provider: {haiku.provider}")
            print(f"    Endpoint: {haiku.endpoint}")

        print()


def demo_cloud_providers():
    """Show available cloud provider options."""
    print("\n=== Cloud Provider Options ===")
    for provider in list_cloud_providers():
        print(f"  • {provider}")

    print("\nTo use a different cloud provider, update config/agents.yaml")
    print("or set model/endpoint/api_key_env in your profile section.")


def demo_local_providers():
    """Show available local provider options."""
    print("\n=== Local Provider Options ===")
    for provider in list_local_providers():
        print(f"  • {provider}")

    print("\nTo use a different local provider, update config/agents.yaml")
    print("or set MNEMOSYNE_AGENT_PROFILE=local-only and configure Ollama/vLLM/llama.cpp")


def demo_task_routing_by_profile():
    """Show how task routing changes by profile."""
    print("\n=== Task Routing by Profile ===\n")

    for profile in list_available_profiles():
        print(f"{profile.upper()}:")
        for task in ["planning", "implementation", "verification", "routine"]:
            agent = get_agent_for_task(task, profile=profile)
            if agent:
                cost = f"({agent.cost_tier} tier)" if agent.cost_tier else ""
                print(f"  {task:16} → {agent.display_name:8} {cost}")
        print()


def demo_cost_implications():
    """Show cost differences between profiles."""
    print("\n=== Cost Implications per Profile ===\n")

    scenarios = [
        ("local-only", "Free (offline)", "$0.00/session"),
        ("hybrid", "Mixed (cloud + local)", "$0.05-0.20/session*"),
        ("cloud-only (Claude)", "All cloud", "$0.20-1.00/session*"),
        ("cloud-only (Kimi)", "All cloud, cheaper", "$0.10-0.50/session*"),
    ]

    for profile, desc, cost in scenarios:
        print(f"  {profile:30} {desc:30} {cost}")

    print("\n  * Rough estimates for a 10-turn planning/implementation/verification cycle")
    print("    Actual cost depends on context size, model, and token usage")


if __name__ == "__main__":
    print("Mnemosyne Agent Profiles & Providers Demo")
    print("=" * 70)

    demo_profiles()
    demo_profile_comparison()
    demo_cloud_providers()
    demo_local_providers()
    demo_task_routing_by_profile()
    demo_cost_implications()

    print("\n✓ Demo complete")
