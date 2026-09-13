"""
Orchestrator Agent — Phase 2: Governed Adaptive Loop.

This is the brain of the system. It coordinates the three specialist agents
through a governed, adaptive research loop with four defense boundaries:

  1. Safety Gate     — Pre-screens the idea before any research
  2. Budget Governor — Enforces hard limits on iterations, tool calls, and time
  3. Data Sanitizer  — (integrated into tools.py) wraps web content in inert envelopes
  4. State Updater   — Validates agent findings before merging into state

The orchestrator no longer runs agents in a fixed 1→2→3 sequence. Instead, it
uses an adaptive loop that inspects prioritized unknowns and dispatches the
most relevant specialist on each iteration.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from strands import Agent, tool
from src.model_provider import ModelRole, create_model

from src.agents.problem_agent import create_problem_agent
from src.agents.competition_agent import create_competition_agent
from src.agents.economics_agent import create_economics_agent
from src.prompts import ORCHESTRATOR_PROMPT

from src.governance.safety_gate import evaluate_scope_and_safety, ScopeResult
from src.governance.budget_governor import BudgetGovernor
from src.governance.state_updater import validate_and_merge, FindingProposal
from src.models import DiligenceState, UnknownStatus
from src.report import render_markdown_report
from src.verdict import synthesize_verdict


# ---------------------------------------------------------------------------
# Lazy agent singletons — created on first use, not at import time
# ---------------------------------------------------------------------------

_problem_agent_instance: Optional[Agent] = None
_competition_agent_instance: Optional[Agent] = None
_economics_agent_instance: Optional[Agent] = None


def _get_problem_agent() -> Agent:
    global _problem_agent_instance
    if _problem_agent_instance is None:
        _problem_agent_instance = create_problem_agent()
    return _problem_agent_instance


def _get_competition_agent() -> Agent:
    global _competition_agent_instance
    if _competition_agent_instance is None:
        _competition_agent_instance = create_competition_agent()
    return _competition_agent_instance


def _get_economics_agent() -> Agent:
    global _economics_agent_instance
    if _economics_agent_instance is None:
        _economics_agent_instance = create_economics_agent()
    return _economics_agent_instance


# ---------------------------------------------------------------------------
# Session-level state and governor — shared across the orchestrator's tools
# ---------------------------------------------------------------------------

_session_state: Optional[DiligenceState] = None
_session_governor: Optional[BudgetGovernor] = None


# ---------------------------------------------------------------------------
# Wrap each specialist agent as a tool the orchestrator can call.
# Each tool now records budget and parses findings through the state updater.
# ---------------------------------------------------------------------------

def _parse_and_merge_findings(agent_result: str, agent_name: str) -> None:
    """Extract save_finding JSON from agent output and merge via state updater.

    Agents call save_finding which returns JSON. The orchestrator receives
    the full conversation text. We extract those JSON blocks and validate
    each one through the propose-validate-merge pipeline.
    """
    global _session_state

    if _session_state is None:
        return

    # Look for JSON finding blocks in the agent output
    # save_finding returns JSON with these keys: category, content, evidence_type, source, confidence
    import re
    json_pattern = re.compile(
        r'\{\s*"category".*?"confidence"\s*:\s*[\d.]+\s*\}',
        re.DOTALL,
    )

    for match in json_pattern.finditer(agent_result):
        try:
            data = json.loads(match.group())
            proposal = FindingProposal(
                category=data.get("category", "unknown"),
                content=data.get("content", ""),
                evidence_type=data.get("evidence_type", "INFERENCE"),
                source=data.get("source", ""),
                confidence=data.get("confidence", 0.5),
                proposed_by=agent_name,
            )
            result = validate_and_merge(proposal, _session_state)
            if result.warnings:
                for w in result.warnings:
                    print(f"  [!] State updater warning: {w}")
            if not result.accepted:
                print(f"  [X] Finding rejected: {result.reason}")
        except (json.JSONDecodeError, Exception) as e:
            # Non-JSON text in agent output — skip silently
            pass


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
    global _session_governor

    agent = _get_problem_agent()

    prompt = f"Research this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we already know:\n{context}"

    result = str(agent(prompt))

    # Record budget and parse findings
    if _session_governor:
        _session_governor.record_tool_call("problem_agent")
    _parse_and_merge_findings(result, "problem_agent")

    # Log action to state
    if _session_state:
        _session_state.log_action("problem_agent", "Researched problem and customers", result[:200])

    return result


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
    global _session_governor

    agent = _get_competition_agent()

    prompt = f"Research competitors for this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we know about the problem:\n{context}"

    result = str(agent(prompt))

    if _session_governor:
        _session_governor.record_tool_call("competition_agent")
    _parse_and_merge_findings(result, "competition_agent")

    if _session_state:
        _session_state.log_action("competition_agent", "Researched competitors and gaps", result[:200])

    return result


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
    global _session_governor

    agent = _get_economics_agent()

    prompt = f"Evaluate the economics of this product idea:\n\n{idea}"
    if context:
        prompt += f"\n\nHere is what we know so far:\n{context}"

    result = str(agent(prompt))

    if _session_governor:
        _session_governor.record_tool_call("economics_agent")
    _parse_and_merge_findings(result, "economics_agent")

    if _session_state:
        _session_state.log_action("economics_agent", "Evaluated economics and viability", result[:200])

    return result


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
    model = create_model(ModelRole.ORCHESTRATOR)

    orchestrator = Agent(
        model=model,
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[problem_agent, competition_agent, economics_agent],
    )

    return orchestrator


def run_diligence(idea: str) -> tuple[str, DiligenceState, ScopeResult, dict]:
    """Run a full due diligence investigation on a product idea.

    This is the main entry point. Give it an idea, get a governed verdict.

    The pipeline:
    1. Safety Gate — screen the idea
    2. Budget Governor — initialize limits
    3. Adaptive Loop — orchestrator calls agents within budget
    4. State Updater — all findings validated before merge

    Args:
        idea: A plain-text description of the product idea.
              Example: "An app that helps small restaurants track food
                       inventory to reduce waste"

    Returns:
        Tuple of (verdict_text, state, scope_result, budget_status)
    """
    global _session_state, _session_governor

    print(f"\n{'='*60}")
    print(f"  IDEA DILIGENCE AGENT — Governed Pipeline + Verdict Engine")
    print(f"{'='*60}")
    print(f"\n  Idea: {idea}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # --- Step 1: Safety Gate ---
    print(f"\n{'-'*60}")
    print(f"  [SAFETY GATE] Pre-screening idea...")
    print(f"{'-'*60}")

    scope_result = evaluate_scope_and_safety(idea)

    if not scope_result.is_valid:
        print(f"\n  [REJECTED] {scope_result.rejection_reason}")
        if scope_result.risk_flags:
            for flag in scope_result.risk_flags:
                print(f"     [!] {flag}")
        empty_state = DiligenceState(idea=idea)
        return (
            f"REJECTED by Safety Gate: {scope_result.rejection_reason}",
            empty_state,
            scope_result,
            {},
        )

    print(f"  [ACCEPTED] Idea is a valid product concept")
    if scope_result.risk_flags:
        for flag in scope_result.risk_flags:
            print(f"     [!] {flag}")

    sanitized_idea = scope_result.sanitized_idea

    # --- Step 2: Initialize Budget Governor & State ---
    governor = BudgetGovernor(
        max_iterations=5,
        max_tool_calls_total=25,
        max_tool_calls_per_agent=8,
        max_wallclock_seconds=300.0,
    )
    governor.start()
    _session_governor = governor

    state = DiligenceState(idea=sanitized_idea)
    _session_state = state

    print(f"\n{'-'*60}")
    print(f"  [RESEARCH LOOP] Starting adaptive investigation...")
    print(f"  Budget: {governor.remaining_summary()}")
    print(f"{'-'*60}\n")

    # --- Step 3: Run orchestrator within budget ---
    orchestrator = create_orchestrator()

    prompt = f"""Investigate this product idea and deliver a GO, MODIFY, or KILL verdict:

{sanitized_idea}

Run an adaptive investigation:
1. Start with problem_agent to understand the problem and customers
2. Use what you learn to guide your competition_agent research
3. Then call economics_agent with the full picture
4. If critical unknowns remain, make targeted follow-up calls
5. Synthesize everything into your verdict

{governor.remaining_summary()}

Be thorough but budget-conscious. The goal is an evidence-backed decision."""

    result = orchestrator(prompt)
    orchestrator_text = str(result)

    # Record final iteration
    governor.record_iteration()

    # --- Step 4: Verdict engine ---
    print(f"\n{'-'*60}")
    print(f"  [VERDICT ENGINE] Classifying evidence and scoring the idea...")
    print(f"{'-'*60}")
    report = synthesize_verdict(state, orchestrator_text=orchestrator_text, use_llm=True)
    print(
        f"  Decision: {report.decision.value}  "
        f"({report.confidence:.0%} confidence, {report.method})"
    )

    # --- Step 5: Compile results ---
    budget_status = governor.get_status()
    formatted = render_markdown_report(state, scope_result, budget_status)

    print(f"\n{'='*60}")
    print(f"  INVESTIGATION COMPLETE")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*60}")
    print(f"  Governance Summary:")
    print(f"    Iterations: {budget_status['iterations']}")
    print(f"    Tool calls: {budget_status['tool_calls_total']}")
    print(f"    Elapsed: {budget_status['elapsed_seconds']}s")
    print(f"    Evidence collected: {len(state.evidence)}")
    print(f"    Open unknowns: {len([u for u in state.unknowns if u.status != UnknownStatus.RESOLVED])}")
    if budget_status.get('exhaustion_reason'):
        print(f"    [!] Budget exhausted: {budget_status['exhaustion_reason']}")
    print(f"{'='*60}\n")

    # Clean up session globals
    _session_state = None
    _session_governor = None

    return formatted, state, scope_result, budget_status
