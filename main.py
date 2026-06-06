"""Command-line runner for the multi-agent travel planner sprint."""

from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from agents.manager import TravelPlannerManager
from tools.travel_tools import load_travel_data
from utils import LLMClient, load_project_env, pretty_json, save_trip_plan, validate_trip_request


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


def run_pipeline(user_request: str, demo_mode: str | None = None) -> Dict[str, Any]:
    """Run the travel-planner pipeline.

    Args:
        user_request: Natural-language request.
        demo_mode: Optional override for DEMO_MODE.

    Returns:
        Full pipeline result.
    """
    settings = load_project_env()
    if demo_mode:
        os.environ["DEMO_MODE"] = demo_mode
        settings["demo_mode"] = demo_mode

    try:
        temperature = float(settings["temperature"])
    except ValueError:
        temperature = 0.2

    llm = LLMClient(
        demo_mode=settings["demo_mode"],
        model_name=settings["model_name"],
        temperature=temperature,
    )
    travel_data = load_travel_data()
    manager = TravelPlannerManager(llm=llm, travel_data=travel_data)
    return manager.run(user_request)


def main() -> None:
    """Run the command-line demo."""
    parser = build_parser()
    args = parser.parse_args()

    validation = validate_trip_request(args.request)
    if not validation["valid"]:
        print("Trip request validation failed:")
        for issue in validation["errors"]:
            print(f"- {issue}")
        raise SystemExit(1)

    result = run_pipeline(args.request, args.demo_mode)
    output_path = save_trip_plan(result)

    print("\n=== Final Travel Plan ===")
    print(pretty_json(result["final_output"]))
    print(f"\nSaved sample trip plan to: {output_path}")

    if args.show_trace:
        print("\n=== Full Manager-Worker Trace ===")
        print(pretty_json(result))


if __name__ == "__main__":
    main()
