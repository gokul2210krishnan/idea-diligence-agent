from src.models import DecisionImpact, DiligenceState, EvidenceType, UnknownStatus, Verdict


def test_state_helpers_track_budget_and_unknowns():
    state = DiligenceState(idea="Test idea", max_iterations=2)
    assert state.has_budget_remaining() is True
    assert state.is_research_complete() is False

    state.add_unknown("What is CAC?", category="pricing", importance=DecisionImpact.CRITICAL)
    state.add_unknown("Nice-to-know brand color?", category="general", importance=DecisionImpact.LOW)
    state.add_evidence("Demand exists", EvidenceType.UNKNOWN, confidence=0.2, category="problem")
    prioritized = state.get_prioritized_unknowns()
    assert prioritized[0].importance == DecisionImpact.CRITICAL
    assert "Demand exists" in state.get_critical_unknowns()

    state.log_action("problem_agent", "search", "found demand")
    state.log_action("competition_agent", "search", "found rivals")
    assert state.iteration_count == 2
    assert state.has_budget_remaining() is False


def test_verdict_enum_values():
    assert {v.value for v in Verdict} == {"GO", "MODIFY", "KILL"}
    assert UnknownStatus.OPEN.value == "OPEN"
