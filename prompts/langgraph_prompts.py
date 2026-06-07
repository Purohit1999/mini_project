"""LangChain prompt templates for the LangGraph travel-planner flow."""

from langchain_core.prompts import PromptTemplate

VALIDATION_PROMPT = PromptTemplate.from_template(
    "Validate the travel request and confirm it matches the Singapore demo contract: {request_text}"
)

FLIGHT_PROMPT = PromptTemplate.from_template(
    "Search the flight options that best match the request and constraints: {request_text}"
)

HOTEL_PROMPT = PromptTemplate.from_template(
    "Search the hotel options that fit budget, area, and preference rules: {request_text}"
)

ITINERARY_PROMPT = PromptTemplate.from_template(
    "Create the first itinerary draft from the flight, hotel, and activity outputs for: {request_text}"
)

CRITIC_PROMPT = PromptTemplate.from_template(
    "Review the draft itinerary for budget, pacing, and preference fit: {request_text}"
)

FINAL_PROMPT = PromptTemplate.from_template(
    "Refine the itinerary into the final travel plan and make trade-offs explicit: {request_text}"
)

EXPORT_PROMPT = PromptTemplate.from_template(
    "Export the final itinerary to Markdown in the outputs directory for: {request_text}"
)

FAQ_ANSWER_PROMPT = PromptTemplate.from_template(
    "Answer only from the Expedia FAQ document context. If the FAQ context is insufficient, say so clearly and do not invent policies, prices, or booking rules. Keep the answer concise and user-friendly: {question}"
)
