"""
Problem Analysis Agent.

This agent investigates the problem that a product idea is trying to solve.
It researches customer segments, pain points, existing workarounds, and demand signals.
"""

from strands import Agent
from strands.models.bedrock import BedrockModel

from src.prompts import PROBLEM_AGENT_PROMPT
from src.tools import save_finding, search_web, read_webpage


def create_problem_agent() -> Agent:
    """Create and return a configured Problem Analysis Agent.

    Returns:
        A Strands Agent ready to research problems and customer segments.
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    agent = Agent(
        model=model,
        system_prompt=PROBLEM_AGENT_PROMPT,
        tools=[search_web, read_webpage, save_finding],
    )

    return agent
