"""Per-investigation session. No process-wide mutable research state."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.governance.budget_governor import BudgetGovernor
from src.models import DiligenceState


@dataclass
class ResearchSession:
    """Isolated runtime for one idea. Concurrent investigations must not share this."""

    state: DiligenceState
    governor: BudgetGovernor
    dispatched: list[str] = field(default_factory=list)
    follow_ups: int = 0
