"""
State Updater — Propose-Validate-Merge pipeline for structured state changes.

This is the FOURTH defense boundary. Instead of agents directly mutating
the DiligenceState, they submit FindingProposals which are validated:

  1. Schema validation  — FACTs require non-empty source
  2. Authorization      — agents can only write to their designated categories
  3. Contradiction check — flags when new evidence conflicts with existing high-confidence FACTs

Only proposals that pass all checks are merged into the authoritative state.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.models import DiligenceState, Evidence, EvidenceType


# ---------------------------------------------------------------------------
# Authorization map — which agents can write to which categories
# ---------------------------------------------------------------------------

_AGENT_PERMISSIONS: dict[str, set[str]] = {
    "problem_agent": {
        "problem", "customer", "risk", "opportunity", "unknown",
    },
    "competition_agent": {
        "competitor", "pricing", "risk", "opportunity", "unknown",
    },
    "economics_agent": {
        "pricing", "market_size", "business_model", "risk", "opportunity", "unknown",
    },
    "orchestrator": {
        "problem", "customer", "competitor", "pricing",
        "market_size", "business_model", "risk", "opportunity", "unknown",
    },
}

# Contradiction threshold — if an existing FACT has confidence >= this,
# a conflicting proposal triggers a warning.
_CONTRADICTION_CONFIDENCE_THRESHOLD = 0.8


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FindingProposal(BaseModel):
    """A structured proposal to add evidence to the DiligenceState.

    Agents produce these instead of directly mutating state.
    """
    category: str = Field(description="Evidence category (problem, customer, competitor, etc.)")
    content: str = Field(description="What was discovered")
    evidence_type: str = Field(description="FACT, ASSUMPTION, INFERENCE, or UNKNOWN")
    source: str = Field(default="", description="Where this came from (URL, report, etc.)")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence (0-1)")
    proposed_by: str = Field(description="Which agent submitted this proposal")


class MergeResult(BaseModel):
    """The outcome of validating and merging a FindingProposal."""
    accepted: bool = Field(description="Whether the proposal was merged into state")
    reason: str = Field(description="Why it was accepted or rejected")
    evidence: Optional[Evidence] = Field(
        default=None,
        description="The Evidence object that was created (None if rejected)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking warnings (e.g., potential contradiction)",
    )


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def _validate_schema(proposal: FindingProposal) -> tuple[bool, str]:
    """Check structural validity of the proposal.

    Returns:
        (valid, reason)
    """
    # Validate evidence type
    valid_types = {e.value for e in EvidenceType}
    if proposal.evidence_type.upper() not in valid_types:
        return False, (
            f"Invalid evidence_type '{proposal.evidence_type}'. "
            f"Must be one of: {', '.join(sorted(valid_types))}"
        )

    # FACTs require a source
    if proposal.evidence_type.upper() == "FACT" and not proposal.source.strip():
        return False, "Evidence type FACT requires a non-empty source URL or reference."

    # Content must not be empty
    if not proposal.content.strip():
        return False, "Evidence content cannot be empty."

    return True, "Schema valid"


def _validate_authorization(proposal: FindingProposal) -> tuple[bool, str]:
    """Check that the agent is allowed to write to this category.

    Returns:
        (authorized, reason)
    """
    agent = proposal.proposed_by.lower()
    allowed = _AGENT_PERMISSIONS.get(agent)

    if allowed is None:
        return False, (
            f"Unknown agent '{agent}' is not authorized to write state. "
            f"Known agents: {', '.join(sorted(_AGENT_PERMISSIONS))}"
        )

    if proposal.category.lower() not in allowed:
        return False, (
            f"Agent '{agent}' is not authorized to write to category '{proposal.category}'. "
            f"Allowed categories: {', '.join(sorted(allowed))}"
        )

    return True, "Authorized"


def _check_contradiction(
    proposal: FindingProposal,
    state: DiligenceState,
) -> list[str]:
    """Check if the proposal contradicts existing high-confidence evidence.

    This is a heuristic check — it flags potential contradictions as warnings
    but does NOT block the merge. Human review or orchestrator judgment
    resolves conflicts.

    Returns:
        List of warning strings (empty if no contradictions detected).
    """
    warnings: list[str] = []

    for existing in state.evidence:
        # Only check existing FACTs with high confidence
        if (
            existing.evidence_type == EvidenceType.FACT
            and existing.confidence >= _CONTRADICTION_CONFIDENCE_THRESHOLD
        ):
            # Simple heuristic: same category + very different content
            # In practice, an LLM-based contradiction detector would be better,
            # but that costs budget. This catches obvious cases.
            existing_lower = existing.content.lower()
            proposal_lower = proposal.content.lower()

            # Check for negation patterns
            negation_pairs = [
                ("no competitors", "competitors include"),
                ("no market", "market size"),
                ("not viable", "viable"),
                ("unviable", "viable"),
            ]
            for neg, pos in negation_pairs:
                if (neg in existing_lower and pos in proposal_lower) or \
                   (pos in existing_lower and neg in proposal_lower):
                    warnings.append(
                        f"Potential contradiction: existing FACT (confidence={existing.confidence}) "
                        f"says '{existing.content[:80]}...' vs. proposed '{proposal.content[:80]}...'"
                    )
                    break

    return warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_and_merge(
    proposal: FindingProposal,
    state: DiligenceState,
) -> MergeResult:
    """Validate a FindingProposal and merge it into the DiligenceState if it passes.

    This is the single entry point for the state updater. All state mutations
    go through this function.

    Args:
        proposal: The evidence proposal from an agent.
        state: The current authoritative DiligenceState (mutated in-place if accepted).

    Returns:
        MergeResult describing the outcome.
    """
    # --- Step 1: Schema validation ---
    schema_ok, schema_reason = _validate_schema(proposal)
    if not schema_ok:
        return MergeResult(accepted=False, reason=f"Schema rejected: {schema_reason}")

    # --- Step 2: Authorization check ---
    auth_ok, auth_reason = _validate_authorization(proposal)
    if not auth_ok:
        return MergeResult(accepted=False, reason=f"Authorization rejected: {auth_reason}")

    # --- Step 3: Contradiction check (non-blocking) ---
    warnings = _check_contradiction(proposal, state)

    # --- Step 4: Merge into state ---
    evidence_type = EvidenceType(proposal.evidence_type.upper())
    evidence = Evidence(
        content=proposal.content,
        evidence_type=evidence_type,
        source=proposal.source if proposal.source.strip() else None,
        confidence=proposal.confidence,
        category=proposal.category or "general",
    )
    state.evidence.append(evidence)

    reason = "Accepted and merged"
    if warnings:
        reason += f" (with {len(warnings)} warning(s))"

    return MergeResult(
        accepted=True,
        reason=reason,
        evidence=evidence,
        warnings=warnings,
    )
