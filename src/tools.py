"""
Custom tools for the Idea Diligence Agent.

Module-level tools remain for ad-hoc agent construction. The governed loop
builds *session-bound* tools via ``create_research_tools`` so budget checks
and state merges happen in Python at call time — not after the LLM returns.
"""

from __future__ import annotations

import json

from strands import tool
from strands_tools import http_request

from src.governance.budget_governor import BudgetGovernor
from src.governance.data_sanitizer import sanitize_web_content
from src.governance.state_updater import FindingProposal, validate_and_merge
from src.models import DiligenceState


def _raw_http_body(url: str) -> str:
    result = http_request(url=url, method="GET")
    if isinstance(result, dict):
        return str(result.get("body", result))
    return str(result)


def _search_web_impl(query: str) -> str:
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        raw = _raw_http_body(search_url)
        return sanitize_web_content(raw, source_url=search_url)
    except Exception as e:
        return f"Search failed: {str(e)}. Try rephrasing your query."


def _read_webpage_impl(url: str) -> str:
    try:
        raw = _raw_http_body(url)
        return sanitize_web_content(raw, source_url=url)
    except Exception as e:
        return f"Failed to read {url}: {str(e)}"


@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic.

    Use this tool to find competitors, pricing data, market reports,
    customer reviews, and any other information relevant to evaluating
    a product idea.

    Args:
        query: The search query (e.g., "restaurant inventory management software pricing")

    Returns:
        Search results as text with titles, snippets, and URLs.
    """
    return _search_web_impl(query)


@tool
def read_webpage(url: str) -> str:
    """Read and extract text content from a webpage.

    Use this tool to read competitor websites, pricing pages,
    blog posts, review sites, or market reports.

    Args:
        url: The full URL to read (e.g., "https://example.com/pricing")

    Returns:
        The text content of the page (HTML stripped).
    """
    return _read_webpage_impl(url)


@tool
def save_finding(
    category: str,
    content: str,
    evidence_type: str,
    source: str = "",
    confidence: float = 0.5,
) -> str:
    """Save a research finding to be included in the final report.

    Call this tool every time you discover something important during research.
    This creates a structured record that the orchestrator uses to make decisions.

    Args:
        category: What area this finding belongs to.
                  One of: "problem", "customer", "competitor", "pricing",
                  "market_size", "business_model", "risk", "opportunity"
        content: A clear, one-sentence description of what you found.
                 Example: "Competitor X charges $49/month for their base plan"
        evidence_type: How reliable this finding is.
                      One of: "FACT" (verified with source),
                              "ASSUMPTION" (believed but not verified),
                              "INFERENCE" (conclusion from facts),
                              "UNKNOWN" (important gap in knowledge)
        source: Where you found this (URL or description). Required for FACTs.
        confidence: How confident you are in this finding (0.0 to 1.0).
                   Use 0.9+ for verified facts, 0.5 for inferences, 0.3 for guesses.

    Returns:
        Confirmation that the finding was saved.
    """
    finding = {
        "category": category,
        "content": content,
        "evidence_type": evidence_type,
        "source": source,
        "confidence": confidence,
    }
    return json.dumps(finding, indent=2)


def create_research_tools(
    *,
    state: DiligenceState,
    governor: BudgetGovernor,
    agent_name: str,
):
    """Build search/read/save tools bound to one investigation and one specialist."""

    @tool
    def search_web(query: str) -> str:
        """Search the web for competitors, pricing, market data, or demand signals."""
        allowed, reason = governor.try_consume_tool(agent_name)
        if not allowed:
            return (
                f"[BUDGET STOP] {reason} "
                "Do not call more tools. Summarize from evidence already gathered."
            )
        return _search_web_impl(query)

    @tool
    def read_webpage(url: str) -> str:
        """Read a webpage and return sanitized text."""
        allowed, reason = governor.try_consume_tool(agent_name)
        if not allowed:
            return (
                f"[BUDGET STOP] {reason} "
                "Do not call more tools. Summarize from evidence already gathered."
            )
        return _read_webpage_impl(url)

    @tool
    def save_finding(
        category: str,
        content: str,
        evidence_type: str,
        source: str = "",
        confidence: float = 0.5,
    ) -> str:
        """Propose a finding. Python validates and merges it into DiligenceState."""
        proposal = FindingProposal(
            category=category,
            content=content,
            evidence_type=evidence_type,
            source=source or "",
            confidence=confidence,
            proposed_by=agent_name,
        )
        result = validate_and_merge(proposal, state)
        payload = {
            "accepted": result.accepted,
            "reason": result.reason,
            "warnings": result.warnings,
        }
        return json.dumps(payload)

    return [search_web, read_webpage, save_finding]
