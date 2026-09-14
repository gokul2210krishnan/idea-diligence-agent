"""Per-investigation session. No process-wide mutable research state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.governance.budget_governor import BudgetGovernor
from src.models import DiligenceState
from src.progress import emit as emit_progress


@dataclass
class ResearchSession:
    """Isolated runtime for one idea. Concurrent investigations must not share this."""

    state: DiligenceState
    governor: BudgetGovernor
    dispatched: list[str] = field(default_factory=list)
    follow_ups: int = 0
    on_progress: Optional[Callable[[dict[str, Any]], None]] = None

    def emit(
        self,
        phase: str,
        message: str,
        *,
        level: str = "info",
        agent: str | None = None,
        tool: str | None = None,
    ) -> None:
        emit_progress(
            self.on_progress,
            phase=phase,
            message=message,
            level=level,
            agent=agent,
            tool=tool,
            evidence_count=len(self.state.evidence),
        )
