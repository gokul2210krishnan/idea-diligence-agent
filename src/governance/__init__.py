"""
Governance Layer — Defense-in-depth boundaries for the Idea Diligence Agent.

This package implements the five architectural invariants that keep
the multi-agent system safe, bounded, and auditable:

1. Safety Gate     — Pre-screens user input before any research begins
2. Budget Governor — Hard deterministic limits on runtime (iterations, tool calls, time)
3. Data Sanitizer  — Isolates untrusted web content in inert XML envelopes
4. State Updater   — Propose-Validate-Merge pipeline for structured state changes
"""

from src.governance.safety_gate import evaluate_scope_and_safety, ScopeResult
from src.governance.budget_governor import BudgetGovernor
from src.governance.data_sanitizer import sanitize_web_content
from src.governance.state_updater import validate_and_merge, FindingProposal, MergeResult

__all__ = [
    "evaluate_scope_and_safety",
    "ScopeResult",
    "BudgetGovernor",
    "sanitize_web_content",
    "validate_and_merge",
    "FindingProposal",
    "MergeResult",
]
