"""
Orchestrator Agent.

This is the brain of the system. It coordinates the three specialist agents
(Problem, Competition, Economics) and decides:
1. What to research next based on current knowledge gaps
2. When enough evidence has been gathered
3. The final GO / MODIFY / KILL verdict

It uses the Strands "agents-as-tools" pattern: each specialist agent is
wrapped as a tool that the orchestrator can call. This lets the orchestrator
decide the order and arguments for each research phase.
"""

from __future__ import annotations

import json
from datetime import datetime

from strands import Agent, tool
from src.model_provider import ModelRole, create_model

from src.agents.problem_agent import create_problem_agent
from src.agents.competition_agent import create_competition_agent
from src.agents.economics_agent import create_economics_agent
from src.prompts import ORCHESTRATOR_PROMPT


# ---------------------------------------------------------------------------
# Wrap each specialist agent as a tool the orchestrator can call.
# This is the "agents-as-tools" pattern from the Strands SDK.
# ---------------------------------------------------------------------------

# Create the specialist agents once (they're reusable)
_problem_agent = create_problem_agent()
_competition_agent = create_competition_agent()
_economics_agent = create_economics_agent()


@tool
def problem_agent(idea: str, context: str = "") -> str:
    """Research the problem that this product idea is trying to solve.

    This agent will search the web to understand:
    - What problem exists and how painful it is
    - Who has this problem (specific customer segments)
    - How people currently deal with it (existing workarounds)
    - Whether there's real demand for a solution

    Args:
        idea: The product idea to investigate.
        context: Any additional context from previous research (optional).

    Returns:
        A detailed problem analysis with evidence and findings.
    """
    prompt = f"Research this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we already know:\n{context}"

    result = _problem_agent(prompt)
    return str(result)


@tool
def competition_agent(idea: str, context: str = "") -> str:
    """Find competitors and alternatives for this product idea.

    This agent will search the web to find:
    - Direct competitors (products doing the same thing)
    - Indirect alternatives (different approaches to the same problem)
    - Competitor pricing and traction
    - Market gaps and user complaints about existing solutions

    Args:
        idea: The product idea to investigate.
        context: What we know about the problem so far (from problem_agent).

    Returns:
        A competitive landscape analysis with pricing data and market gaps.
    """
    prompt = f"Research competitors for this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we know about the problem:\n{context}"

    result = _competition_agent(prompt)
    return str(result)


@tool
def economics_agent(idea: str, context: str = "") -> str:
    """Evaluate whether this product idea can make money.

    This agent will research:
    - Realistic pricing based on competitor data
    - Best revenue model (subscription, usage, etc.)
    - Market size estimates
    - Unit economics viability

    Args:
        idea: The product idea to investigate.
        context: What we know about the problem and competition (from previous agents).

    Returns:
        A financial viability analysis with pricing recommendations.
    """
    prompt = f"Evaluate the economics of this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we know so far:\n{context}"

    result = _economics_agent(prompt)
    return str(result)


# ---------------------------------------------------------------------------
# The Orchestrator itself
# ---------------------------------------------------------------------------

def create_orchestrator() -> Agent:
    """Create and return the Orchestrator Agent.

    The orchestrator coordinates the research by calling specialist agents
    as tools, then synthesizes their findings into a final verdict.

    Returns:
        A Strands Agent configured as the orchestrator.
    """
    model = create_model(ModelRole.PROBLEM)

    orchestrator = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[problem_agent, competition_agent, economics_agent],
    )

    return orchestrator


def run_diligence(idea: str) -> str:
    """Run a full due diligence investigation on a product idea.

    This is the main entry point. Give it an idea, get a verdict.

    Args:
        idea: A plain-text description of the product idea.
              Example: "An app that helps small restaurants track food
                       inventory to reduce waste"

    Returns:
        The orchestrator's verdict and analysis as a formatted string.
    """
    print(f"\n{'='*60}")
    print(f"  IDEA DILIGENCE AGENT")
    print(f"  Starting investigation...")
    print(f"{'='*60}")
    print(f"\n  Idea: {idea}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n  Researching... (this may take a few minutes)")
    print(f"{'='*60}\n")

    orchestrator = create_orchestrator()

    prompt = f"""Investigate this product idea and deliver a GO, MODIFY, or KILL verdict:

{idea}

Run a thorough investigation:
1. First, call problem_agent to understand the problem and customers
2. Then, call competition_agent with what you learned about the problem
3. Then, call economics_agent with everything found so far
4. Finally, synthesize everything into your verdict

Be thorough but efficient. The goal is an evidence-backed decision."""

    result = orchestrator(prompt)

    print(f"\n{'='*60}")
    print(f"  INVESTIGATION COMPLETE")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    return str(result)
