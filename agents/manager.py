"""Manager agent that orchestrates the travel-planning worker team."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from agents.critic import ItineraryCritic
from agents.workers import ActivityWorker, FlightWorker, HotelWorker
from tools.travel_tools import estimate_trip_budget, load_travel_data
from utils import LLMClient


class TravelPlannerManager:
    """Manager-worker travel planner with Reflexion refinement."""

    def __init__(self, llm: LLMClient, travel_data: Dict[str, List[Dict[str, Any]]] | None = None):
        """Create the manager and its workers.

        Args:
            llm: LLM client wrapper.
            travel_data: Optional preloaded travel data.
        """
        self.llm = llm
        self.travel_data = travel_data or load_travel_data()
        self.flight_worker = FlightWorker(llm, self.travel_data["flights"])
        self.hotel_worker = HotelWorker(llm, self.travel_data["hotels"])
        self.activity_worker = ActivityWorker(llm, self.travel_data["activities"])
        self.critic = ItineraryCritic(llm)

    def parse_request(self, user_request: str) -> Dict[str, Any]:
        """Extract structured requirements from a free-text travel request.

        Args:
            user_request: Natural-language trip request.

        Returns:
            Structured travel requirements used by workers.
        """
        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are the manager agent for a travel-planning team. "
                "Extract requirements from a user request. Return JSON with keys: "
                "origin, destination, duration_days, traveller_count, budget_level, "
                "hotel_budget_inr, avoid_red_eye, preferences, assumptions, missing_information. "
                "Use null for unknown values and do not invent precise budgets unless stated."
            )
            return self.llm.complete_json(
                system_prompt,
                {"user_request": user_request},
                purpose="manager requirement extraction",
            )

        return self._offline_parse_request(user_request)

    def _offline_parse_request(self, user_request: str) -> Dict[str, Any]:
        """Parse a request with simple classroom-safe heuristics.

        Args:
            user_request: Natural-language trip request.

        Returns:
            Structured requirements.
        """
        text = user_request.lower()
        known_cities = ["Mumbai", "Delhi", "Bengaluru", "Singapore", "Dubai"]
        origin = None
        destination = None

        from_match = re.search(r"from\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:\s+for|\s+with|\.|,|$)", user_request, re.IGNORECASE)
        if from_match:
            origin_raw = from_match.group(1).strip()
            destination_raw = from_match.group(2).strip()
            origin = next((city for city in known_cities if city.lower() in origin_raw.lower()), origin_raw.title())
            destination = next((city for city in known_cities if city.lower() in destination_raw.lower()), destination_raw.title())
        else:
            for city in known_cities:
                if city.lower() in text:
                    if city in ["Singapore", "Dubai"]:
                        destination = city
                    elif origin is None:
                        origin = city

        duration_match = re.search(r"(\d+)\s*-\s*day|(\d+)\s+day", text)
        duration_days = int(next(group for group in duration_match.groups() if group)) if duration_match else 4

        traveller_match = re.search(r"for\s+(\d+)\s+(people|person|travellers|travelers)", text)
        traveller_count = int(traveller_match.group(1)) if traveller_match else (2 if "two" in text else 1)

        budget_match = re.search(r"(?:hotel budget|hotel.*under|hotel.*below|under|below)\s*(?:₹|rs\.?|inr)?\s*([0-9,]+)", text)
        hotel_budget = int(budget_match.group(1).replace(",", "")) if budget_match else None

        preference_aliases = {
            "food": ["food", "foods", "hawker", "dining", "local food"],
            "culture": ["culture", "cultural", "heritage", "museum", "temple", "historic", "history"],
            "views": ["views", "city views", "skyline", "landmark", "photo"],
            "shopping": ["shopping", "shop"],
            "family": ["family", "kids", "children"],
            "nature": ["nature", "garden", "parks"],
            "local": ["local"],
            "metro": ["metro", "mrt", "public transport"],
        }
        preferences = []
        for canonical_tag, aliases in preference_aliases.items():
            if any(alias in text for alias in aliases):
                preferences.append(canonical_tag)

        return {
            "origin": origin or "Mumbai",
            "destination": destination or "Singapore",
            "duration_days": duration_days,
            "traveller_count": traveller_count,
            "budget_level": "mid-budget" if "mid-budget" in text else ("budget" if "budget" in text else "flexible"),
            "hotel_budget_inr": hotel_budget,
            "avoid_red_eye": "avoid red-eye" in text or "avoid redeye" in text or "no red-eye" in text,
            "preferences": list(dict.fromkeys(preferences or ["food", "culture", "views"])),
            "assumptions": [
                "Local sample data simulates travel APIs.",
                "Prices are teaching estimates, not live market quotes.",
                "The final plan prioritises constraints before nice-to-have preferences.",
            ],
            "missing_information": [],
        }

    def run_workers(self, requirements: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Run all specialist workers.

        Args:
            requirements: Structured travel requirements.

        Returns:
            Mapping of worker names to reports.
        """
        return {
            "flight": self.flight_worker.run(requirements),
            "hotel": self.hotel_worker.run(requirements),
            "activities": self.activity_worker.run(requirements),
        }

    def create_draft_itinerary(
        self,
        requirements: Dict[str, Any],
        worker_outputs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create the first itinerary draft from worker outputs.

        Args:
            requirements: Structured travel requirements.
            worker_outputs: Outputs from specialist workers.

        Returns:
            Draft itinerary.
        """
        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are the synthesis manager in a travel-planning team. "
                "Create a first-draft itinerary using only the worker outputs. "
                "Return JSON with keys: selected_flight, selected_hotel, daily_plan, budget, tradeoffs, assumptions. "
                "Keep the plan practical and day-wise."
            )
            return self.llm.complete_json(
                system_prompt,
                {"requirements": requirements, "worker_outputs": worker_outputs},
                purpose="initial itinerary synthesis",
            )

        flight = worker_outputs["flight"].get("recommendation")
        hotel = worker_outputs["hotel"].get("recommendation")
        activities = worker_outputs["activities"].get("recommendation") or []
        if not flight or not hotel:
            return {
                "status": "blocked",
                "reason": "Missing flight or hotel recommendation.",
                "worker_outputs": worker_outputs,
            }

        duration_days = int(requirements.get("duration_days") or 4)
        traveller_count = int(requirements.get("traveller_count") or 1)
        # Keep the itinerary grounded and non-repetitive: every listed activity should
        # come from the worker recommendation and appear at most once in the day plan.
        selected_activities = activities[: min(len(activities), max(duration_days + 1, 3))]
        activity_queue = list(selected_activities)

        daily_plan = []
        planned_activities: List[Dict[str, Any]] = []
        for day in range(1, duration_days + 1):
            if day == 1:
                max_activities = 1
                focus = "Arrival and light local exploration"
            elif day == duration_days:
                max_activities = 1 if activity_queue else 0
                focus = "Slow morning and departure buffer"
            else:
                # Reserve one lighter option for the final day when possible.
                remaining_middle_days = max(duration_days - day, 0)
                reserve_for_departure = 1 if remaining_middle_days == 1 and len(activity_queue) > 2 else 0
                max_activities = min(2, max(len(activity_queue) - reserve_for_departure, 0))
                focus = "Preference-led sightseeing block"

            day_activities = []
            for _ in range(max_activities):
                if activity_queue:
                    activity = activity_queue.pop(0)
                    day_activities.append(activity)
                    planned_activities.append(activity)

            daily_plan.append({
                "day": day,
                "focus": focus,
                "activities": [
                    {
                        "name": activity.get("name"),
                        "area": activity.get("area"),
                        "best_time": activity.get("best_time"),
                        "duration_hours": activity.get("duration_hours"),
                        "estimated_cost_inr": activity.get("cost_inr"),
                        "why_it_fits": activity.get("notes"),
                    }
                    for activity in day_activities
                ],
            })

        budget = estimate_trip_budget(flight, hotel, planned_activities, traveller_count)

        return {
            "status": "draft",
            "selected_flight": flight,
            "selected_hotel": hotel,
            "daily_plan": daily_plan,
            "budget": budget,
            "tradeoffs": [
                "Uses local sample data rather than live inventory.",
                "Prioritises avoiding red-eye flights when requested.",
                "Keeps hotel selection close to the stated budget before premium views.",
            ],
            "assumptions": requirements.get("assumptions", []),
        }

    def refine_itinerary(
        self,
        requirements: Dict[str, Any],
        draft_itinerary: Dict[str, Any],
        critique: Dict[str, Any],
        worker_outputs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply critic feedback and produce a final itinerary.

        Args:
            requirements: Structured travel requirements.
            draft_itinerary: Initial itinerary.
            critique: Reflexion critique.
            worker_outputs: Worker outputs.

        Returns:
            Refined final itinerary.
        """
        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are the final manager agent. Refine the itinerary using critic feedback. "
                "Return JSON with keys: final_itinerary, changes_after_critique, final_notes. "
                "Keep recommendations grounded in the worker outputs."
            )
            return self.llm.complete_json(
                system_prompt,
                {
                    "requirements": requirements,
                    "draft_itinerary": draft_itinerary,
                    "critique": critique,
                    "worker_outputs": worker_outputs,
                },
                purpose="final itinerary refinement",
            )

        refined = dict(draft_itinerary)
        changes = []
        hotel_budget = int(requirements.get("hotel_budget_inr") or 0)
        hotel_options = worker_outputs["hotel"].get("options", [])
        current_hotel = refined.get("selected_hotel", {})

        if hotel_budget and int(current_hotel.get("total_price_inr", 0)) > hotel_budget:
            cheaper_options = [hotel for hotel in hotel_options if int(hotel.get("total_price_inr", 0)) <= hotel_budget]
            if cheaper_options:
                refined["selected_hotel"] = cheaper_options[0]
                changes.append(f"Changed hotel to {cheaper_options[0]['name']} to respect the stated hotel budget.")

        if not changes:
            changes.append("Kept core choices and made assumptions/trade-offs explicit.")

        refined["status"] = "final"
        refined["quality_score_after_reflexion"] = critique.get("quality_score")
        refined["critic_summary"] = critique.get("overall_assessment")
        return {
            "final_itinerary": refined,
            "changes_after_critique": changes,
            "final_notes": [
                "This is a teaching demo using sample data, not a booking engine.",
                "In production, each local tool can be replaced by a live API adapter.",
                "The same project can later be refactored with deeper agent frameworks.",
            ],
        }

    def run(self, user_request: str) -> Dict[str, Any]:
        """Run the complete manager-worker-reflexion pipeline.

        Args:
            user_request: Natural-language trip request.

        Returns:
            Full state trace for the run.
        """
        requirements = self.parse_request(user_request)
        worker_outputs = self.run_workers(requirements)
        draft_itinerary = self.create_draft_itinerary(requirements, worker_outputs)
        critique = self.critic.evaluate(requirements, draft_itinerary, worker_outputs)
        final_output = self.refine_itinerary(requirements, draft_itinerary, critique, worker_outputs)

        return {
            "user_request": user_request,
            "requirements": requirements,
            "worker_outputs": worker_outputs,
            "draft_itinerary": draft_itinerary,
            "critique": critique,
            "final_output": final_output,
        }
