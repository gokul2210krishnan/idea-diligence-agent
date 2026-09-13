"""
Evidence classifier and confidence scoring.

Phase 3 refines every finding before the verdict engine consumes it:
  - FACT requires provenance; otherwise it is downgraded
  - Confidence is recalibrated from type + source quality
  - Aggregates produce a single investigation-level confidence
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models import DiligenceState, Evidence, EvidenceType, UnknownStatus, DecisionImpact


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

_UNKNOWN_MARKERS = (
    "unknown",
    "unclear",
    "couldn't find",
    "could not find",
    "not found",
    "no data",
    "unable to determine",
    "insufficient evidence",
)
_ASSUMPTION_MARKERS = (
    "assume",
    "assumption",
    "we believe",
    "probably",
    "likely",
    "might",
    "seems to",
    "expected to",
)
_INFERENCE_MARKERS = (
    "therefore",
    "this suggests",
    "this implies",
    "implies that",
    "we infer",
    "based on this",
    "which indicates",
)


@dataclass
class ClassificationResult:
    """Outcome of refining a single finding."""
    evidence_type: EvidenceType
    confidence: float
    notes: list[str] = field(default_factory=list)


def _has_source(source: str | None) -> bool:
    return bool(source and source.strip())


def _has_url(source: str | None, content: str) -> bool:
    blob = f"{source or ''} {content}"
    return bool(_URL_RE.search(blob))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def classify_evidence(
    content: str,
    claimed_type: str | EvidenceType,
    source: str | None = None,
    confidence: float = 0.5,
) -> ClassificationResult:
    """Refine an evidence type and confidence using provenance rules.

    Agents may over-label findings as FACT. This function is the
    deterministic second opinion used by the verdict engine.
    """
    notes: list[str] = []
    text = (content or "").strip()
    claimed = (
        claimed_type.value
        if isinstance(claimed_type, EvidenceType)
        else str(claimed_type).upper().strip()
    )

    try:
        current = EvidenceType(claimed)
    except ValueError:
        current = EvidenceType.INFERENCE
        notes.append(f"Unknown claimed type '{claimed}' — defaulted to INFERENCE.")

    score = min(1.0, max(0.0, float(confidence)))

    if not text:
        return ClassificationResult(EvidenceType.UNKNOWN, 0.1, ["Empty content cannot be evidence."])

    if _contains_any(text, _UNKNOWN_MARKERS) and current != EvidenceType.FACT:
        current = EvidenceType.UNKNOWN
        notes.append("Language indicates an unresolved gap.")

    if current == EvidenceType.FACT and not _has_source(source):
        current = EvidenceType.INFERENCE
        score = min(score, 0.5)
        notes.append("FACT without a source was downgraded to INFERENCE.")
    elif current == EvidenceType.FACT and _has_url(source, text):
        score = max(score, 0.75)
    elif current == EvidenceType.FACT:
        score = max(0.6, min(score, 0.85))
        notes.append("FACT has a non-URL source; confidence capped.")

    if current == EvidenceType.ASSUMPTION:
        score = min(score, 0.45)
    elif current == EvidenceType.INFERENCE:
        score = min(max(score, 0.4), 0.7)
    elif current == EvidenceType.UNKNOWN:
        score = min(score, 0.25)

    if current == EvidenceType.FACT and _contains_any(text, _ASSUMPTION_MARKERS):
        current = EvidenceType.ASSUMPTION
        score = min(score, 0.45)
        notes.append("Hedging language is inconsistent with a FACT label.")
    elif current == EvidenceType.FACT and _contains_any(text, _INFERENCE_MARKERS):
        current = EvidenceType.INFERENCE
        score = min(max(score, 0.4), 0.7)
        notes.append("Inferential language is inconsistent with a FACT label.")

    return ClassificationResult(current, round(score, 3), notes)


def score_confidence(evidence: Evidence) -> float:
    """Return a recalibrated confidence for one evidence item."""
    result = classify_evidence(
        content=evidence.content,
        claimed_type=evidence.evidence_type,
        source=evidence.source,
        confidence=evidence.confidence,
    )
    return result.confidence


def refine_state_evidence(state: DiligenceState) -> list[str]:
    """Reclassify every finding on the state in place.

    Returns a list of classifier notes (useful for tests and audit logs).
    """
    notes: list[str] = []
    for item in state.evidence:
        result = classify_evidence(
            content=item.content,
            claimed_type=item.evidence_type,
            source=item.source,
            confidence=item.confidence,
        )
        item.evidence_type = result.evidence_type
        item.confidence = result.confidence
        notes.extend(result.notes)
    return notes


def aggregate_confidence(state: DiligenceState) -> float:
    """Compute investigation-level confidence from evidence quality and unknowns."""
    weights = {
        EvidenceType.FACT: 1.0,
        EvidenceType.INFERENCE: 0.6,
        EvidenceType.ASSUMPTION: 0.35,
        EvidenceType.UNKNOWN: 0.1,
    }

    if not state.evidence:
        base = 0.3
    else:
        weighted = sum(item.confidence * weights[item.evidence_type] for item in state.evidence)
        total_weight = sum(weights[item.evidence_type] for item in state.evidence)
        base = weighted / total_weight if total_weight else 0.3

    open_unknowns = [u for u in state.unknowns if u.status != UnknownStatus.RESOLVED]
    critical = sum(1 for u in open_unknowns if u.importance == DecisionImpact.CRITICAL)
    other = len(open_unknowns) - critical
    penalty = min(0.4, 0.08 * critical + 0.04 * other)

    fact_count = sum(1 for e in state.evidence if e.evidence_type == EvidenceType.FACT)
    if fact_count >= 3:
        base = min(0.95, base + 0.05)

    return round(min(0.95, max(0.05, base - penalty)), 3)


def evidence_breakdown(state: DiligenceState) -> dict[str, int]:
    """Return counts keyed by evidence type name."""
    counts = {"facts": 0, "assumptions": 0, "inferences": 0, "unknowns": 0}
    for item in state.evidence:
        if item.evidence_type == EvidenceType.FACT:
            counts["facts"] += 1
        elif item.evidence_type == EvidenceType.ASSUMPTION:
            counts["assumptions"] += 1
        elif item.evidence_type == EvidenceType.INFERENCE:
            counts["inferences"] += 1
        else:
            counts["unknowns"] += 1
    return counts
