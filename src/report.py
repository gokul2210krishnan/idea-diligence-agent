"""
Professional diligence report formatter.

Renders a DiligenceState + VerdictReport as markdown, JSON, or a
rich terminal panel used by the CLI demo.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Optional

from src.models import DiligenceState, UnknownStatus, Verdict, VerdictReport


_VERDICT_LABELS = {
    Verdict.GO: "Proceed to a focused MVP",
    Verdict.MODIFY: "Revise the idea before building",
    Verdict.KILL: "Do not invest further in this formulation",
}


def _verdict(state: DiligenceState) -> Optional[VerdictReport]:
    return state.verdict


def render_markdown_report(
    state: DiligenceState,
    scope_result: Any = None,
    budget_status: Optional[dict] = None,
) -> str:
    """Return a professional markdown diligence dossier."""
    verdict = _verdict(state)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "# Idea Diligence Report",
        "",
        f"**Idea:** {state.idea}",
        f"**Generated:** {generated}",
        "",
    ]

    if verdict:
        lines.extend([
            "## Verdict",
            "",
            f"**{verdict.decision.value}** — {_VERDICT_LABELS[verdict.decision]}",
            f"- Confidence: **{verdict.confidence:.0%}**",
            f"- Method: {verdict.method}",
            "",
            verdict.summary,
            "",
            "### Dimension scores",
            "",
            f"| Problem | Competition | Economics |",
            f"| ---: | ---: | ---: |",
            (
                f"| {verdict.dimension_scores.problem:.2f} "
                f"| {verdict.dimension_scores.competition:.2f} "
                f"| {verdict.dimension_scores.economics:.2f} |"
            ),
            "",
            "### Evidence mix",
            "",
            (
                f"- FACT: {verdict.evidence_breakdown.facts} · "
                f"INFERENCE: {verdict.evidence_breakdown.inferences} · "
                f"ASSUMPTION: {verdict.evidence_breakdown.assumptions} · "
                f"UNKNOWN: {verdict.evidence_breakdown.unknowns}"
            ),
            "",
        ])

        if verdict.key_evidence:
            lines.extend(["### Key evidence", ""])
            lines.extend(f"- {item}" for item in verdict.key_evidence)
            lines.append("")

        if verdict.modifications:
            lines.extend(["### Required modifications", ""])
            lines.extend(f"- {item}" for item in verdict.modifications)
            lines.append("")

        if verdict.assumptions:
            lines.extend(["### Assumptions the verdict depends on", ""])
            lines.extend(f"- {item}" for item in verdict.assumptions)
            lines.append("")

        if verdict.remaining_unknowns:
            lines.extend(["### Remaining unknowns", ""])
            lines.extend(f"- {item}" for item in verdict.remaining_unknowns)
            lines.append("")

        if verdict.risks:
            lines.extend(["### Risks", ""])
            lines.extend(f"- {item}" for item in verdict.risks)
            lines.append("")

        if verdict.next_steps:
            lines.extend(["### Recommended next steps", ""])
            lines.extend(f"- {item}" for item in verdict.next_steps)
            lines.append("")
    else:
        lines.extend(["## Verdict", "", "_No verdict has been rendered yet._", ""])

    if state.problem.problem_statement:
        lines.extend(["## Problem", "", state.problem.problem_statement, ""])
        if state.problem.severity:
            lines.append(f"**Severity:** {state.problem.severity}")
            lines.append("")

    if state.customers:
        lines.extend(["## Customer segments", ""])
        for customer in state.customers:
            pains = "; ".join(customer.pain_points) if customer.pain_points else "n/a"
            lines.append(f"- **{customer.name}** — {pains}")
        lines.append("")

    if state.competitors:
        lines.extend(["## Competitive landscape", ""])
        for competitor in state.competitors:
            pricing = f" · {competitor.pricing}" if competitor.pricing else ""
            lines.append(f"- **{competitor.name}**{pricing} — {competitor.description}")
        lines.append("")

    if state.economics.market_size or state.economics.revenue_potential:
        lines.extend(["## Economics", ""])
        if state.economics.market_size:
            lines.append(f"- Market size: {state.economics.market_size}")
        if state.economics.revenue_potential:
            lines.append(f"- Revenue / pricing: {state.economics.revenue_potential}")
        if state.economics.unit_economics:
            lines.append(f"- Unit economics: {state.economics.unit_economics}")
        lines.append("")

    if state.evidence:
        lines.extend(["## Evidence ledger", ""])
        for item in state.evidence:
            source = f" · {item.source}" if item.source else ""
            lines.append(
                f"- `{item.evidence_type.value}` ({item.confidence:.0%}, {item.category}) "
                f"{item.content}{source}"
            )
        lines.append("")

    lines.extend(["## Governance", ""])
    if scope_result is not None:
        passed = getattr(scope_result, "is_valid", True)
        lines.append(f"- Safety gate: {'PASSED' if passed else 'REJECTED'}")
        flags = getattr(scope_result, "risk_flags", []) or []
        for flag in flags:
            lines.append(f"  - {flag}")
    if budget_status:
        lines.append(f"- Iterations: {budget_status.get('iterations', 'n/a')}")
        lines.append(f"- Tool calls: {budget_status.get('tool_calls_total', 'n/a')}")
        lines.append(f"- Elapsed: {budget_status.get('elapsed_seconds', 0)}s")
        if budget_status.get("exhaustion_reason"):
            lines.append(f"- Budget stop: {budget_status['exhaustion_reason']}")
    open_unknowns = [u for u in state.unknowns if u.status != UnknownStatus.RESOLVED]
    lines.append(f"- Open unknowns: {len(open_unknowns)}")
    lines.append(f"- Research actions: {len(state.research_history)}")
    lines.append("")
    lines.append("---")
    lines.append("Generated by the Idea Diligence Agent. Evidence is classified; FACTs require sources.")
    return "\n".join(lines)


def render_json_report(
    state: DiligenceState,
    scope_result: Any = None,
    budget_status: Optional[dict] = None,
) -> str:
    """Serialize the investigation as pretty JSON."""
    payload = {
        "idea": state.idea,
        "verdict": state.verdict.model_dump(mode="json") if state.verdict else None,
        "problem": state.problem.model_dump(mode="json"),
        "customers": [c.model_dump(mode="json") for c in state.customers],
        "competitors": [c.model_dump(mode="json") for c in state.competitors],
        "economics": state.economics.model_dump(mode="json"),
        "evidence": [e.model_dump(mode="json") for e in state.evidence],
        "unknowns": [u.model_dump(mode="json") for u in state.unknowns],
        "research_history": [a.model_dump(mode="json") for a in state.research_history],
        "scope": scope_result.model_dump(mode="json") if hasattr(scope_result, "model_dump") else scope_result,
        "budget": budget_status or {},
    }
    return json.dumps(payload, indent=2, default=str)


def render_console_report(
    state: DiligenceState,
    scope_result: Any = None,
    budget_status: Optional[dict] = None,
) -> str:
    """Render a colorized terminal report. Falls back to markdown without Rich."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        return render_markdown_report(state, scope_result, budget_status)

    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "─│".encode(encoding)
        unicode_ok = True
    except (LookupError, UnicodeEncodeError):
        unicode_ok = False

    if not unicode_ok:
        return render_markdown_report(state, scope_result, budget_status)

    import io

    buffer = io.StringIO()
    console = Console(
        file=buffer,
        force_terminal=True,
        width=100,
        color_system="standard",
        legacy_windows=True,
    )
    verdict = _verdict(state)

    colors = {Verdict.GO: "green", Verdict.MODIFY: "yellow", Verdict.KILL: "red"}
    if verdict:
        color = colors[verdict.decision]
        header = Text(f"  {verdict.decision.value}  ", style=f"bold white on {color}")
        header.append(f"  {verdict.confidence:.0%} confidence  ·  {verdict.method}", style="dim")
        console.print(Panel(header, title="Idea Diligence Verdict", subtitle=state.idea[:80]))
        console.print()
        console.print(verdict.summary)
        console.print()

        table = Table(title="Dimension scores", show_header=True, header_style="bold")
        table.add_column("Problem")
        table.add_column("Competition")
        table.add_column("Economics")
        table.add_row(
            f"{verdict.dimension_scores.problem:.2f}",
            f"{verdict.dimension_scores.competition:.2f}",
            f"{verdict.dimension_scores.economics:.2f}",
        )
        console.print(table)

        if verdict.key_evidence:
            console.print("\n[bold]Key evidence[/bold]")
            for item in verdict.key_evidence:
                console.print(f"  • {item}")
        if verdict.modifications:
            console.print("\n[bold yellow]Required modifications[/bold yellow]")
            for item in verdict.modifications:
                console.print(f"  • {item}")
        if verdict.next_steps:
            console.print("\n[bold]Next steps[/bold]")
            for item in verdict.next_steps:
                console.print(f"  • {item}")
    else:
        console.print(Panel("No verdict rendered", title="Idea Diligence"))

    if budget_status:
        console.print(
            f"\n[dim]Governance — safety: "
            f"{'PASSED' if getattr(scope_result, 'is_valid', True) else 'REJECTED'} · "
            f"iterations {budget_status.get('iterations', 'n/a')} · "
            f"tools {budget_status.get('tool_calls_total', 'n/a')} · "
            f"{budget_status.get('elapsed_seconds', 0)}s[/dim]"
        )

    return buffer.getvalue()
