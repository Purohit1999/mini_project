"""Deterministic local travel tools used by worker agents.

These functions simulate travel APIs using small JSON datasets. The point is
to teach agent-tool orchestration without requiring fragile external API keys.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from utils import PROJECT_ROOT, load_json_file


def load_travel_data(data_dir: Path | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """Load flights, hotels, and activities from local JSON files.

    Args:
        data_dir: Optional directory containing sample JSON files.

    Returns:
        Dictionary with flights, hotels, and activities lists.
    """
    data_dir = data_dir or PROJECT_ROOT / "data"
    return {
        "flights": load_json_file(data_dir / "sample_flights.json"),
        "hotels": load_json_file(data_dir / "sample_hotels.json"),
        "activities": load_json_file(data_dir / "sample_activities.json"),
    }


def _normalise(text: Any) -> str:
    """Normalise a text value for simple matching.

    Args:
        text: Text-like value.

    Returns:
        Lowercase trimmed string.
    """
    return str(text or "").strip().lower()


def _score_tags(item_tags: List[str], desired_tags: List[str]) -> int:
    """Score overlap between item tags and desired tags.

    Args:
        item_tags: Tags present on an item.
        desired_tags: Tags requested by the user.

    Returns:
        Number of overlapping tags.
    """
    item_tag_set = {_normalise(tag) for tag in item_tags}
    desired_tag_set = {_normalise(tag) for tag in desired_tags}
    return len(item_tag_set.intersection(desired_tag_set))


def search_flights(requirements: Dict[str, Any], flights: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Search local flight options for the requested route.

    Args:
        requirements: Parsed travel requirements.
        flights: Local flight records.
        top_k: Maximum number of results.

    Returns:
        Ranked list of matching flight options.
    """
    origin = _normalise(requirements.get("origin"))
    destination = _normalise(requirements.get("destination"))
    avoid_red_eye = bool(requirements.get("avoid_red_eye", False))

    candidates: List[Dict[str, Any]] = []
    for flight in flights:
        if origin and _normalise(flight.get("origin")) != origin:
            continue
        if destination and _normalise(flight.get("destination")) != destination:
            continue

        score = 0
        tags = [_normalise(tag) for tag in flight.get("tags", [])]
        if "direct" in tags:
            score += 4
        if "daytime" in tags:
            score += 3
        if "budget" in tags or "mid-budget" in tags:
            score += 2
        if avoid_red_eye and "red-eye" in tags:
            score -= 8
        score -= int(flight.get("stops", 0))
        score -= int(flight.get("price_inr", 0) / 20000)

        enriched = dict(flight)
        enriched["selection_score"] = score
        candidates.append(enriched)

    return sorted(candidates, key=lambda item: (item["selection_score"], -item["price_inr"]), reverse=True)[:top_k]


def search_hotels(requirements: Dict[str, Any], hotels: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Search local hotel options for the requested destination.

    Args:
        requirements: Parsed travel requirements.
        hotels: Local hotel records.
        top_k: Maximum number of results.

    Returns:
        Ranked list of matching hotels.
    """
    destination = _normalise(requirements.get("destination"))
    duration_days = int(requirements.get("duration_days") or 4)
    nights = max(duration_days - 1, 1)
    hotel_budget = int(requirements.get("hotel_budget_inr") or 0)
    preferences = requirements.get("preferences", [])

    candidates: List[Dict[str, Any]] = []
    for hotel in hotels:
        if destination and _normalise(hotel.get("destination")) != destination:
            continue

        total_price = int(hotel.get("price_per_night_inr", 0)) * nights
        score = 0
        score += _score_tags(hotel.get("tags", []), preferences) * 3
        score += int(float(hotel.get("rating", 0)) * 2)
        if hotel_budget and total_price <= hotel_budget:
            score += 5
        elif hotel_budget:
            score -= 5
        if "metro nearby" in [_normalise(a) for a in hotel.get("amenities", [])]:
            score += 2

        enriched = dict(hotel)
        enriched["nights"] = nights
        enriched["total_price_inr"] = total_price
        enriched["selection_score"] = score
        candidates.append(enriched)

    return sorted(candidates, key=lambda item: (item["selection_score"], -item["total_price_inr"]), reverse=True)[:top_k]


def search_activities(requirements: Dict[str, Any], activities: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    """Search local activities aligned with destination and preferences.

    Args:
        requirements: Parsed travel requirements.
        activities: Local activity records.
        top_k: Maximum number of results.

    Returns:
        Ranked list of activity candidates.
    """
    destination = _normalise(requirements.get("destination"))
    preferences = requirements.get("preferences", [])

    candidates: List[Dict[str, Any]] = []
    for activity in activities:
        if destination and _normalise(activity.get("destination")) != destination:
            continue

        score = _score_tags(activity.get("tags", []), preferences) * 4
        if "low-cost" in [_normalise(tag) for tag in activity.get("tags", [])]:
            score += 1

        enriched = dict(activity)
        enriched["selection_score"] = score
        candidates.append(enriched)

    return sorted(candidates, key=lambda item: (item["selection_score"], -item["cost_inr"]), reverse=True)[:top_k]


def estimate_trip_budget(
    selected_flight: Dict[str, Any],
    selected_hotel: Dict[str, Any],
    selected_activities: List[Dict[str, Any]],
    traveller_count: int,
) -> Dict[str, int]:
    """Estimate a simple trip budget.

    Args:
        selected_flight: Chosen flight option.
        selected_hotel: Chosen hotel option.
        selected_activities: Chosen activities.
        traveller_count: Number of travellers.

    Returns:
        Budget breakdown in INR.
    """
    flight_total = int(selected_flight.get("price_inr", 0)) * max(traveller_count, 1)
    hotel_total = int(selected_hotel.get("total_price_inr", selected_hotel.get("price_per_night_inr", 0)))
    activities_total = sum(int(activity.get("cost_inr", 0)) for activity in selected_activities) * max(traveller_count, 1)

    return {
        "flights_inr": flight_total,
        "hotel_inr": hotel_total,
        "activities_inr": activities_total,
        "estimated_total_inr": flight_total + hotel_total + activities_total,
    }
