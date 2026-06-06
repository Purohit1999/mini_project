"""Worker agents for flight search, hotel search, and activity planning."""

from __future__ import annotations

from typing import Any, Dict, List

from tools.travel_tools import search_activities, search_flights, search_hotels
from utils import LLMClient


class FlightWorker:
    """Worker that searches and explains flight options."""

    def __init__(self, llm: LLMClient, flights: List[Dict[str, Any]]):
        """Create a flight worker.

        Args:
            llm: LLM client wrapper.
            flights: Local flight data.
        """
        self.llm = llm
        self.flights = flights

    def run(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights and return a worker report.

        Args:
            requirements: Parsed travel requirements.

        Returns:
            Worker output containing ReAct trace, options, and recommendation.
        """
        options = search_flights(requirements, self.flights)
        if not options:
            return {
                "worker": "flight_search",
                "react_trace": [
                    "Thought: Need route-matching flights.",
                    "Action: search_flights",
                    "Observation: No matching local records found.",
                    "Decision: Ask the manager to clarify origin/destination or expand data.",
                ],
                "options": [],
                "recommendation": None,
                "rationale": "No matching flights were available in the local dataset.",
            }

        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are a flight-search worker in a travel-planning agent team. "
                "Return JSON with keys: worker, react_trace, options, recommendation, rationale. "
                "Be concise and choose one best option. Do not invent flights."
            )
            return self.llm.complete_json(
                system_prompt,
                {"requirements": requirements, "flight_options": options},
                purpose="flight worker ranking",
            )

        best = options[0]
        return {
            "worker": "flight_search",
            "react_trace": [
                "Thought: Need flights that match route and hard constraints.",
                "Action: search_flights(origin, destination, avoid_red_eye)",
                f"Observation: Found {len(options)} candidate option(s).",
                f"Decision: Recommend {best['flight_id']} because it best balances constraints and cost.",
            ],
            "options": options,
            "recommendation": best,
            "rationale": best.get("notes", "Best-ranked option from local flight search."),
        }


class HotelWorker:
    """Worker that searches and explains hotel options."""

    def __init__(self, llm: LLMClient, hotels: List[Dict[str, Any]]):
        """Create a hotel worker.

        Args:
            llm: LLM client wrapper.
            hotels: Local hotel data.
        """
        self.llm = llm
        self.hotels = hotels

    def run(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Search hotels and return a worker report.

        Args:
            requirements: Parsed travel requirements.

        Returns:
            Worker output containing ReAct trace, options, and recommendation.
        """
        options = search_hotels(requirements, self.hotels)
        if not options:
            return {
                "worker": "hotel_search",
                "react_trace": [
                    "Thought: Need destination-matching hotels.",
                    "Action: search_hotels",
                    "Observation: No matching local records found.",
                    "Decision: Ask the manager to clarify destination or expand data.",
                ],
                "options": [],
                "recommendation": None,
                "rationale": "No matching hotels were available in the local dataset.",
            }

        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are a hotel-search worker in a travel-planning agent team. "
                "Return JSON with keys: worker, react_trace, options, recommendation, rationale. "
                "Choose a hotel that respects budget and preferences. Do not invent hotels."
            )
            return self.llm.complete_json(
                system_prompt,
                {"requirements": requirements, "hotel_options": options},
                purpose="hotel worker ranking",
            )

        budget = int(requirements.get("hotel_budget_inr") or 0)
        best = options[0]
        budget_phrase = "within budget" if budget and best["total_price_inr"] <= budget else "best trade-off available"
        return {
            "worker": "hotel_search",
            "react_trace": [
                "Thought: Need hotel options matching destination, budget, and preferences.",
                "Action: search_hotels(destination, hotel_budget, preferences)",
                f"Observation: Found {len(options)} candidate option(s).",
                f"Decision: Recommend {best['name']} as the {budget_phrase}.",
            ],
            "options": options,
            "recommendation": best,
            "rationale": best.get("notes", "Best-ranked option from local hotel search."),
        }


class ActivityWorker:
    """Worker that searches and groups activities for the itinerary."""

    def __init__(self, llm: LLMClient, activities: List[Dict[str, Any]]):
        """Create an activity worker.

        Args:
            llm: LLM client wrapper.
            activities: Local activity data.
        """
        self.llm = llm
        self.activities = activities

    def run(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Search activities and return a worker report.

        Args:
            requirements: Parsed travel requirements.

        Returns:
            Worker output containing ReAct trace, options, and recommendation.
        """
        options = search_activities(requirements, self.activities)
        if not options:
            return {
                "worker": "activity_planner",
                "react_trace": [
                    "Thought: Need destination-matching activities.",
                    "Action: search_activities",
                    "Observation: No matching local records found.",
                    "Decision: Ask the manager to clarify destination or expand data.",
                ],
                "options": [],
                "recommendation": [],
                "rationale": "No matching activities were available in the local dataset.",
            }

        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are an activity-planning worker in a travel-planning agent team. "
                "Return JSON with keys: worker, react_trace, options, recommendation, rationale. "
                "Recommend a balanced shortlist only from provided activities."
            )
            return self.llm.complete_json(
                system_prompt,
                {"requirements": requirements, "activity_options": options},
                purpose="activity worker shortlisting",
            )

        selected = options[: min(len(options), 5)]
        return {
            "worker": "activity_planner",
            "react_trace": [
                "Thought: Need activities that match trip preferences and fit across days.",
                "Action: search_activities(destination, preferences)",
                f"Observation: Found {len(options)} candidate activity option(s).",
                "Decision: Shortlist the strongest matches and leave room for pacing.",
            ],
            "options": options,
            "recommendation": selected,
            "rationale": "Selected activities maximise overlap with stated preferences while keeping variety.",
        }
