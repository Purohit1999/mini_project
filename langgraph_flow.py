"""LangGraph-based orchestration for the offline-safe travel planner."""

from __future__ import annotations

from typing import Any, Dict, TypedDict

from langgraph.graph import END, StateGraph

from agents.manager import TravelPlannerManager
from prompts.langgraph_prompts import (
    CRITIC_PROMPT,
    EXPORT_PROMPT,
    FINAL_PROMPT,
    FLIGHT_PROMPT,
    HOTEL_PROMPT,
    ITINERARY_PROMPT,
    VALIDATION_PROMPT,
)
from tools.travel_tools import load_travel_data
from utils import LLMClient, save_trip_plan, validate_trip_request


class PlannerState(TypedDict, total=False):
    request_text: str
    validation_errors: list[str]
    requirements: Dict[str, Any]
    worker_outputs: Dict[str, Any]
    draft_itinerary: Dict[str, Any]
    critique: Dict[str, Any]
    final_output: Dict[str, Any]
    markdown_path: str
    trace: list[str]
    status: str


def build_langgraph_pipeline(llm: LLMClient) -> StateGraph:
    """Build a minimal LangGraph pipeline that reuses the existing manager logic."""

    travel_data = load_travel_data()
    manager = TravelPlannerManager(llm=llm, travel_data=travel_data)

    def validate_request(state: PlannerState) -> PlannerState:
        prompt = VALIDATION_PROMPT.format(request_text=state["request_text"])
        validation = validate_trip_request(state["request_text"])
        state["trace"] = [prompt]
        if not validation["valid"]:
            state["validation_errors"] = validation["errors"]
            state["status"] = "error"
            return state
        state["requirements"] = manager.parse_request(state["request_text"])
        state["status"] = "validated"
        return state

    def flight_search(state: PlannerState) -> PlannerState:
        prompt = FLIGHT_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        worker_outputs = manager.run_workers(state["requirements"])
        state["worker_outputs"] = worker_outputs
        state["selected_flight"] = worker_outputs.get("flight", {}).get("recommendation")
        return state

    def hotel_search(state: PlannerState) -> PlannerState:
        prompt = HOTEL_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        state["selected_hotel"] = state["worker_outputs"].get("hotel", {}).get("recommendation")
        return state

    def itinerary_builder(state: PlannerState) -> PlannerState:
        prompt = ITINERARY_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        state["draft_itinerary"] = manager.create_draft_itinerary(state["requirements"], state["worker_outputs"])
        return state

    def critic_review(state: PlannerState) -> PlannerState:
        prompt = CRITIC_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        state["critique"] = manager.critic.evaluate(state["requirements"], state["draft_itinerary"], state["worker_outputs"])
        return state

    def final_formatter(state: PlannerState) -> PlannerState:
        prompt = FINAL_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        state["final_output"] = manager.refine_itinerary(
            state["requirements"],
            state["draft_itinerary"],
            state["critique"],
            state["worker_outputs"],
        )
        return state

    def markdown_export(state: PlannerState) -> PlannerState:
        prompt = EXPORT_PROMPT.format(request_text=state["request_text"])
        state.setdefault("trace", []).append(prompt)
        state["markdown_path"] = str(save_trip_plan(state["final_output"]))
        state["status"] = "complete"
        return state

    graph = StateGraph(PlannerState)
    graph.add_node("validate_request", validate_request)
    graph.add_node("flight_search", flight_search)
    graph.add_node("hotel_search", hotel_search)
    graph.add_node("itinerary_builder", itinerary_builder)
    graph.add_node("critic_review", critic_review)
    graph.add_node("final_formatter", final_formatter)
    graph.add_node("markdown_export", markdown_export)

    graph.set_entry_point("validate_request")
    graph.add_conditional_edges(
        "validate_request",
        lambda state: "error" if state.get("status") == "error" else "continue",
        {
            "error": END,
            "continue": "flight_search",
        },
    )
    graph.add_edge("flight_search", "hotel_search")
    graph.add_edge("hotel_search", "itinerary_builder")
    graph.add_edge("itinerary_builder", "critic_review")
    graph.add_edge("critic_review", "final_formatter")
    graph.add_edge("final_formatter", "markdown_export")
    graph.add_edge("markdown_export", END)

    return graph.compile()


def run_langgraph_pipeline(user_request: str, demo_mode: str | None = None) -> Dict[str, Any]:
    """Run the LangGraph planner flow and return a result structure compatible with the CLI/UI."""
    from main import resolve_request_text

    request_text = resolve_request_text(user_request)
    settings = {
        "demo_mode": demo_mode or "offline",
        "model_name": "gpt-4o-mini",
        "temperature": 0.2,
    }
    llm = LLMClient(demo_mode=settings["demo_mode"], model_name=settings["model_name"], temperature=float(settings["temperature"]))
    app = build_langgraph_pipeline(llm)
    state = app.invoke({"request_text": request_text})

    if state.get("status") == "error":
        return {
            "user_request": request_text,
            "status": "error",
            "validation_errors": state.get("validation_errors", []),
            "trace": state.get("trace", []),
        }

    return {
        "user_request": request_text,
        "requirements": state.get("requirements", {}),
        "worker_outputs": state.get("worker_outputs", {}),
        "draft_itinerary": state.get("draft_itinerary", {}),
        "critique": state.get("critique", {}),
        "final_output": state.get("final_output", {}),
        "markdown_path": state.get("markdown_path"),
        "trace": state.get("trace", []),
        "status": state.get("status", "complete"),
    }
