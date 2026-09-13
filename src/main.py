"""
Idea Diligence Agent — Main Entry Point.

Run this file to investigate a product idea:

    python -m src.main "An app that helps small restaurants track food inventory"

Or run it without arguments for interactive mode.
"""

import sys
from dotenv import load_dotenv

load_dotenv()
from src.agents.orchestrator import run_diligence
from src.models import UnknownStatus


def main():
    """Main entry point for the Idea Diligence Agent."""

    # Check if an idea was passed as a command-line argument
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        # Interactive mode — ask the user for an idea
        print("\n" + "=" * 60)
        print("  IDEA DILIGENCE AGENT — Phase 2")
        print("  Evidence-backed GO / MODIFY / KILL decisions")
        print("  Governed by: Safety Gate • Budget Governor • Data Sanitizer")
        print("=" * 60)
        print("\nDescribe your product idea below.")
        print("Be as specific as possible — include what it does,")
        print("who it's for, and how it would work.\n")

        idea = input("Your idea: ").strip()

        if not idea:
            print("\nNo idea provided. Exiting.")
            sys.exit(1)

    # Run the governed investigation
    verdict_text, state, scope_result, budget_status = run_diligence(idea)

    # Print the final verdict
    print("\n" + "=" * 60)
    print("  FINAL VERDICT")
    print("=" * 60)
    print(verdict_text)

    # Print governance summary
    if budget_status:
        print("\n" + "-" * 60)
        print("  GOVERNANCE REPORT")
        print("-" * 60)
        print(f"  Safety Gate:    {'[PASSED]' if scope_result.is_valid else '[REJECTED]'}")
        if scope_result.risk_flags:
            for flag in scope_result.risk_flags:
                print(f"    [!] {flag}")
        print(f"  Iterations:     {budget_status.get('iterations', 'N/A')}")
        print(f"  Tool Calls:     {budget_status.get('tool_calls_total', 'N/A')}")
        if budget_status.get('tool_calls_by_agent'):
            for agent_name, count in budget_status['tool_calls_by_agent'].items():
                print(f"    > {agent_name}: {count}")
        print(f"  Time Elapsed:   {budget_status.get('elapsed_seconds', 0)}s")
        print(f"  Evidence Found: {len(state.evidence)}")
        open_unknowns = [u for u in state.unknowns if u.status != UnknownStatus.RESOLVED]
        print(f"  Open Unknowns:  {len(open_unknowns)}")
        if budget_status.get('exhaustion_reason'):
            print(f"  [!] Budget:     {budget_status['exhaustion_reason']}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
