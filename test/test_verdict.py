from src.models import DiligenceState, EvidenceType, Verdict
from src.verdict import (
    decide_verdict,
    hydrate_state_from_evidence,
    parse_orchestrator_verdict,
    score_dimensions,
    synthesize_verdict,
)


def test_go_path(go_state: DiligenceState):
    report = synthesize_verdict(go_state, use_llm=False)
    assert report.decision == Verdict.GO
    assert report.confidence > 0.5
    assert report.modifications == []
    assert report.next_steps
    assert go_state.verdict is report


def test_kill_path(kill_state: DiligenceState):
    report = synthesize_verdict(kill_state, use_llm=False)
    assert report.decision == Verdict.KILL
    assert "not invest" in " ".join(report.next_steps).lower() or report.next_steps


def test_modify_path(modify_state: DiligenceState):
    report = synthesize_verdict(modify_state, use_llm=False)
    assert report.decision == Verdict.MODIFY
    assert report.modifications
    assert report.evidence_breakdown.facts >= 1


def test_empty_state_does_not_crash(empty_state: DiligenceState):
    report = synthesize_verdict(empty_state, use_llm=False)
    assert report.decision in {Verdict.GO, Verdict.MODIFY, Verdict.KILL}
    assert 0.05 <= report.confidence <= 0.95


def test_parse_json_and_plaintext_verdicts():
    json_text = '{"decision": "KILL", "confidence": 0.7, "summary": "No market."}'
    parsed = parse_orchestrator_verdict(json_text)
    assert parsed["decision"] == "KILL"
    assert parsed["confidence"] == 0.7

    plain = "Decision: MODIFY\nConfidence: 0.61\nSummary: Tighten the wedge."
    parsed_plain = parse_orchestrator_verdict(plain)
    assert parsed_plain["decision"] == "MODIFY"
    assert parsed_plain["summary"].startswith("Tighten")


def test_parse_empty_returns_none():
    assert parse_orchestrator_verdict("") is None
    assert parse_orchestrator_verdict("no decision here") is None


def test_hydrate_state_from_evidence(empty_state: DiligenceState):
    empty_state.add_evidence(
        "Walk-in spoilage is the core problem",
        EvidenceType.FACT,
        "https://example.com",
        0.8,
        "problem",
    )
    empty_state.add_evidence(
        "MarketMan charges $99/month",
        EvidenceType.FACT,
        "https://marketman.com",
        0.8,
        "competitor",
    )
    empty_state.add_evidence(
        "Independent restaurants with 1-3 locations: waste hits food cost",
        EvidenceType.INFERENCE,
        "",
        0.5,
        "customer",
    )
    hydrate_state_from_evidence(empty_state)
    assert empty_state.problem.problem_statement
    assert empty_state.competitors
    assert empty_state.customers


def test_decide_verdict_thresholds():
    from src.models import DimensionScores

    assert decide_verdict(DimensionScores(problem=0.2, competition=0.8, economics=0.8), 0, 5) == Verdict.KILL
    assert decide_verdict(DimensionScores(problem=0.8, competition=0.8, economics=0.2), 0, 5) == Verdict.KILL
    assert decide_verdict(DimensionScores(problem=0.7, competition=0.7, economics=0.7), 0, 3) == Verdict.GO
    assert decide_verdict(DimensionScores(problem=0.7, competition=0.7, economics=0.7), 2, 3) == Verdict.MODIFY


def test_hybrid_method_when_orchestrator_agrees(go_state: DiligenceState):
    report = synthesize_verdict(
        go_state,
        orchestrator_text='{"decision":"GO","confidence":0.8,"summary":"Strong fit."}',
        use_llm=False,
    )
    assert report.decision == Verdict.GO
    assert report.method == "hybrid"
    assert "Strong fit" in report.summary


def test_score_dimensions_responds_to_language(empty_state: DiligenceState):
    empty_state.add_evidence(
        "The problem is painful and urgent with real demand",
        EvidenceType.FACT,
        "https://example.com",
        0.9,
        "problem",
    )
    scores = score_dimensions(empty_state)
    assert scores.problem > 0.5
