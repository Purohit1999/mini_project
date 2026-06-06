"""Command-line runner for the multi-agent travel planner sprint."""

from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from langgraph_flow import run_langgraph_pipeline
from utils import pretty_json, save_trip_plan, validate_trip_request


DEFAULT_REQUEST = (
    "Plan a 4-day trip from Mumbai to Singapore for two people. Keep it mid-budget, "
    "avoid red-eye flights, prefer food, city views, and cultural sites. "
    "Keep the total hotel budget under ₹45,000."
)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser.

    Returns:
        Configured argparse parser.
    """
    parser = argparse.ArgumentParser(description="Run the multi-agent travel planner demo.")
    parser.add_argument("--request", default=DEFAULT_REQUEST, help="Natural-language travel request.")
    parser.add_argument(
        "--demo-mode",
        choices=["offline", "live"],
        default=None,
        help="offline uses deterministic logic; live uses OpenAI calls.",
    )
    parser.add_argument("--show-trace", action="store_true", help="Print the full state trace.")
    return parser


def resolve_request_text(user_request: str) -> str:
    """Return the provided request, or fall back to the default demo prompt."""
    candidate = (user_request or "").strip()
    return candidate or DEFAULT_REQUEST


def run_pipeline(user_request: str, demo_mode: str | None = None) -> Dict[str, Any]:
    """Run the travel-planner pipeline via the LangGraph orchestration layer."""
    return run_langgraph_pipeline(user_request, demo_mode=demo_mode)


def main() -> None:
    """Run the command-line demo."""
    parser = build_parser()
    args = parser.parse_args()

    request_text = resolve_request_text(args.request)
    validation = validate_trip_request(request_text)
    if not validation["valid"]:
        print("Trip request validation failed:")
        for issue in validation["errors"]:
            print(f"- {issue}")
        raise SystemExit(1)

    result = run_pipeline(request_text, args.demo_mode)
    output_path = save_trip_plan(result)

    print("\n=== Final Travel Plan ===")
    print(pretty_json(result["final_output"]))
    print(f"\nSaved sample trip plan to: {output_path}")

    if args.show_trace:
        print("\n=== Full Manager-Worker Trace ===")
        print(pretty_json(result))


if __name__ == "__main__":
    main()
