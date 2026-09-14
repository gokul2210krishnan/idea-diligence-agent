"""
Problem Analysis Agent.

This agent investigates the problem that a product idea is trying to solve.
It researches customer segments, pain points, existing workarounds, and demand signals.
"""

from strands import Agent
from src.model_provider import ModelRole, create_model

from src.prompts import PROBLEM_AGENT_PROMPT
from src.tools import save_finding, search_web, read_webpage


def create_problem_agent(tools=None) -> Agent:
    """Create and return a configured Problem Analysis Agent.

    Args:
        tools: Optional session-bound tools. Defaults to unbound research tools.

    Returns:
        A Strands Agent ready to research problems and customer segments.
    """
    model = create_model(ModelRole.PROBLEM)

    agent = Agent(
        model=model,
        system_prompt=PROBLEM_AGENT_PROMPT,
        tools=tools or [search_web, read_webpage, save_finding],
    )

    return agent
