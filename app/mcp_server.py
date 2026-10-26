from mcp.server.fastmcp import FastMCP

from app.tools import (
    assemble_itinerary,
    get_project_status,
    search_activities,
    search_flights,
    search_hotels,
    validate_budget,
)

mcp = FastMCP("agent-orchestration-platform")


@mcp.tool()
def project_status() -> dict[str, str]:
    """Return a safe, read-only project status summary."""
    return get_project_status({})


@mcp.tool()
def travel_options(
    origin: str = "Berlin",
    destination: str = "Paris",
    days: int = 3,
) -> dict:
    """Return deterministic demo flight, hotel, activity, and itinerary options."""
    trip = {"origin": origin, "destination": destination, "days": days}
    research = [
        search_flights(trip),
        search_hotels(trip),
        search_activities(trip),
    ]
    return assemble_itinerary({"trip": trip, "research": research})


@mcp.tool()
def validate_trip_budget(
    destination: str = "Paris",
    days: int = 3,
    travelers: int = 1,
    budget: float = 1500,
) -> dict:
    """Estimate whether a demo trip is within the supplied budget."""
    return validate_budget(
        {
            "trip": {
                "destination": destination,
                "days": days,
                "travelers": travelers,
                "budget": budget,
            },
            "flight_price": 180,
            "hotel_nightly_price": 140,
        }
    )


if __name__ == "__main__":
    mcp.run()
