"""
Safety Gate — Pre-flight validation for user-submitted ideas.

This is the FIRST defense boundary. Before any agent runs, the idea is
screened for:
  1. Deterministic checks (length, encoding, prompt-injection patterns)
  2. LLM-based semantic check (is this actually a product/business idea?)

If the idea fails either check, the pipeline rejects it immediately
without consuming research budget.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from strands import Agent
from src.model_provider import ModelRole, create_model
from src.prompts import SAFETY_GATE_PROMPT


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class ScopeResult(BaseModel):
    """The output of the safety gate evaluation."""

    is_valid: bool = Field(description="Whether the idea passed all checks")
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Why the idea was rejected (None if valid)",
    )
    sanitized_idea: str = Field(
        default="",
        description="The cleaned idea text (empty if rejected)",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Non-blocking warnings (e.g., 'idea is vague')",
    )


# ---------------------------------------------------------------------------
# Known prompt-injection patterns (deterministic blocklist)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+(instructions?|rules?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"output\s+(your|the)\s+system", re.IGNORECASE),
    re.compile(r"repeat\s+(everything|all)\s+(above|before)", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[\s*INST\s*\]", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a\s+)?(jailbroken|unrestricted|unfiltered)", re.IGNORECASE),
]

# Reasonable limits
_MIN_IDEA_LENGTH = 10
_MAX_IDEA_LENGTH = 5000


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------

def _check_deterministic(raw_idea: str) -> tuple[bool, list[str], Optional[str]]:
    """Run fast, deterministic checks on the raw idea text.

    Returns:
        (passed, risk_flags, rejection_reason)
    """
    risk_flags: list[str] = []

    # --- Length checks ---
    if len(raw_idea.strip()) < _MIN_IDEA_LENGTH:
        return False, risk_flags, (
            f"Idea is too short ({len(raw_idea.strip())} chars). "
            f"Please provide at least {_MIN_IDEA_LENGTH} characters describing your product idea."
        )

    if len(raw_idea) > _MAX_IDEA_LENGTH:
        return False, risk_flags, (
            f"Idea is too long ({len(raw_idea)} chars, max {_MAX_IDEA_LENGTH}). "
            f"Please provide a concise description of your product idea."
        )

    # --- Encoding / invisible character checks ---
    # Flag non-ASCII control characters (except newlines, tabs)
    invisible_chars = [
        c for c in raw_idea
        if ord(c) < 32 and c not in ('\n', '\r', '\t')
    ]
    if invisible_chars:
        risk_flags.append(
            f"Input contains {len(invisible_chars)} invisible control character(s) — stripped."
        )

    # --- Prompt injection pattern scan ---
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(raw_idea)
        if match:
            return False, risk_flags, (
                f"Input appears to contain a prompt-injection attempt "
                f"(matched: '{match.group()}'). "
                f"Please provide a genuine product or business idea."
            )

    # --- Vagueness heuristic ---
    word_count = len(raw_idea.split())
    if word_count < 5:
        risk_flags.append(
            "Idea is very short — results may be less useful. "
            "Consider adding who the product is for and what problem it solves."
        )

    return True, risk_flags, None


# ---------------------------------------------------------------------------
# LLM-based semantic check
# ---------------------------------------------------------------------------

def _check_semantic(sanitized_idea: str) -> tuple[bool, Optional[str], list[str]]:
    """Use a fast LLM call to determine if the text is a valid product idea.

    Returns:
        (is_valid, rejection_reason, additional_risk_flags)
    """
    model = create_model(ModelRole.SAFETY_GATE)
    gate_agent = Agent(
        model=model,
        system_prompt=SAFETY_GATE_PROMPT,
        tools=[],  # No tools — pure classification
    )

    prompt = (
        f"Classify this input. Is it a genuine product, business, or startup idea "
        f"that can be investigated for market viability?\n\n"
        f"INPUT: {sanitized_idea}\n\n"
        f"Respond in EXACTLY this format:\n"
        f"VALID: yes or no\n"
        f"REASON: one sentence explaining your classification\n"
        f"FLAGS: comma-separated risk flags, or 'none'"
    )

    result = str(gate_agent(prompt))

    # Parse the structured response
    is_valid = True
    rejection_reason = None
    risk_flags: list[str] = []

    result_lower = result.lower()
    if "valid: no" in result_lower or "valid:no" in result_lower:
        is_valid = False
        # Extract reason
        for line in result.split("\n"):
            if line.strip().upper().startswith("REASON:"):
                rejection_reason = line.split(":", 1)[1].strip()
                break
        if not rejection_reason:
            rejection_reason = "Input does not appear to be a product or business idea."

    # Extract flags
    for line in result.split("\n"):
        if line.strip().upper().startswith("FLAGS:"):
            flags_text = line.split(":", 1)[1].strip()
            if flags_text.lower() != "none":
                risk_flags = [f.strip() for f in flags_text.split(",") if f.strip()]
            break

    return is_valid, rejection_reason, risk_flags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_scope_and_safety(raw_idea: str) -> ScopeResult:
    """Screen a user-submitted idea before the research pipeline runs.

    This is the single entry point for the safety gate. It runs:
    1. Deterministic checks (fast, no LLM cost)
    2. Semantic classification (one LLM call if deterministic checks pass)

    Args:
        raw_idea: The raw text submitted by the user.

    Returns:
        ScopeResult with is_valid, rejection_reason, sanitized_idea, risk_flags.
    """
    # --- Step 1: Deterministic checks ---
    passed, risk_flags, rejection_reason = _check_deterministic(raw_idea)

    if not passed:
        return ScopeResult(
            is_valid=False,
            rejection_reason=rejection_reason,
            sanitized_idea="",
            risk_flags=risk_flags,
        )

    # --- Sanitize the idea text ---
    # Strip invisible control characters but preserve newlines/tabs
    sanitized = "".join(
        c for c in raw_idea
        if ord(c) >= 32 or c in ('\n', '\r', '\t')
    ).strip()

    # --- Step 2: Semantic classification ---
    try:
        is_valid, sem_reason, sem_flags = _check_semantic(sanitized)
        risk_flags.extend(sem_flags)

        if not is_valid:
            return ScopeResult(
                is_valid=False,
                rejection_reason=sem_reason,
                sanitized_idea="",
                risk_flags=risk_flags,
            )
    except Exception as e:
        # If the semantic check fails (e.g., API error), log a warning
        # but allow the idea through — fail-open for availability
        risk_flags.append(
            f"Semantic safety check failed ({type(e).__name__}): proceeding with caution."
        )

    return ScopeResult(
        is_valid=True,
        rejection_reason=None,
        sanitized_idea=sanitized,
        risk_flags=risk_flags,
    )
