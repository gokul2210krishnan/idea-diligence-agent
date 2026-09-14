"""
Orchestrator — Python-owned adaptive research loop.

The LLM does not own control flow. For each investigation this module:

  1. Builds an isolated ResearchSession (no process globals)
  2. Asks Python which specialist to dispatch next
  3. Asks the BudgetGovernor whether that dispatch is allowed
  4. Runs a *fresh* specialist agent with session-bound tools
  5. Stops when the governor is exhausted or no work remains
  6. Hands DiligenceState to the verdict engine

Specialist agents still use an LLM to research. They cannot start themselves,
exceed budget, or write state except through validate_and_merge.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Callable, Optional

from src.agents.competition_agent import create_competition_agent
from src.agents.economics_agent import create_economics_agent
from src.agents.problem_agent import create_problem_agent
from src.governance.budget_governor import BudgetGovernor
from src.governance.safety_gate import evaluate_scope_and_safety, ScopeResult
from src.governance.state_updater import FindingProposal, validate_and_merge
from src.model_provider import ModelRole, describe_model
from src.models import DecisionImpact, DiligenceState, UnknownStatus
from src.progress import emit, specialist_label
from src.report import render_markdown_report
from src.session import InvestigationCancelled, ResearchSession
from src.tools import create_research_tools
from src.verdict import synthesize_verdict

REQUIRED_SPECIALISTS = ("problem_agent", "competition_agent", "economics_agent")

_CATEGORY_TO_AGENT = {
    "problem": "problem_agent",
    "customer": "problem_agent",
    "competitor": "competition_agent",
    "pricing": "economics_agent",
    "market_size": "economics_agent",
    "business_model": "economics_agent",
}

_JSON_FINDING = re.compile(
    r'\{\s*"category".*?"confidence"\s*:\s*[\d.]+\s*\}',
    re.DOTALL,
)

DispatchFn = Callable[[ResearchSession, str], str]

def _sleep_interruptible(session: ResearchSession, seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        session.raise_if_stopped()
        time.sleep(min(0.2, max(0.0, deadline - time.time())))


def _raise_if_stopped(should_stop: Callable[[], bool] | None) -> None:
    if should_stop and should_stop():
        raise InvestigationCancelled()


_DISPATCH_ATTEMPTS = 3
_TRANSIENT_MARKERS = (
    "503",
    "429",
    "unavailable",
    "overloaded",
    "resource_exhausted",
    "timeout",
    "temporarily",
)


def _is_transient_provider_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def select_next_specialist(session: ResearchSession) -> Optional[str]:
    """Choose the next specialist. Pure Python — the LLM does not pick this."""
    ran = set(session.dispatched)
    for name in REQUIRED_SPECIALISTS:
        if name not in ran:
            return name

    if session.follow_ups >= 1:
        return None

    for unknown in session.state.get_prioritized_unknowns():
        if unknown.importance != DecisionImpact.CRITICAL:
            continue
        agent = _CATEGORY_TO_AGENT.get(unknown.category.lower())
        if agent and not session.governor.is_agent_over_budget(agent):
            return agent
    return None


def ingest_agent_output(state: DiligenceState, agent_result: str, agent_name: str) -> None:
    """Merge any leftover save_finding JSON that was not already applied via tools."""
    for match in _JSON_FINDING.finditer(agent_result):
        try:
            data = json.loads(match.group())
            if "accepted" in data and "reason" in data:
                continue
            proposal = FindingProposal(
                category=data.get("category", "unknown"),
                content=data.get("content", ""),
                evidence_type=data.get("evidence_type", "INFERENCE"),
                source=data.get("source", ""),
                confidence=data.get("confidence", 0.5),
                proposed_by=agent_name,
            )
            result = validate_and_merge(proposal, state)
            if result.warnings:
                for warning in result.warnings:
                    print(f"  [!] State updater warning: {warning}")
            if not result.accepted:
                print(f"  [X] Finding rejected: {result.reason}")
        except (json.JSONDecodeError, TypeError, ValueError):
            continue


def _context_for(session: ResearchSession) -> str:
    lines = [f"Idea: {session.state.idea}"]
    if session.state.evidence:
        lines.append("Evidence so far:")
        for item in session.state.evidence[-8:]:
            lines.append(f"- [{item.evidence_type.value}/{item.category}] {item.content}")
    unknowns = session.state.get_prioritized_unknowns()[:4]
    if unknowns:
        lines.append("Open unknowns:")
        for unknown in unknowns:
            lines.append(f"- ({unknown.importance.value}) {unknown.question}")
    lines.append(session.governor.remaining_summary())
    return "\n".join(lines)


def _prompt_for(agent_name: str, session: ResearchSession) -> str:
    idea = session.state.idea
    context = _context_for(session)
    if agent_name == "problem_agent":
        return f"Research this product idea:\n\n{idea}\n\n{context}"
    if agent_name == "competition_agent":
        return f"Research competitors for this product idea:\n\n{idea}\n\n{context}"
    return f"Evaluate the economics of this product idea:\n\n{idea}\n\n{context}"


def dispatch_specialist(session: ResearchSession, agent_name: str) -> str:
    """Run one fresh specialist with tools bound to this session only."""
    tools = create_research_tools(
        state=session.state,
        governor=session.governor,
        agent_name=agent_name,
        on_progress=session.on_progress,
        should_stop=session.should_stop,
    )
    factories = {
        "problem_agent": create_problem_agent,
        "competition_agent": create_competition_agent,
        "economics_agent": create_economics_agent,
    }
    factory = factories.get(agent_name)
    if factory is None:
        return f"Unknown specialist '{agent_name}' — skipped."

    last_error: BaseException | None = None
    for attempt in range(1, _DISPATCH_ATTEMPTS + 1):
        agent = factory(tools=tools)
        try:
            result = str(agent(_prompt_for(agent_name, session)))
            ingest_agent_output(session.state, result, agent_name)
            session.state.log_action(agent_name, f"Dispatched {agent_name}", result[:200])
            session.emit(
                "research",
                f"{specialist_label(agent_name)} finished",
                level="ok",
                agent=agent_name,
            )
            return result
        except InvestigationCancelled:
            raise
        except Exception as exc:
            last_error = exc
            transient = _is_transient_provider_error(exc)
            if not transient or attempt == _DISPATCH_ATTEMPTS:
                break
            wait = 2 * attempt
            session.emit(
                "research",
                f"{specialist_label(agent_name)} hit {type(exc).__name__} "
                f"(attempt {attempt}/{_DISPATCH_ATTEMPTS}); retrying in {wait}s",
                level="warn",
                agent=agent_name,
            )
            _sleep_interruptible(session, wait)

    assert last_error is not None
    note = (
        f"{agent_name} unavailable ({type(last_error).__name__}). "
        "Specialist skipped; investigation continues with remaining evidence."
    )
    session.emit(
        "research",
        f"{specialist_label(agent_name)} unavailable ({type(last_error).__name__}). Skipping.",
        level="warn",
        agent=agent_name,
    )
    session.state.log_action(agent_name, f"Failed {agent_name}", str(last_error)[:200])
    return note


def run_research_loop(
    session: ResearchSession,
    dispatch_fn: DispatchFn | None = None,
) -> str:
    """Python control loop. Stops on budget exhaustion or when no specialist remains."""
    dispatch = dispatch_fn or dispatch_specialist
    notes: list[str] = []

    while not session.governor.is_exhausted():
        session.raise_if_stopped()
        agent_name = select_next_specialist(session)
        if agent_name is None:
            break
        if not session.governor.begin_iteration(agent_name):
            session.emit(
                "research",
                f"Budget stop: {session.governor.exhaustion_reason}",
                level="warn",
            )
            break

        if agent_name in session.dispatched:
            session.follow_ups += 1
        session.dispatched.append(agent_name)

        session.emit(
            "research",
            f"Dispatching {specialist_label(agent_name)} ({session.governor.remaining_summary()})",
            agent=agent_name,
        )
        try:
            notes.append(dispatch(session, agent_name))
        except InvestigationCancelled:
            raise
        except Exception as exc:
            note = (
                f"{agent_name} failed ({type(exc).__name__}). "
                "Specialist skipped; investigation continues with remaining evidence."
            )
            session.emit("research", note, level="warn", agent=agent_name)
            session.state.log_action(agent_name, f"Failed {agent_name}", str(exc)[:200])
            notes.append(note)
        session.raise_if_stopped()

    return "\n\n".join(notes)


def _seed_unknowns(state: DiligenceState) -> None:
    state.add_unknown(
        "Is the problem painful enough that buyers will pay?",
        category="problem",
        importance=DecisionImpact.CRITICAL,
    )
    state.add_unknown(
        "Is there a competitive gap, or is the category crowded?",
        category="competitor",
        importance=DecisionImpact.HIGH,
    )
    state.add_unknown(
        "Are unit economics viable at realistic pricing?",
        category="pricing",
        importance=DecisionImpact.CRITICAL,
    )


def run_diligence(
    idea: str,
    on_progress: Callable[[dict], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[str, DiligenceState, ScopeResult, dict]:
    """Run a full due diligence investigation on a product idea.

    Each call creates its own ResearchSession. Concurrent calls do not share
    state, agents, or budget counters. ``on_progress`` receives UI-safe event dicts.
    ``should_stop`` is checked between specialists so a live UI can cancel the run.
    """
    print(f"\n{'='*60}")
    print(f"  IDEA DILIGENCE AGENT — Governed Pipeline + Verdict Engine")
    print(f"{'='*60}")
    print(f"\n  Idea: {idea}")
    print(f"  Model: {describe_model(ModelRole.SAFETY_GATE)}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    emit(
        on_progress,
        phase="safety",
        message=f"Safety gate screening · {describe_model(ModelRole.SAFETY_GATE)}",
    )
    scope_result = evaluate_scope_and_safety(idea)

    if not scope_result.is_valid:
        emit(
            on_progress,
            phase="safety",
            message=f"Rejected: {scope_result.rejection_reason}",
            level="error",
        )
        empty_state = DiligenceState(idea=idea)
        return (
            f"REJECTED by Safety Gate: {scope_result.rejection_reason}",
            empty_state,
            scope_result,
            {},
        )

    emit(on_progress, phase="safety", message="Safety gate passed", level="ok")
    _raise_if_stopped(should_stop)

    governor = BudgetGovernor(
        max_iterations=5,
        max_tool_calls_total=25,
        max_tool_calls_per_agent=8,
        max_wallclock_seconds=300.0,
    )
    governor.start()

    state = DiligenceState(idea=scope_result.sanitized_idea)
    _seed_unknowns(state)
    session = ResearchSession(
        state=state,
        governor=governor,
        on_progress=on_progress,
        should_stop=should_stop,
    )

    emit(
        on_progress,
        phase="research",
        message=f"Research loop starting · {governor.remaining_summary()}",
    )

    research_notes = run_research_loop(session)
    session.raise_if_stopped()

    emit(
        on_progress,
        phase="verdict",
        message="Verdict engine classifying evidence and scoring the idea",
        evidence_count=len(state.evidence),
    )
    report = synthesize_verdict(state, orchestrator_text=research_notes, use_llm=True)
    emit(
        on_progress,
        phase="done",
        message=(
            f"Verdict: {report.decision.value} "
            f"({report.confidence:.0%} confidence, {report.method})"
        ),
        level="ok",
        evidence_count=len(state.evidence),
    )

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
    if budget_status.get("exhaustion_reason"):
        print(f"    [!] Budget exhausted: {budget_status['exhaustion_reason']}")
    print(f"{'='*60}\n")

    return formatted, state, scope_result, budget_status
