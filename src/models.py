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


class DecisionImpact(str, Enum):
    """How much an unknown affects the GO / MODIFY / KILL decision."""
    CRITICAL = "CRITICAL"  # Verdict cannot be trusted without resolving this
    HIGH = "HIGH"          # Significantly affects confidence in the verdict
    MEDIUM = "MEDIUM"      # Affects verdict nuance but not direction
    LOW = "LOW"            # Nice to know, won't change the decision


class UnknownStatus(str, Enum):
    """Lifecycle state of an unknown."""
    OPEN = "OPEN"                # Not yet investigated
    INVESTIGATING = "INVESTIGATING"  # An agent is currently researching this
    RESOLVED = "RESOLVED"        # Answered with evidence


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
    category: str = Field(
        default="general",
        description="Research area: problem, customer, competitor, pricing, market_size, etc.",
    )


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


class UnknownItem(BaseModel):
    """A structured unknown — something important the system doesn't know yet.

    Unlike raw strings, UnknownItems carry decision-impact metadata so the
    adaptive loop can prioritize which gaps to investigate next.
    """
    question: str = Field(description="What we don't know (phrased as a question)")
    category: str = Field(
        default="general",
        description="Which research area (problem, customer, competitor, pricing, market_size)",
    )
    importance: DecisionImpact = Field(
        default=DecisionImpact.MEDIUM,
        description="How much this unknown affects the final verdict",
    )
    hypothesis: Optional[str] = Field(
        default=None,
        description="Best guess answer (to be validated by research)",
    )
    status: UnknownStatus = Field(
        default=UnknownStatus.OPEN,
        description="OPEN, INVESTIGATING, or RESOLVED",
    )


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


class EvidenceBreakdown(BaseModel):
    """Counts of evidence by epistemic type."""
    facts: int = 0
    assumptions: int = 0
    inferences: int = 0
    unknowns: int = 0


class DimensionScores(BaseModel):
    """0-1 scores for the three diligence dimensions."""
    problem: float = Field(default=0.5, ge=0.0, le=1.0)
    competition: float = Field(default=0.5, ge=0.0, le=1.0)
    economics: float = Field(default=0.5, ge=0.0, le=1.0)


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
    evidence_breakdown: EvidenceBreakdown = Field(default_factory=EvidenceBreakdown)
    dimension_scores: DimensionScores = Field(default_factory=DimensionScores)
    risks: list[str] = Field(default_factory=list, description="Key risks that could invalidate the verdict")
    next_steps: list[str] = Field(default_factory=list, description="Recommended actions after this verdict")
    method: str = Field(
        default="deterministic",
        description="How the verdict was produced: deterministic, llm, or hybrid",
    )
    generated_at: datetime = Field(default_factory=datetime.now)


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
    unknowns: list[UnknownItem] = Field(default_factory=list)

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
        """Return unknowns that are tagged as UNKNOWN in evidence plus open UnknownItems."""
        evidence_unknowns = [
            e.content for e in self.evidence
            if e.evidence_type == EvidenceType.UNKNOWN
        ]
        item_unknowns = [
            u.question for u in self.unknowns
            if u.status != UnknownStatus.RESOLVED
        ]
        return evidence_unknowns + item_unknowns

    def get_prioritized_unknowns(self) -> list[UnknownItem]:
        """Return open unknowns sorted by decision impact (CRITICAL first).

        The adaptive loop uses this to decide which gap to investigate next.
        """
        priority_order = {
            DecisionImpact.CRITICAL: 0,
            DecisionImpact.HIGH: 1,
            DecisionImpact.MEDIUM: 2,
            DecisionImpact.LOW: 3,
        }
        open_unknowns = [
            u for u in self.unknowns
            if u.status != UnknownStatus.RESOLVED
        ]
        return sorted(open_unknowns, key=lambda u: priority_order.get(u.importance, 99))

    def add_unknown(self, question: str, category: str = "general",
                    importance: DecisionImpact = DecisionImpact.MEDIUM,
                    hypothesis: str | None = None) -> None:
        """Helper to add a structured unknown to the state."""
        self.unknowns.append(UnknownItem(
            question=question,
            category=category,
            importance=importance,
            hypothesis=hypothesis,
        ))

    def add_evidence(self, content: str, evidence_type: EvidenceType,
                     source: str | None = None, confidence: float = 0.5,
                     category: str = "general") -> None:
        """Helper to add a new piece of evidence to the state."""
        self.evidence.append(Evidence(
            content=content,
            evidence_type=evidence_type,
            source=source,
            confidence=confidence,
            category=category,
        ))

    def log_action(self, agent_name: str, action: str, findings: str = "") -> None:
        """Record what an agent did (for the audit trail)."""
        self.research_history.append(ResearchAction(
            agent_name=agent_name,
            action=action,
            findings_summary=findings,
        ))
        self.iteration_count += 1
