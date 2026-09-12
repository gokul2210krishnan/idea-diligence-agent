"""
Data models for the Idea Diligence Agent.

These Pydantic models define the "DiligenceState" — the single source of truth
for everything the system currently knows about the idea being investigated.

Every specialist agent reads from and writes back to this state.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence types — every finding is tagged so the orchestrator knows
# how confident it can be in the overall picture.
# ---------------------------------------------------------------------------

class EvidenceType(str, Enum):
    """How reliable is this piece of information?"""
    FACT = "FACT"                # Verified, sourced information
    ASSUMPTION = "ASSUMPTION"    # Something we believe but haven't verified
    INFERENCE = "INFERENCE"      # A conclusion drawn from facts
    UNKNOWN = "UNKNOWN"          # Something important we still don't know


class Verdict(str, Enum):
    """The final decision about the idea."""
    GO = "GO"           # Evidence supports proceeding
    MODIFY = "MODIFY"   # Idea has potential but needs changes
    KILL = "KILL"       # Evidence says don't pursue


# ---------------------------------------------------------------------------
# Building blocks — small models that the agents produce as outputs
# ---------------------------------------------------------------------------

class Evidence(BaseModel):
    """A single piece of evidence discovered during research."""
    content: str = Field(description="What was discovered")
    evidence_type: EvidenceType = Field(description="FACT, ASSUMPTION, INFERENCE, or UNKNOWN")
    source: Optional[str] = Field(default=None, description="Where this came from (URL, report, etc.)")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="How confident we are (0-1)")


class CustomerSegment(BaseModel):
    """A group of people who might use this product."""
    name: str = Field(description="Who they are (e.g., 'SMB restaurant owners')")
    pain_points: list[str] = Field(default_factory=list, description="What problems they face")
    size_estimate: Optional[str] = Field(default=None, description="Rough market size")


class Competitor(BaseModel):
    """A company or product that solves a similar problem."""
    name: str = Field(description="Competitor name")
    description: str = Field(default="", description="What they do")
    pricing: Optional[str] = Field(default=None, description="What they charge")
    strengths: list[str] = Field(default_factory=list, description="What they do well")
    weaknesses: list[str] = Field(default_factory=list, description="Where they fall short")
    url: Optional[str] = Field(default=None, description="Their website")


class BusinessModel(BaseModel):
    """A way the product could make money."""
    model_type: str = Field(description="E.g., 'subscription', 'usage-based', 'freemium'")
    pricing_range: Optional[str] = Field(default=None, description="Suggested price range")
    reasoning: str = Field(default="", description="Why this model makes sense")


class ResearchAction(BaseModel):
    """A record of what an agent did during research."""
    agent_name: str = Field(description="Which agent performed this action")
    action: str = Field(description="What the agent did")
    timestamp: datetime = Field(default_factory=datetime.now)
    findings_summary: str = Field(default="", description="Brief summary of what was found")


# ---------------------------------------------------------------------------
# The main state object — this is the heart of the system
# ---------------------------------------------------------------------------

class ProblemAnalysis(BaseModel):
    """The orchestrator's understanding of the problem the idea solves."""
    problem_statement: str = Field(default="", description="What problem does this idea solve?")
    severity: Optional[str] = Field(default=None, description="How painful is this problem?")
    existing_solutions: list[str] = Field(default_factory=list, description="How people currently solve it")
    demand_signals: list[str] = Field(default_factory=list, description="Signs that people want a solution")


class EconomicAnalysis(BaseModel):
    """Financial viability assessment."""
    market_size: Optional[str] = Field(default=None, description="Total addressable market estimate")
    revenue_potential: Optional[str] = Field(default=None, description="Realistic revenue estimate")
    business_models: list[BusinessModel] = Field(default_factory=list)
    unit_economics: Optional[str] = Field(default=None, description="Cost vs. revenue per customer")


class VerdictReport(BaseModel):
    """The final verdict with supporting evidence."""
    decision: Verdict = Field(description="GO, MODIFY, or KILL")
    confidence: float = Field(ge=0.0, le=1.0, description="How confident the system is (0-1)")
    summary: str = Field(description="One-paragraph executive summary")
    key_evidence: list[str] = Field(default_factory=list, description="Top evidence supporting this decision")
    modifications: list[str] = Field(
        default_factory=list,
        description="If MODIFY: what should change. Empty for GO/KILL.",
    )
    remaining_unknowns: list[str] = Field(
        default_factory=list,
        description="Important things the system couldn't determine",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="What the verdict depends on being true",
    )


class DiligenceState(BaseModel):
    """
    The single source of truth for a research investigation.

    Every specialist agent reads from this state and writes updates back to it.
    The orchestrator uses this state to decide what to research next.
    """

    # --- The idea being investigated ---
    idea: str = Field(description="The original idea text from the user")

    # --- Research findings (updated by specialist agents) ---
    problem: ProblemAnalysis = Field(default_factory=ProblemAnalysis)
    customers: list[CustomerSegment] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    economics: EconomicAnalysis = Field(default_factory=EconomicAnalysis)

    # --- Evidence tracking ---
    evidence: list[Evidence] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    # --- Audit trail ---
    research_history: list[ResearchAction] = Field(default_factory=list)

    # --- Final output ---
    verdict: Optional[VerdictReport] = Field(default=None)

    # --- Session metadata ---
    created_at: datetime = Field(default_factory=datetime.now)
    iteration_count: int = Field(default=0, description="How many research loops have run")
    max_iterations: int = Field(default=5, description="Safety limit to prevent infinite loops")

    def is_research_complete(self) -> bool:
        """Check if we have enough evidence to make a verdict."""
        return self.verdict is not None

    def has_budget_remaining(self) -> bool:
        """Check if we haven't exceeded the maximum research iterations."""
        return self.iteration_count < self.max_iterations

    def get_critical_unknowns(self) -> list[str]:
        """Return unknowns that are tagged as UNKNOWN in evidence."""
        return [
            e.content for e in self.evidence
            if e.evidence_type == EvidenceType.UNKNOWN
        ] + self.unknowns

    def add_evidence(self, content: str, evidence_type: EvidenceType,
                     source: str | None = None, confidence: float = 0.5) -> None:
        """Helper to add a new piece of evidence to the state."""
        self.evidence.append(Evidence(
            content=content,
            evidence_type=evidence_type,
            source=source,
            confidence=confidence,
        ))

    def log_action(self, agent_name: str, action: str, findings: str = "") -> None:
        """Record what an agent did (for the audit trail)."""
        self.research_history.append(ResearchAction(
            agent_name=agent_name,
            action=action,
            findings_summary=findings,
        ))
        self.iteration_count += 1
