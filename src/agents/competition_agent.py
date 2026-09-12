"""
Competition Analysis Agent.

This agent finds competitors, pricing data, market gaps, and user complaints
related to the product idea being investigated.
"""

from strands import Agent
from strands.models.bedrock import BedrockModel

from src.prompts import COMPETITION_AGENT_PROMPT
from src.tools import save_finding, search_web, read_webpage


def create_competition_agent() -> Agent:
    """Create and return a configured Competition Analysis Agent.

    Returns:
        A Strands Agent ready to research competitors and market landscape.
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    agent = Agent(
        model=model,
        system_prompt=COMPETITION_AGENT_PROMPT,
        tools=[search_web, read_webpage, save_finding],
    )

    return agent
