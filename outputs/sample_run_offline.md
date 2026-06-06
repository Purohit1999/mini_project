# Sample Offline Run

Command:

```bash
python main.py
```

Expected final output from the packaged offline demo:

```text
=== Final Travel Plan ===
{
  "final_itinerary": {
    "status": "final",
    "selected_flight": {
      "flight_id": "SQ-421",
      "origin": "Mumbai",
      "destination": "Singapore",
      "airline": "Singapore Airlines",
      "depart_time": "11:45",
      "arrive_time": "19:50",
      "duration_hours": 5.6,
      "stops": 0,
      "price_inr": 28500,
      "baggage": "25 kg checked + 7 kg cabin",
      "tags": [
        "direct",
        "daytime",
        "premium",
        "reliable"
      ],
      "notes": "Comfortable direct daytime option; arrives before dinner.",
      "selection_score": 6
    },
    "selected_hotel": {
      "hotel_id": "SG-H03",
      "destination": "Singapore",
      "name": "Bugis Heritage Inn",
      "area": "Bugis",
      "price_per_night_inr": 8900,
      "rating": 4.1,
      "amenities": [
        "metro nearby",
        "self check-in"
      ],
      "tags": [
        "budget",
        "culture",
        "metro",
        "walkable"
      ],
      "notes": "Strong budget option near Arab Street and Kampong Glam.",
      "nights": 3,
      "total_price_inr": 26700,
      "selection_score": 18
    },
    "daily_plan": [
      {
        "day": 1,
        "focus": "Arrival and light local exploration",
        "activities": [
          {
            "name": "Kampong Glam food and heritage trail",
            "area": "Bugis",
            "best_time": "Late afternoon",
            "duration_hours": 3,
            "estimated_cost_inr": 1500,
            "why_it_fits": "Fits well with a Bugis hotel base."
          }
        ]
      },
      {
        "day": 2,
        "focus": "Preference-led sightseeing block",
        "activities": [
          {
            "name": "Chinatown and Maxwell Food Centre walk",
            "area": "Chinatown",
            "best_time": "Evening",
            "duration_hours": 3,
            "estimated_cost_inr": 1600,
            "why_it_fits": "Works well on arrival day if the flight lands before evening."
          },
          {
            "name": "Hawker centre tasting route",
            "area": "Multiple",
            "best_time": "Lunch or dinner",
            "duration_hours": 4,
            "estimated_cost_inr": 2200,
            "why_it_fits": "Strong fit for food-focused travellers."
          }
        ]
      },
      {
        "day": 3,
        "focus": "Preference-led sightseeing block",
        "activities": [
          {
            "name": "National Gallery and Civic District",
            "area": "Civic District",
            "best_time": "Morning",
            "duration_hours": 4,
            "estimated_cost_inr": 1200,
            "why_it_fits": "Good choice for culture-focused travellers."
          },
          {
            "name": "Gardens by the Bay + Marina Bay walk",
            "area": "Marina Bay",
            "best_time": "Afternoon to night",
            "duration_hours": 5,
            "estimated_cost_inr": 2800,
            "why_it_fits": "Pairs well with sunset and the evening light show."
          }
        ]
      },
      {
        "day": 4,
        "focus": "Slow morning and departure buffer",
        "activities": []
      }
    ],
    "budget": {
      "flights_inr": 57000,
      "hotel_inr": 26700,
      "activities_inr": 18600,
      "estimated_total_inr": 102300
    },
    "tradeoffs": [
      "Uses local sample data rather than live inventory.",
      "Prioritises avoiding red-eye flights when requested.",
      "Keeps hotel selection close to the stated budget before premium views."
    ],
    "assumptions": [
      "Local sample data simulates travel APIs.",
      "Prices are teaching estimates, not live market quotes.",
      "The final plan prioritises constraints before nice-to-have preferences."
    ],
    "quality_score_after_reflexion": 90,
    "critic_summary": "Ready with minor polish"
  },
  "changes_after_critique": [
    "Kept core choices and made assumptions/trade-offs explicit."
  ],
  "final_notes": [
    "This is a teaching demo using sample data, not a booking engine.",
    "In production, each local tool can be replaced by a live API adapter.",
    "The same project can later be refactored with deeper agent frameworks."
  ]
}
```

What to notice:

- Requirement extraction captures food, culture, and views from the original request.
- The selected flight avoids the red-eye option.
- Hotel cost remains under the stated ₹45,000 hotel budget.
- Activities are sourced from local sample data and are not duplicated across the day plan.
- The Reflexion critic asks for explicit assumptions and trade-offs even when no blocking issue is found.
