"""Reflexion-style critic agent for itinerary quality checks."""

from __future__ import annotations

from typing import Any, Dict, List

from utils import LLMClient


class ItineraryCritic:
    """Critic that evaluates an itinerary and proposes refinements."""

    def __init__(self, llm: LLMClient):
        """Create a critic.

        Args:
            llm: LLM client wrapper.
        """
        self.llm = llm

    def evaluate(
        self,
        requirements: Dict[str, Any],
        draft_itinerary: Dict[str, Any],
        worker_outputs: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate a draft itinerary.

        Args:
            requirements: Parsed travel requirements.
            draft_itinerary: First itinerary draft.
            worker_outputs: Outputs from specialist workers.

        Returns:
            Critique with issue list, severity, and revision instructions.
        """
        if self.llm.demo_mode == "live":
            system_prompt = (
                "You are a Reflexion critic for a travel-planning agent team. "
                "Return JSON with keys: overall_assessment, issues, revision_instructions, quality_score. "
                "Check budget, pacing, constraints, unsupported assumptions, and preference fit. "
                "Do not invent facts beyond the provided worker outputs."
            )
            return self.llm.complete_json(
                system_prompt,
                {
                    "requirements": requirements,
                    "draft_itinerary": draft_itinerary,
                    "worker_outputs": worker_outputs,
                },
                purpose="itinerary critique",
            )

        issues: List[Dict[str, str]] = []
        hotel_budget = int(requirements.get("hotel_budget_inr") or 0)
        hotel_total = int(draft_itinerary.get("budget", {}).get("hotel_inr", 0))
        if hotel_budget and hotel_total > hotel_budget:
            issues.append({
                "severity": "high",
                "issue": "Hotel choice exceeds the stated hotel budget.",
                "fix": "Select a cheaper hotel option or explain the trade-off clearly.",
            })

        if requirements.get("avoid_red_eye"):
            flight_tags = draft_itinerary.get("selected_flight", {}).get("tags", [])
            if "red-eye" in [str(tag).lower() for tag in flight_tags]:
                issues.append({
                    "severity": "high",
                    "issue": "Selected flight violates the avoid-red-eye constraint.",
                    "fix": "Use a daytime or early-morning flight alternative.",
                })

        duration_days = int(requirements.get("duration_days") or 4)
        daily_plan = draft_itinerary.get("daily_plan", [])
        if len(daily_plan) != duration_days:
            issues.append({
                "severity": "medium",
                "issue": "The number of day blocks does not match trip duration.",
                "fix": "Create one clear plan block for each day of the trip.",
            })

        preferences = [str(pref).lower() for pref in requirements.get("preferences", [])]
        plan_text = str(draft_itinerary).lower()
        for pref in preferences:
            if pref and pref not in plan_text:
                issues.append({
                    "severity": "medium",
                    "issue": f"The itinerary does not visibly address the '{pref}' preference.",
                    "fix": f"Add at least one activity or explanation connected to '{pref}'.",
                })

        if not issues:
            issues.append({
                "severity": "low",
                "issue": "No major blocking issue found.",
                "fix": "Improve final answer by making assumptions and trade-offs explicit.",
            })

        quality_score = max(
            60,
            95
            - (len([issue for issue in issues if issue["severity"] == "high"]) * 20)
            - (len(issues) * 5),
        )
        return {
            "overall_assessment": "Refine before final response" if any(i["severity"] != "low" for i in issues) else "Ready with minor polish",
            "issues": issues,
            "revision_instructions": [
                issue["fix"] for issue in issues
            ],
            "quality_score": quality_score,
        }
