"""Load the canned investigation used by CLI --demo and the web demo button."""

from __future__ import annotations

import json
from pathlib import Path

from src.governance.safety_gate import ScopeResult
from src.models import DiligenceState
from src.verdict import synthesize_verdict


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "sample_investigation.json"

_DEMO_BUDGET = {
    "iterations": "3/5",
    "tool_calls_total": "12/25",
    "tool_calls_by_agent": {
        "problem_agent": 4,
        "competition_agent": 4,
        "economics_agent": 4,
    },
    "elapsed_seconds": 94.0,
    "max_wallclock_seconds": 300.0,
    "is_exhausted": False,
    "exhaustion_reason": None,
}


def load_sample_state() -> DiligenceState:
    """Return the example DiligenceState without synthesizing a verdict."""
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    return DiligenceState.model_validate(raw)


def load_sample_investigation() -> tuple[DiligenceState, ScopeResult, dict]:
    """Return a fully scored sample investigation for demos and tests."""
    state = load_sample_state()
    synthesize_verdict(state, use_llm=False)
    scope = ScopeResult(
        is_valid=True,
        sanitized_idea=state.idea,
        risk_flags=[],
    )
    return state, scope, dict(_DEMO_BUDGET)
