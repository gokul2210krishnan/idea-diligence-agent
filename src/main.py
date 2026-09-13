"""
Idea Diligence Agent — Main Entry Point.

    python -m src.main "An app that helps small restaurants track food inventory"
    python -m src.main --demo
    python -m src.main --json --output report.json "Your idea"
    python -m src.main --web
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.demo_data import load_sample_investigation
from src.models import UnknownStatus
from src.report import render_console_report, render_json_report, render_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Idea Diligence Agent — evidence-backed GO / MODIFY / KILL.",
    )
    parser.add_argument(
        "idea",
        nargs="*",
        help="Product idea to investigate. Omit for interactive prompt.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the local demo web UI.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Render the canned restaurant-inventory investigation (no LLM calls).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the investigation as JSON instead of a formatted report.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write the report to this file (markdown or JSON).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for --web (default: 8000).",
    )
    return parser


def _prompt_for_idea() -> str:
    print("\n" + "=" * 60)
    print("  IDEA DILIGENCE AGENT — Phase 3 / 4")
    print("  Evidence-backed GO / MODIFY / KILL decisions")
    print("  Safety Gate · Budget Governor · Verdict Engine")
    print("=" * 60)
    print("\nDescribe your product idea below.")
    print("Be as specific as possible — include what it does,")
    print("who it's for, and how it would work.\n")
    idea = input("Your idea: ").strip()
    if not idea:
        print("\nNo idea provided. Exiting.")
        sys.exit(1)
    return idea


def _print_governance(state, scope_result, budget_status) -> None:
    if not budget_status:
        return
    print("\n" + "-" * 60)
    print("  GOVERNANCE REPORT")
    print("-" * 60)
    print(f"  Safety Gate:    {'[PASSED]' if scope_result.is_valid else '[REJECTED]'}")
    if scope_result.risk_flags:
        for flag in scope_result.risk_flags:
            print(f"    [!] {flag}")
    print(f"  Iterations:     {budget_status.get('iterations', 'N/A')}")
    print(f"  Tool Calls:     {budget_status.get('tool_calls_total', 'N/A')}")
    if budget_status.get("tool_calls_by_agent"):
        for agent_name, count in budget_status["tool_calls_by_agent"].items():
            print(f"    > {agent_name}: {count}")
    print(f"  Time Elapsed:   {budget_status.get('elapsed_seconds', 0)}s")
    print(f"  Evidence Found: {len(state.evidence)}")
    open_unknowns = [u for u in state.unknowns if u.status != UnknownStatus.RESOLVED]
    print(f"  Open Unknowns:  {len(open_unknowns)}")
    if state.verdict:
        print(f"  Verdict:        {state.verdict.decision.value} ({state.verdict.confidence:.0%})")
    if budget_status.get("exhaustion_reason"):
        print(f"  [!] Budget:     {budget_status['exhaustion_reason']}")
    print("=" * 60 + "\n")


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", "utf-8")
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def run_cli(args: argparse.Namespace) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if args.demo:
        state, scope_result, budget_status = load_sample_investigation()
    else:
        idea = " ".join(args.idea).strip() or _prompt_for_idea()
        from src.agents.orchestrator import run_diligence

        _formatted, state, scope_result, budget_status = run_diligence(idea)

    if args.output:
        if args.json or args.output.suffix.lower() == ".json":
            args.output.write_text(
                render_json_report(state, scope_result, budget_status),
                encoding="utf-8",
            )
        else:
            args.output.write_text(
                render_markdown_report(state, scope_result, budget_status),
                encoding="utf-8",
            )

    if args.json:
        _safe_print(render_json_report(state, scope_result, budget_status))
    else:
        _safe_print("\n" + "=" * 60)
        _safe_print("  FINAL VERDICT")
        _safe_print("=" * 60)
        _safe_print(render_console_report(state, scope_result, budget_status))
        _print_governance(state, scope_result, budget_status)

    if args.output:
        _safe_print(f"Report written to {args.output}")
    return 0


def run_web(port: int) -> int:
    import uvicorn
    from src.web.app import app

    print(f"\nStarting Idea Diligence UI on http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.web:
        return run_web(args.port)
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
