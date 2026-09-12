"""
Custom tools for the Idea Diligence Agent.

These tools let the specialist agents perform real research:
- Search the web for competitors, pricing, and market data
- Read and extract information from web pages
- Store structured findings back into the DiligenceState

Tools are Python functions decorated with @tool from the Strands SDK.
The LLM decides when and how to call them.
"""

from __future__ import annotations

import json

from strands import tool
from strands_tools import http_request


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
    try:
        # Use DuckDuckGo HTML search (no API key needed)
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        result = http_request(
            url=search_url,
            method="GET",
        )
        # Return raw text — the LLM will parse and extract relevant info
        if isinstance(result, dict):
            return result.get("body", str(result))
        return str(result)
    except Exception as e:
        return f"Search failed: {str(e)}. Try rephrasing your query."


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
    try:
        result = http_request(
            url=url,
            method="GET",
        )
        if isinstance(result, dict):
            body = result.get("body", "")
            # Truncate very long pages to avoid overwhelming the LLM context
            if len(body) > 15000:
                body = body[:15000] + "\n\n[Content truncated — page was very long]"
            return body
        return str(result)[:15000]
    except Exception as e:
        return f"Failed to read {url}: {str(e)}"


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
    # This tool stores findings as structured JSON that the orchestrator
    # will parse back into Evidence objects for the DiligenceState.
    finding = {
        "category": category,
        "content": content,
        "evidence_type": evidence_type,
        "source": source,
        "confidence": confidence,
    }
    # Return the finding as JSON — the orchestrator will collect these
    # from the agent's tool use results
    return json.dumps(finding, indent=2)
