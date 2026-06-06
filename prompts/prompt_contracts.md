# Prompt Contracts for the Travel Planner Agent Team

This file is a trainer-facing reference for the practical build.

## Manager requirement extraction

Input: natural-language travel request.

Output JSON keys:

```json
{
  "origin": "Mumbai",
  "destination": "Singapore",
  "duration_days": 4,
  "traveller_count": 2,
  "budget_level": "mid-budget",
  "hotel_budget_inr": 45000,
  "avoid_red_eye": true,
  "preferences": ["food", "views", "culture"],
  "assumptions": [],
  "missing_information": []
}
```

Teaching point: the manager turns vague language into a stable contract that workers can use.

## Worker reports

Every worker returns:

```json
{
  "worker": "flight_search",
  "react_trace": [
    "Thought: ...",
    "Action: ...",
    "Observation: ...",
    "Decision: ..."
  ],
  "options": [],
  "recommendation": {},
  "rationale": "..."
}
```

Teaching point: ReAct does not have to be uncontrolled. In this project it is a disciplined reasoning trace around a real tool call.

## Critic report

The Reflexion critic returns:

```json
{
  "overall_assessment": "Refine before final response",
  "issues": [
    {
      "severity": "medium",
      "issue": "The plan does not visibly address the food preference.",
      "fix": "Add a local food activity."
    }
  ],
  "revision_instructions": [],
  "quality_score": 85
}
```

Teaching point: critique becomes useful only when it is actionable enough for the manager to revise the output.

## Final output

The final manager returns:

```json
{
  "final_itinerary": {},
  "changes_after_critique": [],
  "final_notes": []
}
```

Teaching point: final answers should expose trade-offs, not hide them.
