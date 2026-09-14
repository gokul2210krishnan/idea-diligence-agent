"""Per-investigation session. No process-wide mutable research state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.governance.budget_governor import BudgetGovernor
from src.models import DiligenceState
from src.progress import emit as emit_progress


class InvestigationCancelled(Exception):
    """Raised when the operator stops a live investigation."""


@dataclass
class ResearchSession:
    """Isolated runtime for one idea. Concurrent investigations must not share this."""

    state: DiligenceState
    governor: BudgetGovernor
    dispatched: list[str] = field(default_factory=list)
    follow_ups: int = 0
    on_progress: Optional[Callable[[dict[str, Any]], None]] = None
    should_stop: Optional[Callable[[], bool]] = None

    def stop_requested(self) -> bool:
        return bool(self.should_stop and self.should_stop())

    def raise_if_stopped(self) -> None:
        if self.stop_requested():
            raise InvestigationCancelled()

    def emit(
        self,
        phase: str,
        message: str,
        *,
        level: str = "info",
        agent: str | None = None,
        tool: str | None = None,
    ) -> None:
        self.raise_if_stopped()
        emit_progress(
            self.on_progress,
            phase=phase,
            message=message,
            level=level,
            agent=agent,
            tool=tool,
            evidence_count=len(self.state.evidence),
        )
