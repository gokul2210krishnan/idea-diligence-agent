"""
Budget Governor — Deterministic circuit breaker for runtime limits.

This is the SECOND defense boundary. It enforces hard limits on:
  - Total research iterations (orchestrator loops)
  - Total tool calls across all agents
  - Tool calls per individual agent invocation
  - Wall-clock elapsed time

When any limit is hit, the governor signals the orchestrator to stop
researching and synthesize a verdict from whatever evidence exists.

All limits are deterministic — no LLM is involved in budget decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BudgetGovernor:
    """Enforces hard runtime boundaries on the research pipeline.

    Usage:
        governor = BudgetGovernor(max_iterations=5)
        governor.start()

        while not governor.is_exhausted():
            governor.record_iteration()
            # ... run an agent ...
            governor.record_tool_call("problem_agent")
    """

    # --- Configurable limits ---
    max_iterations: int = 5
    max_tool_calls_total: int = 25
    max_tool_calls_per_agent: int = 8
    max_wallclock_seconds: float = 180.0

    # --- Internal counters ---
    iteration_count: int = field(default=0, init=False)
    tool_calls_total: int = field(default=0, init=False)
    tool_calls_by_agent: dict[str, int] = field(default_factory=dict, init=False)
    _start_time: Optional[float] = field(default=None, init=False)
    _exhaustion_reason: Optional[str] = field(default=None, init=False)

    def start(self) -> None:
        """Mark the start of the research session. Call once before the loop."""
        self._start_time = time.monotonic()
        self._exhaustion_reason = None

    def record_iteration(self) -> None:
        """Record one orchestrator loop iteration."""
        self.iteration_count += 1

    def record_tool_call(self, agent_name: str) -> None:
        """Record a tool call made by a specific agent.

        Args:
            agent_name: The name of the agent that made the tool call.
        """
        self.tool_calls_total += 1
        self.tool_calls_by_agent[agent_name] = (
            self.tool_calls_by_agent.get(agent_name, 0) + 1
        )

    def elapsed_seconds(self) -> float:
        """Return wall-clock seconds since start()."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def is_exhausted(self) -> bool:
        """Check if ANY budget limit has been reached.

        Returns:
            True if the orchestrator should stop researching and force a verdict.
        """
        # Check iteration limit
        if self.iteration_count >= self.max_iterations:
            self._exhaustion_reason = (
                f"Iteration limit reached ({self.iteration_count}/{self.max_iterations})"
            )
            return True

        # Check total tool call limit
        if self.tool_calls_total >= self.max_tool_calls_total:
            self._exhaustion_reason = (
                f"Total tool call limit reached ({self.tool_calls_total}/{self.max_tool_calls_total})"
            )
            return True

        # Check wall-clock time
        if self._start_time is not None:
            elapsed = self.elapsed_seconds()
            if elapsed >= self.max_wallclock_seconds:
                self._exhaustion_reason = (
                    f"Wall-clock time limit reached ({elapsed:.1f}s / {self.max_wallclock_seconds:.1f}s)"
                )
                return True

        return False

    def is_agent_over_budget(self, agent_name: str) -> bool:
        """Check if a specific agent has exceeded its per-agent tool call limit.

        Args:
            agent_name: The agent to check.

        Returns:
            True if the agent should not be called again.
        """
        return self.tool_calls_by_agent.get(agent_name, 0) >= self.max_tool_calls_per_agent

    @property
    def exhaustion_reason(self) -> Optional[str]:
        """Human-readable reason why the budget was exhausted."""
        # Re-check to ensure reason is current
        self.is_exhausted()
        return self._exhaustion_reason

    def get_status(self) -> dict:
        """Return a snapshot of all budget counters.

        Useful for logging and for the CLI governance summary.
        """
        return {
            "iterations": f"{self.iteration_count}/{self.max_iterations}",
            "tool_calls_total": f"{self.tool_calls_total}/{self.max_tool_calls_total}",
            "tool_calls_by_agent": dict(self.tool_calls_by_agent),
            "elapsed_seconds": round(self.elapsed_seconds(), 1),
            "max_wallclock_seconds": self.max_wallclock_seconds,
            "is_exhausted": self.is_exhausted(),
            "exhaustion_reason": self._exhaustion_reason,
        }

    def remaining_summary(self) -> str:
        """One-line summary of remaining budget for prompt injection."""
        remaining_iters = max(0, self.max_iterations - self.iteration_count)
        remaining_calls = max(0, self.max_tool_calls_total - self.tool_calls_total)
        remaining_time = max(0.0, self.max_wallclock_seconds - self.elapsed_seconds())
        return (
            f"Budget remaining: {remaining_iters} iterations, "
            f"{remaining_calls} tool calls, "
            f"{remaining_time:.0f}s wall-clock"
        )
