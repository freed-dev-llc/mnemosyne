"""Tests for the agent orchestration system."""

from __future__ import annotations

from config.agents import get_all, get_by_name, get_by_role, get_conductors, get_utility
from mnemosyne.agents import Agent, get_agent_for_task, get_haiku, get_nova, get_sage, get_vera


class TestAgentRegistry:
    """Test agent registry loading and accessors."""

    def test_load_all_agents(self):
        """All agents load from YAML."""
        all_agents = get_all()
        assert len(all_agents) >= 4, "Should have at least 4 agents (Sage, Nova, Vera, Haiku)"

    def test_get_conductors(self):
        """Conductors are Sage, Nova, Vera."""
        conductors = get_conductors()
        names = {a["name"] for a in conductors}
        assert "sage" in names
        assert "nova" in names
        assert "vera" in names

    def test_get_utility(self):
        """Utility agent is Haiku."""
        haiku = get_utility()
        assert haiku is not None
        assert haiku["name"] == "haiku"

    def test_get_by_name(self):
        """Individual agents can be looked up by name."""
        sage = get_by_name("sage")
        assert sage is not None
        assert sage["display_name"] == "Sage"

    def test_get_by_role(self):
        """Agents can be looked up by role."""
        planner = get_by_role("planner")
        assert planner is not None
        assert planner["name"] == "sage"

        implementer = get_by_role("implementer")
        assert implementer is not None
        assert implementer["name"] == "nova"


class TestAgentOrchestration:
    """Test agent selection and orchestration."""

    def test_get_sage(self):
        """Sage is accessible and properly typed."""
        sage = get_sage()
        assert sage is not None
        assert isinstance(sage, Agent)
        assert sage.role == "planner"
        assert sage.cost_tier == "premium"

    def test_get_nova(self):
        """Nova is accessible and properly typed."""
        nova = get_nova()
        assert nova is not None
        assert isinstance(nova, Agent)
        assert nova.role == "implementer"
        assert nova.cost_tier == "premium"

    def test_get_vera(self):
        """Vera is accessible and properly typed."""
        vera = get_vera()
        assert vera is not None
        assert isinstance(vera, Agent)
        assert vera.role == "verifier"
        assert vera.cost_tier == "premium"

    def test_get_haiku(self):
        """Haiku is accessible and properly typed."""
        haiku = get_haiku()
        assert haiku is not None
        assert isinstance(haiku, Agent)
        assert haiku.role == "default"
        assert haiku.cost_tier == "cheap"

    def test_get_agent_for_task_planning(self):
        """Planning task returns Sage."""
        agent = get_agent_for_task("planning")
        assert agent is not None
        assert agent.name == "sage"

    def test_get_agent_for_task_implementation(self):
        """Implementation task returns Nova."""
        agent = get_agent_for_task("implementation")
        assert agent is not None
        assert agent.name == "nova"

    def test_get_agent_for_task_verification(self):
        """Verification task returns Vera."""
        agent = get_agent_for_task("verification")
        assert agent is not None
        assert agent.name == "vera"

    def test_get_agent_for_task_routine(self):
        """Routine task returns Haiku."""
        agent = get_agent_for_task("routine")
        assert agent is not None
        assert agent.name == "haiku"

    def test_get_agent_for_task_prefer_cheap(self):
        """Prefer cheap returns Haiku even for premium tasks."""
        agent = get_agent_for_task("planning", prefer_cheap=True)
        assert agent is not None
        assert agent.name == "haiku"


class TestAgentProperties:
    """Test agent data integrity."""

    def test_sage_properties(self):
        """Sage has expected properties."""
        sage = get_sage()
        assert sage is not None
        assert sage.model == "claude-opus-4-8"
        assert sage.endpoint == "https://api.anthropic.com/v1/messages"
        assert sage.api_key_env == "ANTHROPIC_API_KEY"
        assert "plan" in sage.when_to_use.lower()

    def test_haiku_properties(self):
        """Haiku has expected properties."""
        haiku = get_haiku()
        assert haiku is not None
        assert haiku.model == "claude-haiku-4-5-20251001"
        assert haiku.endpoint == "https://api.anthropic.com/v1/messages"
        assert haiku.cost_tier == "cheap"

    def test_conductor_expertise(self):
        """Conductors have expertise markers."""
        for agent in [get_sage(), get_nova(), get_vera()]:
            assert agent is not None
            assert agent.expertise
            assert len(agent.expertise) > 0

    def test_all_agents_have_when_to_use(self):
        """All agents have guidance on when to use them."""
        for agent in [get_sage(), get_nova(), get_vera(), get_haiku()]:
            assert agent is not None
            assert agent.when_to_use
            assert len(agent.when_to_use) > 0
