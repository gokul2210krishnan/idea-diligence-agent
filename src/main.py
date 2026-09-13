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


def main():
    """Main entry point for the Idea Diligence Agent."""

    # Check if an idea was passed as a command-line argument
    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:])
    else:
        # Interactive mode — ask the user for an idea
        print("\n" + "=" * 60)
        print("  IDEA DILIGENCE AGENT")
        print("  Evidence-backed GO / MODIFY / KILL decisions")
        print("=" * 60)
        print("\nDescribe your product idea below.")
        print("Be as specific as possible — include what it does,")
        print("who it's for, and how it would work.\n")

        idea = input("Your idea: ").strip()

        if not idea:
            print("\nNo idea provided. Exiting.")
            sys.exit(1)

    # Run the investigation
    verdict = run_diligence(idea)

    # Print the final verdict
    print("\n" + "=" * 60)
    print("  FINAL VERDICT")
    print("=" * 60)
    print(verdict)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
