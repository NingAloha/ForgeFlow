from __future__ import annotations

import argparse
import sys

from agents.orchestrator import Orchestrator


def build_user_input(args: argparse.Namespace) -> str:
    if args.user_input:
        return " ".join(args.user_input).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the ForgeFlow orchestrator for a single input."
    )
    parser.add_argument(
        "user_input",
        nargs="*",
        help="User request to send into the orchestrator.",
    )
    args = parser.parse_args()

    orchestrator = Orchestrator()
    result = orchestrator.orchestrate(build_user_input(args))
    decision = result.decision

    print(f"Computed stage: {decision.computed_stage}")
    print(f"Final stage: {decision.final_stage}")
    print(f"Executed stage: {result.executed_stage or 'None'}")
    print(f"Summary: {result.summary}")
    if decision.evidence:
        print("Evidence:")
        for item in decision.evidence:
            print(f"- {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
