"""Streamlit frontend for the existing multi-agent travel planner."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from main import run_pipeline
from tools.faq_rag import answer_faq_question
from utils import pretty_json, save_trip_plan, validate_trip_request


DEFAULT_REQUEST = (
    "Plan a 4-day Singapore trip from Mumbai for two people. Mid-budget. "
    "Avoid red-eye flights. Prefer food, city views, and cultural sites. "
    "Keep hotel budget under ₹45,000."
)


def _inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: dark; }
        html, body { overflow-x: hidden; }
        [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(circle at top, #18263d 0%, #0b1220 38%, #040812 100%);
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stMain"] { padding-top: 0; }
        [data-testid="stMainBlockContainer"] { padding-top: 0; padding-bottom: 0; }
        .block-container {
          max-width: 1240px !important;
          margin: 0 auto;
          padding-top: 0.35rem !important;
          padding-bottom: 2rem !important;
          padding-left: 1rem !important;
          padding-right: 1rem !important;
        }
        section[data-testid="stSidebar"] {
          background: linear-gradient(180deg, #07111f 0%, #0b1728 100%);
          border-right: 1px solid rgba(148, 163, 184, 0.18);
        }
        section[data-testid="stSidebar"] * { color: #e5eefb !important; }
        .hero-card {
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 24px;
          padding: 1.15rem 1.1rem;
          background: linear-gradient(135deg, rgba(17, 24, 39, 0.98), rgba(30, 41, 59, 0.92));
          box-shadow: 0 18px 40px rgba(8, 15, 27, 0.45);
          margin-top: 18px;
          margin-bottom: 0.9rem;
          text-align: center;
        }
        .glass-card {
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 20px;
          padding: 1rem 1.05rem;
          background: linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(8, 15, 27, 0.92));
          box-shadow: 0 14px 30px rgba(8, 15, 27, 0.35);
          margin-bottom: 1rem;
        }
        .prompt-shell {
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 20px;
          padding: 0.9rem;
          background: rgba(8, 15, 27, 0.78);
          box-shadow: 0 14px 30px rgba(8, 15, 27, 0.35);
          margin-bottom: 1rem;
        }
        .dashboard-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 1rem;
        }
        @media (max-width: 980px) {
          .dashboard-grid { grid-template-columns: 1fr; }
        }
        .kicker { letter-spacing: 0.18em; text-transform: uppercase; color: #8ec5ff; font-size: 0.82rem; }
        .tiny-note { color: #dbe5f5; font-size: 0.95rem; }
        .stButton > button {
          width: 100%;
          border-radius: 14px;
          border: 1px solid rgba(129, 140, 248, 0.45);
          background: linear-gradient(135deg, #6d5dfc 0%, #4f8cff 100%);
          color: #fff;
          font-weight: 700;
          padding: 0.65rem 1rem;
          box-shadow: 0 10px 24px rgba(109, 93, 252, 0.35);
        }
        .stButton > button:hover {
          background: linear-gradient(135deg, #7c69ff 0%, #5da0ff 100%);
          box-shadow: 0 14px 28px rgba(109, 93, 252, 0.45);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_budget_summary(itinerary: Dict[str, Any]) -> None:
    budget = itinerary.get("budget", {}) or {}
    st.markdown("<div class='glass-card'><h3 style='margin-top:0'>Budget Summary</h3></div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Flights", f"₹{budget.get('flights_inr', 0):,}")
    col2.metric("Hotel", f"₹{budget.get('hotel_inr', 0):,}")
    col3.metric("Activities", f"₹{budget.get('activities_inr', 0):,}")
    col4.metric("Estimated total", f"₹{budget.get('estimated_total_inr', 0):,}")


def _render_card(title: str, body: str) -> None:
    st.markdown(
        f"<article class='glass-card'><h4 style='margin:0 0 0.35rem 0; font-size:1.02rem;'>{title}</h4><div class='tiny-note'>{body}</div></article>",
        unsafe_allow_html=True,
    )


def _render_result_cards(final_itinerary: Dict[str, Any], output_path: str) -> None:
    flight = final_itinerary.get("selected_flight", {}) or {}
    hotel = final_itinerary.get("selected_hotel", {}) or {}
    budget = final_itinerary.get("budget", {}) or {}

    st.markdown("<div class='dashboard-grid'>", unsafe_allow_html=True)

    with st.container():
        _render_card(
            "Selected Flight",
            f"<strong>{flight.get('airline', 'N/A')} {flight.get('flight_id', '')}</strong><br/>"
            f"{flight.get('origin', 'Mumbai')} → {flight.get('destination', 'Singapore')}<br/>"
            f"Depart: {flight.get('depart_time', 'N/A')} · Arrive: {flight.get('arrive_time', 'N/A')}<br/>"
            f"Price: ₹{flight.get('price_inr', 0):,}<br/>"
            f"Notes: {flight.get('notes', 'No notes available.')}",
        )

    with st.container():
        _render_card(
            "Selected Hotel",
            f"<strong>{hotel.get('name', 'N/A')}</strong> · {hotel.get('area', 'N/A')}<br/>"
            f"{hotel.get('nights', 0)} nights · ₹{hotel.get('total_price_inr', 0):,} total<br/>"
            f"Rating: {hotel.get('rating', 'N/A')} / 5<br/>"
            f"Notes: {hotel.get('notes', 'No notes available.')}",
        )

    with st.container():
        _render_card(
            "Estimated Total Budget",
            f"Flights: ₹{budget.get('flights_inr', 0):,}<br/>"
            f"Hotel: ₹{budget.get('hotel_inr', 0):,}<br/>"
            f"Activities: ₹{budget.get('activities_inr', 0):,}<br/>"
            f"<strong>Total: ₹{budget.get('estimated_total_inr', 0):,}</strong>",
        )

    with st.container():
        _render_card(
            "Day-by-Day Itinerary",
            "<ul style='margin:0; padding-left:1rem;'>" +
            "".join(
                f"<li><strong>Day {day.get('day', '?')}</strong>: {day.get('focus', 'Plan block')}</li>"
                for day in (final_itinerary.get('daily_plan', []) or [])
            ) +
            "</ul>",
        )

    with st.container():
        _render_card(
            "Budget Summary",
            "<ul style='margin:0; padding-left:1rem;'>"
            f"<li>Flights: ₹{budget.get('flights_inr', 0):,}</li>"
            f"<li>Hotel: ₹{budget.get('hotel_inr', 0):,}</li>"
            f"<li>Activities: ₹{budget.get('activities_inr', 0):,}</li>"
            f"<li><strong>Total: ₹{budget.get('estimated_total_inr', 0):,}</strong></li>"
            "</ul>",
        )

    with st.container():
        _render_card(
            "Assumptions",
            "<ul style='margin:0; padding-left:1rem;'>" +
            "".join(f"<li>{item}</li>" for item in (final_itinerary.get('assumptions', []) or [])) +
            "</ul>",
        )

    with st.container():
        _render_card(
            "Trade-offs",
            "<ul style='margin:0; padding-left:1rem;'>" +
            "".join(f"<li>{item}</li>" for item in (final_itinerary.get('tradeoffs', []) or [])) +
            "</ul>",
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        f"<article class='glass-card'><strong>Saved Markdown path:</strong> {output_path}</article>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="AI-Powered Travel Planner", layout="wide")
    _inject_theme()

    st.markdown(
        """
        <div class='hero-card'>
          <p class='kicker'>✈️ AI-Powered Travel Planner</p>
          <h1 style='margin:0 0 0.35rem 0; font-size:2.3rem; line-height:1.1;'>Plan your perfect Singapore trip with a polished AI travel dashboard</h1>
          <p class='tiny-note' style='margin-bottom:0; max-width: 880px; margin-left:auto; margin-right:auto;'>Offline-first, secure, and ready to demo without exposing API keys or requiring live mode.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Settings")
        st.caption("Offline mode is the safest demo path and does not require API keys.")
        demo_mode = st.selectbox("Mode", ["offline", "live"], index=0)
        model_name = st.text_input("Model name", value="gpt-4o-mini", help="Used for live mode only.")
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
        show_trace = st.checkbox("Show Full Trace", value=False)
        st.caption(f"Preview: model {model_name}, temperature {temperature:.2f}, mode {demo_mode}.")

    st.markdown("<div class='glass-card'><h2 style='margin-top:0; font-size:1.1rem;'>Describe Your Dream Trip</h2><p class='tiny-note' style='margin-bottom:0;'>Use the prompt below or write your own request. The planner stays offline by default.</p></div>", unsafe_allow_html=True)

    prompt_col, action_col = st.columns([6, 2], vertical_alignment="bottom", gap="small")
    with prompt_col:
        st.markdown("<div class='prompt-shell'>", unsafe_allow_html=True)
        request_text = st.text_area("Trip prompt", value=DEFAULT_REQUEST, height=165, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    with action_col:
        st.markdown("<div class='prompt-shell' style='padding: 0.55rem; height: 100%;'>", unsafe_allow_html=True)
        plan_clicked = st.button("🚀 Plan Trip", type="primary", use_container_width=True)
        st.caption("Safe demo path · no live keys required.")
        st.markdown("</div>", unsafe_allow_html=True)

    if plan_clicked:
        validation = validate_trip_request(request_text)
        if not validation["valid"]:
            st.error("Trip request validation failed.")
            for issue in validation["errors"]:
                st.write(f"- {issue}")
            return

        with st.spinner("Planning your trip..."):
            result = run_pipeline(request_text, demo_mode=demo_mode)
            output_path = save_trip_plan(result)

        final_itinerary = result.get("final_output", {}).get("final_itinerary", {})

        st.success("Trip plan ready.")

        _render_result_cards(final_itinerary, str(output_path))

        st.markdown("<div class='glass-card'><h3 style='margin-top:0'>Detailed Day Plan</h3></div>", unsafe_allow_html=True)
        for day in final_itinerary.get("daily_plan", []) or []:
            st.markdown(f"<div class='glass-card'><h4 style='margin-top:0'>Day {day.get('day', '?')} — {day.get('focus', 'Plan block')}</h4></div>", unsafe_allow_html=True)
            activities = day.get("activities", []) or []
            if not activities:
                st.write("- Buffer / departure day with flexible free time.")
                continue
            for activity in activities:
                st.write(f"- {activity.get('name', 'Activity')} ({activity.get('area', 'Area')})")
                st.write(f"  - Best time: {activity.get('best_time', 'TBD')}")
                st.write(f"  - Estimated cost: ₹{activity.get('estimated_cost_inr', 0):,}")
                st.write(f"  - Why it fits: {activity.get('why_it_fits', 'Matches the stated preferences.')}")

        if show_trace:
            st.markdown("<div class='glass-card'><h3 style='margin-top:0'>Full Trace</h3></div>", unsafe_allow_html=True)
            st.code(pretty_json(result), language="json")

    st.markdown("<div class='glass-card'><h2 style='margin-top:0; font-size:1.1rem;'>Ask Expedia FAQ</h2><p class='tiny-note' style='margin-bottom:0;'>Search the Expedia FAQ PDF using hybrid dense + sparse retrieval with offline-safe local embeddings.</p></div>", unsafe_allow_html=True)
    faq_question = st.text_input("Expedia FAQ question", value="", placeholder="Example: What is Expedia's cancellation policy?")
    faq_clicked = st.button("Search FAQ", use_container_width=True)

    if faq_clicked and faq_question.strip():
        with st.spinner("Searching the FAQ document..."):
            faq_result = answer_faq_question(faq_question)

        st.info(faq_result["answer"])
        st.caption(f"Confidence: {faq_result.get('confidence', 'low')} · {faq_result.get('retrieval_note', 'Hybrid retrieval used local context.')}")
        if faq_result.get("sources"):
            st.write("Source references:")
            for source in faq_result["sources"]:
                st.write(f"- page {source['page']} · {source['source']} · chunk {source['chunk_id']}")
        if faq_result.get("retrieved_chunks"):
            with st.expander("Retrieved FAQ snippets"):
                for chunk in faq_result["retrieved_chunks"][:4]:
                    st.write(f"- {chunk['text'][:220]} ...")
                    st.caption(f"chunk {chunk['chunk_id']} · page {chunk['page']} · combined score {chunk['combined_score']:.3f}")


if __name__ == "__main__":
    main()
