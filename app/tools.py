from collections.abc import Callable
from typing import Any

Tool = Callable[[dict[str, Any]], dict[str, Any]]


def get_project_status(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": "get_project_status",
        "status": "operational",
        "message": "The project is operational and ready for the requested workflow.",
    }


def create_task(arguments: dict[str, Any]) -> dict[str, Any]:
    title = arguments.get("title", "Untitled task").strip()
    return {"tool": "create_task", "created": True, "title": title}


def search_flights(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent": "flight_agent",
        "tool": "search_flights",
        "origin": arguments.get("origin", "Berlin"),
        "destination": arguments.get("destination", "Paris"),
        "options": [
            {"airline": "Demo Air", "price": 180, "currency": "EUR", "stops": 0},
            {"airline": "Budget Wings", "price": 120, "currency": "EUR", "stops": 1},
        ],
    }


def search_hotels(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent": "hotel_agent",
        "tool": "search_hotels",
        "destination": arguments.get("destination", "Paris"),
        "options": [
            {"name": "Central Garden Hotel", "nightly_price": 140, "currency": "EUR", "rating": 4.6},
            {"name": "Riverside Guesthouse", "nightly_price": 95, "currency": "EUR", "rating": 4.2},
        ],
    }


def search_activities(arguments: dict[str, Any]) -> dict[str, Any]:
    destination = arguments.get("destination", "Paris")
    return {
        "agent": "activity_agent",
        "tool": "search_activities",
        "destination": destination,
        "activities": [
            f"Guided historic walking tour in {destination}",
            f"Local food market experience in {destination}",
            f"Museum and landmark day in {destination}",
        ],
    }


def assemble_itinerary(arguments: dict[str, Any]) -> dict[str, Any]:
    trip = arguments.get("trip", {})
    research = arguments.get("research", [])
    destination = trip.get("destination", "Paris")
    days = int(trip.get("days", 3))
    hotel_options = next(
        (item["options"] for item in research if item.get("tool") == "search_hotels"), []
    )
    flight_options = next(
        (item["options"] for item in research if item.get("tool") == "search_flights"), []
    )
    activities = next(
        (item["activities"] for item in research if item.get("tool") == "search_activities"), []
    )
    hotel = hotel_options[0] if hotel_options else {}
    flight = flight_options[0] if flight_options else {}
    return {
        "agent": "itinerary_agent",
        "tool": "assemble_itinerary",
        "destination": destination,
        "days": days,
        "flight": flight,
        "hotel": hotel,
        "daily_plan": [
            {"day": day, "activity": activities[(day - 1) % len(activities)]}
            for day in range(1, days + 1)
        ]
        if activities
        else [],
        "estimated_total": arguments.get("budget_check", {}).get("estimated_total", 0),
        "budget_status": arguments.get("budget_check", {}).get("status", "not_checked"),
    }


def validate_budget(arguments: dict[str, Any]) -> dict[str, Any]:
    trip = arguments.get("trip", {})
    days = int(trip.get("days", 3))
    travelers = int(trip.get("travelers", 1))
    flight_price = float(arguments.get("flight_price", 180)) * travelers
    hotel_price = float(arguments.get("hotel_nightly_price", 140)) * max(days - 1, 1)
    activities_price = 35 * days * travelers
    estimated_total = flight_price + hotel_price + activities_price
    budget = float(trip.get("budget", 1500))
    return {
        "agent": "budget_agent",
        "tool": "validate_budget",
        "budget": budget,
        "estimated_total": estimated_total,
        "remaining": budget - estimated_total,
        "status": "within_budget" if estimated_total <= budget else "over_budget",
    }


def review_itinerary(arguments: dict[str, Any]) -> dict[str, Any]:
    itinerary = arguments.get("itinerary", {})
    issues: list[str] = []
    if not itinerary.get("flight"):
        issues.append("No flight option selected.")
    if not itinerary.get("hotel"):
        issues.append("No hotel option selected.")
    if not itinerary.get("daily_plan"):
        issues.append("No daily activities selected.")
    return {
        "agent": "review_agent",
        "tool": "review_itinerary",
        "approved": not issues,
        "issues": issues,
        "message": "Itinerary passed review." if not issues else "Itinerary needs revision.",
    }


TOOL_REGISTRY: dict[str, Tool] = {
    "get_project_status": get_project_status,
    "create_task": create_task,
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "search_activities": search_activities,
    "assemble_itinerary": assemble_itinerary,
    "validate_budget": validate_budget,
    "review_itinerary": review_itinerary,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")
    return tool(arguments)
