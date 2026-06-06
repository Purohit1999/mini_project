"""Utility helpers for the multi-agent travel planner sprint.

The package defaults to offline mode so the architecture can be demonstrated
without API credentials. Set DEMO_MODE=live and provide OPENAI_API_KEY for
live LLM calls.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled with a clear runtime message
    OpenAI = None  # type: ignore

try:
    from langsmith.wrappers import wrap_openai
except ImportError:  # pragma: no cover - LangSmith is optional at runtime
    wrap_openai = None  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parent


def load_project_env() -> Dict[str, str]:
    """Load .env values and return the main runtime settings.

    Returns:
        Dictionary containing demo mode, model name, temperature, and tracing flags.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    return {
        "demo_mode": os.getenv("DEMO_MODE", "offline").strip().lower(),
        "model_name": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        "temperature": os.getenv("OPENAI_TEMPERATURE", "0.2").strip(),
        "langsmith_tracing": os.getenv("LANGSMITH_TRACING", "false").strip().lower(),
    }


def load_json_file(path: Path) -> Any:
    """Read a JSON file from disk.

    Args:
        path: Absolute or relative path to a JSON file.

    Returns:
        Parsed JSON content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains invalid JSON.
    """
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path.name}: {exc}") from exc


def parse_json_safely(raw_text: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Parse a JSON object from model output with a friendly fallback.

    Args:
        raw_text: Text expected to contain a JSON object.
        fallback: Value to return if parsing fails.

    Returns:
        Parsed dictionary, or fallback when provided.
    """
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return fallback or {"error": "Model returned malformed JSON", "raw_text": raw_text}


def pretty_json(data: Any) -> str:
    """Format Python data as readable JSON text.

    Args:
        data: Any JSON-serialisable value.

    Returns:
        Pretty JSON string.
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


def validate_trip_request(user_request: str) -> Dict[str, Any]:
    """Validate that a travel request matches the Singapore demo contract.

    The project uses sample data and deterministic logic for teaching. This helper
    makes the contract explicit and easy to test.
    """
    text = (user_request or "").lower()

    duration_match = re.search(r"(\d+)\s*-?\s*days?", text)
    duration_days = int(duration_match.group(1)) if duration_match else None

    traveller_match = re.search(r"for\s+(\d+)\s+(people|person|travellers|travelers)", text)
    traveller_count = int(traveller_match.group(1)) if traveller_match else None
    if traveller_count is None:
        word_to_number = {"one": 1, "two": 2, "three": 3, "four": 4}
        for word, value in word_to_number.items():
            if f"for {word} people" in text or f"for {word} person" in text or f"for {word} travellers" in text:
                traveller_count = value
                break

    hotel_budget_match = re.search(r"(?:hotel budget|under|below)\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*)", text)
    hotel_budget_inr = int(hotel_budget_match.group(1).replace(",", "")) if hotel_budget_match else None

    preferences = []
    preference_aliases = {
        "food": ["food", "hawker", "dining", "local food"],
        "views": ["view", "views", "city view", "city views", "skyline", "landmark", "scenery"],
        "culture": ["culture", "cultural", "cultural sites", "heritage", "museum", "history"],
    }
    for canonical_tag, aliases in preference_aliases.items():
        if any(alias in text for alias in aliases):
            preferences.append(canonical_tag)

    errors = []
    if "mumbai" not in text:
        errors.append("Origin must be Mumbai.")
    if "singapore" not in text:
        errors.append("Destination must be Singapore.")
    if duration_days != 4:
        errors.append("Trip duration must be 4 days.")
    if traveller_count != 2:
        errors.append("Trip must be for 2 people.")
    if hotel_budget_inr is None or hotel_budget_inr > 45000:
        errors.append("Hotel budget must be under or equal to ₹45,000 total.")
    if "avoid red-eye" not in text and "avoid redeye" not in text and "no red-eye" not in text:
        errors.append("The trip must explicitly avoid red-eye flights.")
    if not set(["food", "views", "culture"]).issubset(set(preferences)):
        errors.append("The request must prefer food, city views, and cultural sites.")

    return {
        "valid": not errors,
        "requirements": {
            "origin": "Mumbai" if "mumbai" in text else "Unknown",
            "destination": "Singapore" if "singapore" in text else "Unknown",
            "duration_days": duration_days or 0,
            "traveller_count": traveller_count or 0,
            "hotel_budget_inr": hotel_budget_inr or 0,
            "avoid_red_eye": "avoid red-eye" in text or "avoid redeye" in text or "no red-eye" in text,
            "preferences": list(dict.fromkeys(preferences)),
        },
        "errors": errors,
    }


def render_trip_plan_markdown(plan: Dict[str, Any]) -> str:
    """Render the final itinerary as a readable Markdown file for outputs/."""
    final_output = plan.get("final_output", plan) or {}
    final_itinerary = final_output.get("final_itinerary", final_output) or {}
    budget = final_itinerary.get("budget", {}) or {}
    selected_flight = final_itinerary.get("selected_flight", {}) or {}
    selected_hotel = final_itinerary.get("selected_hotel", {}) or {}
    daily_plan = final_itinerary.get("daily_plan", []) or []

    lines = [
        "# Singapore Trip Plan (Sample Data)",
        "",
        "This plan is generated from local sample data and is intended for teaching/demo use only.",
        "",
        "## Constraints checked",
        f"- Origin: {selected_flight.get('origin', 'Mumbai')}",
        f"- Destination: {selected_flight.get('destination', 'Singapore')}",
        f"- Hotel budget cap: ₹45,000 total",
        f"- Red-eye flights avoided: {'Yes' if selected_flight.get('tags') and 'red-eye' not in [str(tag).lower() for tag in selected_flight.get('tags')] else 'No'}",
        "",
        "## Flight recommendation notes",
        f"- Recommended flight: {selected_flight.get('airline', 'N/A')} {selected_flight.get('flight_id', '')}",
        f"- Depart/arrive: {selected_flight.get('depart_time', 'N/A')} → {selected_flight.get('arrive_time', 'N/A')}",
        f"- Notes: {selected_flight.get('notes', 'No extra notes supplied.')}",
        "",
        "## Hotel budget guidance",
        f"- Recommended hotel: {selected_hotel.get('name', 'N/A')} in {selected_hotel.get('area', 'N/A')}",
        f"- Nights: {selected_hotel.get('nights', 'N/A')}",
        f"- Total hotel cost: ₹{selected_hotel.get('total_price_inr', 0):,}",
        f"- Rate per night: ₹{selected_hotel.get('price_per_night_inr', 0):,}",
        "",
        "## Day-by-day itinerary",
    ]

    for day in daily_plan:
        lines.append(f"### Day {day.get('day', '?')} — {day.get('focus', 'Plan block')}")
        activities = day.get("activities", []) or []
        if not activities:
            lines.append("- Buffer / departure day with flexible free time.")
        else:
            for activity in activities:
                lines.append(f"- {activity.get('name', 'Activity')} ({activity.get('area', 'Area')})")
                lines.append(f"  - Best time: {activity.get('best_time', 'TBD')}")
                lines.append(f"  - Estimated cost: ₹{activity.get('estimated_cost_inr', 0):,}")
                lines.append(f"  - Why it fits: {activity.get('why_it_fits', 'Matches the stated preferences.')}")
        lines.append("")

    lines.extend([
        "## Food, cultural sites, and city views",
        "- Food: hawker centres, Chinatown, Kampong Glam, and Maxwell Food Centre are the strongest sample matches.",
        "- Cultural sites: National Gallery, Civic District, Kampong Glam heritage trail, and Chinatown walk.",
        "- City views: Marina Bay, Gardens by the Bay, and skyline-focused areas are highlighted for scenic value.",
        "",
        "## Estimated budget range",
        f"- Flights: ₹{budget.get('flights_inr', 0):,}",
        f"- Hotel: ₹{budget.get('hotel_inr', 0):,}",
        f"- Activities: ₹{budget.get('activities_inr', 0):,}",
        f"- Estimated total: ₹{budget.get('estimated_total_inr', 0):,}",
        "",
        "## Practical travel tips",
        "- Keep a light day 1 because arrival timing and jet lag can change the pace.",
        "- Use MRT / public transport to keep costs under control.",
        "- Book the hotel early if you want the main city-view or heritage area options.",
        "- Carry a small umbrella and light layers because Singapore is humid and can change quickly.",
        "",
        "## Notes",
        "- This file is a sample/demo artifact generated from local JSON data.",
        "- Replace the local tools with real APIs when you are ready to book live travel inventory.",
    ])
    return "\n".join(lines) + "\n"


def save_trip_plan(plan: Dict[str, Any], output_dir: Path | None = None) -> Path:
    """Save the final trip plan to outputs/ as Markdown."""
    output_dir = output_dir or PROJECT_ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"trip_plan_{timestamp}.md"
    output_path.write_text(render_trip_plan_markdown(plan), encoding="utf-8")
    return output_path


class LLMClient:
    """Small wrapper around OpenAI JSON-mode calls with optional LangSmith tracing."""

    def __init__(self, demo_mode: str = "offline", model_name: str = "gpt-4o-mini", temperature: float = 0.2):
        """Create a client.

        Args:
            demo_mode: "offline" for deterministic classroom mode, "live" for OpenAI calls.
            model_name: OpenAI model name.
            temperature: Sampling temperature for live calls.
        """
        self.demo_mode = demo_mode
        self.model_name = model_name
        self.temperature = temperature
        self._client = None

        if self.demo_mode == "live":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is missing. Add it to .env or set DEMO_MODE=offline "
                    "to run the classroom-safe deterministic version."
                )
            if OpenAI is None:
                raise RuntimeError("The openai package is not installed. Run: pip install -r requirements.txt")
            client = OpenAI(api_key=api_key)
            langsmith_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
            langsmith_key = os.getenv("LANGSMITH_API_KEY")
            if langsmith_enabled and langsmith_key and wrap_openai is not None:
                client = wrap_openai(client)
            self._client = client

    def complete_json(self, system_prompt: str, user_payload: Dict[str, Any], purpose: str) -> Dict[str, Any]:
        """Call the model and ask for a JSON object.

        Args:
            system_prompt: Instruction prompt for the agent.
            user_payload: JSON-serialisable payload passed to the model.
            purpose: Human-readable purpose shown in error messages.

        Returns:
            Parsed JSON object.

        Raises:
            RuntimeError: If live mode call fails.
        """
        if self.demo_mode != "live":
            raise RuntimeError("LLMClient.complete_json should only be called in live mode.")

        # COST NOTE: Each call is intentionally small. A full demo uses about 5-7 calls
        # with local data, usually well under the target classroom cost when using gpt-4o-mini.
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - depends on live API/network
            raise RuntimeError(f"Live LLM call failed while handling {purpose}: {exc}") from exc

        content = response.choices[0].message.content or "{}"
        parsed = parse_json_safely(content)
        if "error" in parsed:
            parsed["purpose"] = purpose
        return parsed
