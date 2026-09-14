"""
Verdict synthesis engine — GO / MODIFY / KILL.

The engine scores three diligence dimensions from classified evidence,
then renders a structured VerdictReport. An optional LLM pass can refine
the prose; the decision itself is always constrained by deterministic rules.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from src.evidence import aggregate_confidence, evidence_breakdown, refine_state_evidence
from src.models import (
    Competitor,
    CustomerSegment,
    DecisionImpact,
    DiligenceState,
    DimensionScores,
    EvidenceBreakdown,
    EvidenceType,
    UnknownStatus,
    Verdict,
    VerdictReport,
)


# ---------------------------------------------------------------------------
# Dimension signal lexicons
# ---------------------------------------------------------------------------

_PROBLEM_POSITIVE = (
    "painful", "urgent", "demand", "frustrated", "hair on fire", "critical",
    "actively looking", "willing to pay", "high severity", "acute",
)
_PROBLEM_NEGATIVE = (
    "nice to have", "no demand", "not a real problem", "already solved",
    "low severity", "no one is looking", "solved already",
)
_COMP_POSITIVE = (
    "gap", "underserved", "complaints", "weakness", "opportunity",
    "whitespace", "poor reviews", "users complain",
)
_COMP_NEGATIVE = (
    "saturated", "crowded", "many competitors", "dominated", "incumbent",
    "free alternative", "no room", "winner-take-all",
)
_ECON_POSITIVE = (
    "viable", "large market", "healthy", "willingness to pay",
    "recurring revenue", "strong unit economics", "affordable cac",
)
_ECON_NEGATIVE = (
    "unviable", "too small", "cannot charge", "can't charge", "high cac",
    "thin margin", "no budget", "unsustainable",
)

_CATEGORY_DIMENSION = {
    "problem": "problem",
    "customer": "problem",
    "competitor": "competition",
    "pricing": "economics",
    "market_size": "economics",
    "business_model": "economics",
    "risk": "economics",
    "opportunity": "competition",
}

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_DECISION_RE = re.compile(r"\b(GO|MODIFY|KILL)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hits(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for marker in markers if marker in lowered)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_dimensions(state: DiligenceState) -> DimensionScores:
    """Score problem / competition / economics from classified evidence."""
    scores = {"problem": 0.5, "competition": 0.5, "economics": 0.5}
    weights = {"problem": 0.0, "competition": 0.0, "economics": 0.0}
    lexicons = {
        "problem": (_PROBLEM_POSITIVE, _PROBLEM_NEGATIVE),
        "competition": (_COMP_POSITIVE, _COMP_NEGATIVE),
        "economics": (_ECON_POSITIVE, _ECON_NEGATIVE),
    }

    for item in state.evidence:
        dimension = _CATEGORY_DIMENSION.get(item.category.lower(), None)
        if dimension is None:
            # Fall back to keyword routing when category is generic.
            blob = item.content.lower()
            if _hits(blob, _PROBLEM_POSITIVE + _PROBLEM_NEGATIVE):
                dimension = "problem"
            elif _hits(blob, _COMP_POSITIVE + _COMP_NEGATIVE):
                dimension = "competition"
            elif _hits(blob, _ECON_POSITIVE + _ECON_NEGATIVE):
                dimension = "economics"
            else:
                continue

        positive, negative = lexicons[dimension]
        pos = _hits(item.content, positive)
        neg = _hits(item.content, negative)
        signal = 0.5 + 0.15 * (pos - neg)
        if item.evidence_type == EvidenceType.FACT:
            signal += 0.05
        elif item.evidence_type == EvidenceType.UNKNOWN:
            signal -= 0.1
        signal = _clamp(signal)
        influence = 0.5 + item.confidence
        scores[dimension] = (
            (scores[dimension] * max(weights[dimension], 0.01) + signal * influence)
            / (max(weights[dimension], 0.01) + influence)
        )
        weights[dimension] += influence

    return DimensionScores(
        problem=round(_clamp(scores["problem"]), 3),
        competition=round(_clamp(scores["competition"]), 3),
        economics=round(_clamp(scores["economics"]), 3),
    )


def decide_verdict(
    scores: DimensionScores,
    critical_unknowns: int,
    fact_count: int,
) -> Verdict:
    """Apply deterministic GO / MODIFY / KILL rules."""
    if scores.problem < 0.35 or scores.economics < 0.30:
        return Verdict.KILL
    if (
        scores.problem >= 0.60
        and scores.competition >= 0.55
        and scores.economics >= 0.55
        and critical_unknowns == 0
        and fact_count >= 2
    ):
        return Verdict.GO
    return Verdict.MODIFY


def parse_orchestrator_verdict(text: str) -> Optional[dict]:
    """Extract a structured verdict fragment from free-text orchestrator output."""
    if not text or not text.strip():
        return None

    match = _JSON_BLOCK.search(text)
    if match:
        try:
            data = json.loads(match.group())
            decision = str(data.get("decision", "")).upper()
            if decision in {v.value for v in Verdict}:
                return data
        except json.JSONDecodeError:
            pass

    decision_match = _DECISION_RE.search(text)
    if not decision_match:
        return None

    confidence_match = re.search(r"confidence[^0-9]{0,12}(0(?:\.\d+)?|1(?:\.0+)?)", text, re.I)
    summary = ""
    for line in text.splitlines():
        if line.strip().lower().startswith("summary"):
            summary = line.split(":", 1)[-1].strip()
            break

    return {
        "decision": decision_match.group(1).upper(),
        "confidence": float(confidence_match.group(1)) if confidence_match else None,
        "summary": summary,
    }


def hydrate_state_from_evidence(state: DiligenceState) -> None:
    """Populate structured state fields from categorized evidence when empty."""
    for item in state.evidence:
        category = (item.category or "general").lower()
        if category == "problem" and not state.problem.problem_statement:
            state.problem.problem_statement = item.content
        elif category == "customer":
            name = item.content.split(":")[0][:80].strip()
            if name and not any(c.name.lower() == name.lower() for c in state.customers):
                state.customers.append(CustomerSegment(name=name, pain_points=[item.content]))
        elif category == "competitor":
            name = re.split(r"\s+(?:charges|is|offers|provides)\s+", item.content, maxsplit=1)[0]
            name = name.split(":")[0][:80].strip()
            if name and not any(c.name.lower() == name.lower() for c in state.competitors):
                state.competitors.append(
                    Competitor(name=name, description=item.content, url=item.source)
                )
        elif category == "market_size" and not state.economics.market_size:
            state.economics.market_size = item.content
        elif category == "pricing" and not state.economics.revenue_potential:
            state.economics.revenue_potential = item.content


def _top_evidence(state: DiligenceState, limit: int = 5) -> list[str]:
    ranked = sorted(
        state.evidence,
        key=lambda e: (
            0 if e.evidence_type == EvidenceType.FACT else
            1 if e.evidence_type == EvidenceType.INFERENCE else
            2 if e.evidence_type == EvidenceType.ASSUMPTION else 3,
            -e.confidence,
        ),
    )
    return [
        f"[{item.evidence_type.value}] {item.content}"
        + (f" ({item.source})" if item.source else "")
        for item in ranked[:limit]
    ]


def _assumptions(state: DiligenceState) -> list[str]:
    return [e.content for e in state.evidence if e.evidence_type == EvidenceType.ASSUMPTION][:5]


def _unknowns(state: DiligenceState) -> list[str]:
    open_items = [
        u.question for u in state.get_prioritized_unknowns()
    ]
    evidence_unknowns = [
        e.content for e in state.evidence if e.evidence_type == EvidenceType.UNKNOWN
    ]
    merged: list[str] = []
    for item in open_items + evidence_unknowns:
        if item not in merged:
            merged.append(item)
    return merged[:6]


def _modifications(decision: Verdict, scores: DimensionScores, idea: str) -> list[str]:
    if decision != Verdict.MODIFY:
        return []
    tips: list[str] = []
    if scores.problem < 0.55:
        tips.append("Narrow the target customer until the pain is acute and observable.")
    if scores.competition < 0.55:
        tips.append("Differentiate against incumbents; compete on a specific gap, not the whole category.")
    if scores.economics < 0.55:
        tips.append("Revisit pricing and buyer budget — current unit economics look fragile.")
    if not tips:
        tips.append("Keep the core problem, but tighten positioning before building an MVP.")
    tips.append(f"Re-test the revised concept: {idea[:140]}")
    return tips


def _risks(state: DiligenceState, scores: DimensionScores) -> list[str]:
    risks: list[str] = []
    if scores.competition < 0.45:
        risks.append("Crowded or incumbent-heavy market may leave little room to win.")
    if scores.economics < 0.45:
        risks.append("Willingness to pay or market size may not support a standalone product.")
    if scores.problem < 0.45:
        risks.append("The problem may be a nice-to-have rather than a buying trigger.")
    critical = [
        u.question for u in state.unknowns
        if u.status != UnknownStatus.RESOLVED and u.importance == DecisionImpact.CRITICAL
    ]
    risks.extend(critical[:2])
    return risks[:5]


def _next_steps(decision: Verdict) -> list[str]:
    if decision == Verdict.GO:
        return [
            "Interview 5–10 buyers in the named segment to confirm willingness to pay.",
            "Scope a thin MVP around the sharpest competitive gap.",
            "Draft pricing against the competitor range already found.",
        ]
    if decision == Verdict.MODIFY:
        return [
            "Apply the recommended modifications and re-run diligence on the revised idea.",
            "Validate the new segment or wedge with 5 customer conversations.",
            "Do not fund a broad build until the weakest dimension improves.",
        ]
    return [
        "Stop further build investment on this formulation.",
        "If you continue, treat it as a learning experiment with a hard time-box.",
        "Look for a related problem with clearer demand and pricing power.",
    ]


def _fallback_summary(idea: str, decision: Verdict, scores: DimensionScores) -> str:
    return (
        f"Verdict for '{idea[:160]}' is {decision.value}. "
        f"Problem score {scores.problem:.2f}, competition {scores.competition:.2f}, "
        f"economics {scores.economics:.2f}. "
        f"The recommendation is based on classified evidence, not founder enthusiasm."
    )


def _llm_refine(state: DiligenceState, orchestrator_text: str) -> Optional[dict]:
    """Optional LLM pass. Failures return None so the deterministic path stays in charge."""
    try:
        from strands import Agent
        from src.model_provider import ModelRole, create_model
        from src.prompts import VERDICT_ENGINE_PROMPT
    except Exception:
        return None

    try:
        agent = Agent(
            model=create_model(ModelRole.VERDICT),
            system_prompt=VERDICT_ENGINE_PROMPT,
            tools=[],
        )
        payload = {
            "idea": state.idea,
            "evidence": [e.model_dump() for e in state.evidence],
            "unknowns": [u.model_dump() for u in state.unknowns],
            "orchestrator_notes": orchestrator_text[:4000],
        }
        raw = str(agent(
            "Render a final diligence verdict from this state. JSON only.\n\n"
            + json.dumps(payload, default=str)
        ))
        match = _JSON_BLOCK.search(raw)
        if not match:
            return None
        data = json.loads(match.group())
        if str(data.get("decision", "")).upper() not in {v.value for v in Verdict}:
            return None
        return data
    except Exception:
        return None


def synthesize_verdict(
    state: DiligenceState,
    orchestrator_text: str = "",
    use_llm: bool = False,
) -> VerdictReport:
    """Build a VerdictReport from DiligenceState.

    Args:
        state: Investigation state (evidence is refined in place).
        orchestrator_text: Optional free-text notes from the orchestrator.
        use_llm: When True, try an LLM prose pass. Decision rules stay deterministic
                 unless the LLM agrees with the scored recommendation.

    Returns:
        A populated VerdictReport, also assigned to ``state.verdict``.
    """
    refine_state_evidence(state)
    hydrate_state_from_evidence(state)

    scores = score_dimensions(state)
    breakdown = evidence_breakdown(state)
    critical_unknowns = sum(
        1 for u in state.unknowns
        if u.status != UnknownStatus.RESOLVED and u.importance == DecisionImpact.CRITICAL
    )
    decision = decide_verdict(scores, critical_unknowns, breakdown["facts"])
    confidence = aggregate_confidence(state)
    method = "deterministic"

    parsed = parse_orchestrator_verdict(orchestrator_text)
    llm_data = _llm_refine(state, orchestrator_text) if use_llm else None
    prose_source = llm_data or parsed or {}

    if (
        llm_data
        and str(llm_data.get("decision", "")).upper() == decision.value
    ):
        method = "hybrid"
        try:
            llm_conf = float(llm_data.get("confidence", confidence))
            confidence = round(_clamp((confidence + llm_conf) / 2), 3)
        except (TypeError, ValueError):
            pass
    elif parsed and str(parsed.get("decision", "")).upper() == decision.value:
        method = "hybrid"
        if parsed.get("confidence") is not None:
            try:
                confidence = round(_clamp((confidence + float(parsed["confidence"])) / 2), 3)
            except (TypeError, ValueError):
                pass

    summary = (
        str(prose_source.get("summary") or "").strip()
        or _fallback_summary(state.idea, decision, scores)
    )
    key_evidence = prose_source.get("key_evidence") or _top_evidence(state)
    modifications = prose_source.get("modifications") if decision == Verdict.MODIFY else []
    if decision == Verdict.MODIFY and not modifications:
        modifications = _modifications(decision, scores, state.idea)
    if decision != Verdict.MODIFY:
        modifications = []

    report = VerdictReport(
        decision=decision,
        confidence=confidence,
        summary=summary,
        key_evidence=list(key_evidence)[:6],
        modifications=list(modifications)[:6],
        remaining_unknowns=list(prose_source.get("remaining_unknowns") or _unknowns(state))[:6],
        assumptions=list(prose_source.get("assumptions") or _assumptions(state))[:6],
        evidence_breakdown=EvidenceBreakdown(**breakdown),
        dimension_scores=scores,
        risks=list(prose_source.get("risks") or _risks(state, scores))[:5],
        next_steps=list(prose_source.get("next_steps") or _next_steps(decision))[:5],
        method=method,
    )
    state.verdict = report
    return report
