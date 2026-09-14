"""Structured investigation progress for CLI prints and the web UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

ProgressCallback = Callable[[dict[str, Any]], None]

AGENT_LABELS = {
    "problem_agent": "Problem specialist",
    "competition_agent": "Competition specialist",
    "economics_agent": "Economics specialist",
}


def progress_event(
    *,
    phase: str,
    message: str,
    level: str = "info",
    agent: str | None = None,
    tool: str | None = None,
    evidence_count: int | None = None,
) -> dict[str, Any]:
    return {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phase": phase,
        "level": level,
        "message": message,
        "agent": agent,
        "tool": tool,
        "evidence_count": evidence_count,
    }


def emit(
    callback: Optional[ProgressCallback],
    *,
    phase: str,
    message: str,
    level: str = "info",
    agent: str | None = None,
    tool: str | None = None,
    evidence_count: int | None = None,
) -> None:
    """Print a CLI line and notify the web job poller."""
    tag = phase.upper()
    print(f"  [{tag}] {message}")
    if callback is None:
        return
    callback(
        progress_event(
            phase=phase,
            message=message,
            level=level,
            agent=agent,
            tool=tool,
            evidence_count=evidence_count,
        )
    )


def specialist_label(agent_name: str) -> str:
    return AGENT_LABELS.get(agent_name, agent_name)
