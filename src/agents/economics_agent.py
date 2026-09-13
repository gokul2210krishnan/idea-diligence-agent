"""
Economics Analysis Agent.

This agent evaluates the financial viability of the product idea:
pricing strategy, revenue models, market size, and unit economics.
"""

from strands import Agent
from src.model_provider import ModelRole, create_model

from src.prompts import ECONOMICS_AGENT_PROMPT
from src.tools import save_finding, search_web, read_webpage


def create_economics_agent() -> Agent:
    """Create and return a configured Economics Analysis Agent.

    Returns:
        A Strands Agent ready to research financial viability.
    """
    model = create_model(ModelRole.PROBLEM)

    agent = Agent(
        model=model,
        system_prompt=ECONOMICS_AGENT_PROMPT,
        tools=[search_web, read_webpage, save_finding],
    )

    return agent
