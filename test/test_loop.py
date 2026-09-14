from src.agents.orchestrator import (
    ingest_agent_output,
    run_diligence,
    run_research_loop,
    select_next_specialist,
)
from src.governance.budget_governor import BudgetGovernor
from src.governance.safety_gate import ScopeResult
from src.models import DecisionImpact, DiligenceState, EvidenceType
from src.session import InvestigationCancelled, ResearchSession


def _session(max_iterations: int = 5) -> ResearchSession:
    governor = BudgetGovernor(
        max_iterations=max_iterations,
        max_tool_calls_total=25,
        max_tool_calls_per_agent=8,
        max_wallclock_seconds=999,
    )
    governor.start()
    state = DiligenceState(idea="A notebook app for leftover grocery ingredients")
    state.add_unknown(
        "Is the problem painful enough that buyers will pay?",
        category="problem",
        importance=DecisionImpact.CRITICAL,
    )
    return ResearchSession(state=state, governor=governor)


def test_select_next_specialist_is_python_owned():
    session = _session()
    assert select_next_specialist(session) == "problem_agent"
    session.dispatched.append("problem_agent")
    assert select_next_specialist(session) == "competition_agent"
    session.dispatched.append("competition_agent")
    assert select_next_specialist(session) == "economics_agent"
    session.dispatched.append("economics_agent")
    assert select_next_specialist(session) == "problem_agent"
    session.follow_ups = 1
    assert select_next_specialist(session) is None


def test_python_loop_stops_when_budget_exhausted():
    session = _session(max_iterations=2)
    calls: list[str] = []

    def dispatch(sess: ResearchSession, name: str) -> str:
        calls.append(name)
        sess.state.add_evidence(
            f"{name} finding",
            EvidenceType.INFERENCE,
            confidence=0.5,
            category="problem",
        )
        return name

    run_research_loop(session, dispatch_fn=dispatch)
    assert calls == ["problem_agent", "competition_agent"]
    assert session.governor.is_exhausted() is True
    assert session.governor.iteration_count == 2


def test_sessions_do_not_share_state():
    first = _session()
    second = _session()

    def dispatch_first(sess: ResearchSession, name: str) -> str:
        sess.state.add_evidence(
            "only in first session",
            EvidenceType.FACT,
            source="https://example.com",
            confidence=0.8,
            category="problem",
        )
        return name

    run_research_loop(first, dispatch_fn=dispatch_first)
    assert any(item.content == "only in first session" for item in first.state.evidence)
    assert second.state.evidence == []
    assert second.dispatched == []


def test_ingest_skips_tool_ack_json_and_merges_findings(empty_state: DiligenceState):
    blob = """
    {"accepted": true, "reason": "Accepted and merged", "warnings": []}
    {"category": "problem", "content": "Demand exists on operator forums",
     "evidence_type": "FACT", "source": "https://example.com", "confidence": 0.8}
    """
    ingest_agent_output(empty_state, blob, "problem_agent")
    assert len(empty_state.evidence) == 1
    assert empty_state.evidence[0].content.startswith("Demand exists")


def test_python_loop_skips_failed_specialist_and_continues():
    session = _session(max_iterations=5)
    calls: list[str] = []

    def dispatch(_sess: ResearchSession, name: str) -> str:
        calls.append(name)
        if name == "competition_agent":
            raise RuntimeError("503 Service Unavailable")
        return name

    notes = run_research_loop(session, dispatch_fn=dispatch)
    assert calls[:3] == ["problem_agent", "competition_agent", "economics_agent"]
    assert "competition_agent failed" in notes
    assert "Specialist skipped" in notes


def test_python_loop_stops_when_cancelled():
    session = _session(max_iterations=5)
    calls: list[str] = []
    cancelled = False

    def should_stop() -> bool:
        return cancelled

    session.should_stop = should_stop

    def dispatch(_sess: ResearchSession, name: str) -> str:
        nonlocal cancelled
        calls.append(name)
        if name == "problem_agent":
            cancelled = True
        return name

    try:
        run_research_loop(session, dispatch_fn=dispatch)
        raise AssertionError("cancelled loop should not finish")
    except InvestigationCancelled:
        pass

    assert calls == ["problem_agent"]
    assert session.dispatched == ["problem_agent"]


def test_transient_provider_errors_are_detected():
    from src.agents.orchestrator import _is_transient_provider_error

    assert _is_transient_provider_error(RuntimeError("503 Service Unavailable"))
    assert _is_transient_provider_error(RuntimeError("status: UNAVAILABLE"))
    assert not _is_transient_provider_error(RuntimeError("AccessDeniedException"))


def test_run_diligence_emits_safety_progress():
    events: list[dict] = []
    from unittest.mock import patch

    rejected = ScopeResult(is_valid=False, rejection_reason="too spicy", sanitized_idea="")
    with patch("src.agents.orchestrator.evaluate_scope_and_safety", return_value=rejected):
        run_diligence("An app that helps restaurants track food inventory waste", on_progress=events.append)
    assert events
    assert events[0]["phase"] == "safety"
    assert any("Rejected" in event["message"] for event in events)
