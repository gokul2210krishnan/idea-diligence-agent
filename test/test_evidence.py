from src.evidence import (
    aggregate_confidence,
    classify_evidence,
    evidence_breakdown,
    refine_state_evidence,
)
from src.models import DiligenceState, EvidenceType


def test_fact_without_source_is_downgraded():
    result = classify_evidence(
        content="There are many competitors in this space",
        claimed_type="FACT",
        source="",
        confidence=0.9,
    )
    assert result.evidence_type == EvidenceType.INFERENCE
    assert result.confidence <= 0.5
    assert any("downgraded" in note.lower() for note in result.notes)


def test_fact_with_url_keeps_high_confidence():
    result = classify_evidence(
        content="MarketMan publishes pricing on its site",
        claimed_type=EvidenceType.FACT,
        source="https://www.marketman.com/pricing",
        confidence=0.7,
    )
    assert result.evidence_type == EvidenceType.FACT
    assert result.confidence >= 0.75


def test_hedging_language_cannot_stay_a_fact():
    result = classify_evidence(
        content="We believe restaurants will probably adopt this",
        claimed_type="FACT",
        source="https://example.com",
        confidence=0.9,
    )
    assert result.evidence_type == EvidenceType.ASSUMPTION
    assert result.confidence <= 0.45


def test_unknown_markers_reclassify():
    result = classify_evidence(
        content="Customer acquisition cost is unknown and could not find data",
        claimed_type="INFERENCE",
        source="",
        confidence=0.6,
    )
    assert result.evidence_type == EvidenceType.UNKNOWN
    assert result.confidence <= 0.25


def test_empty_content_is_unknown():
    result = classify_evidence("", "FACT", "https://example.com", 0.9)
    assert result.evidence_type == EvidenceType.UNKNOWN


def test_refine_state_and_breakdown(empty_state: DiligenceState):
    empty_state.add_evidence(
        "A sourced fact about demand",
        EvidenceType.FACT,
        "https://example.com",
        0.8,
        "problem",
    )
    empty_state.add_evidence("We assume buyers exist", EvidenceType.FACT, "", 0.9, "customer")
    notes = refine_state_evidence(empty_state)
    counts = evidence_breakdown(empty_state)
    assert counts["facts"] == 1
    assert counts["inferences"] == 1
    assert notes
    assert 0.05 <= aggregate_confidence(empty_state) <= 0.95
