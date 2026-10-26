import asyncio
from typing import Any

from app.config import get_settings
from app.guardrails import validate_task
from app.tools import execute_tool


def guardrail_node(state: dict[str, Any]) -> dict[str, Any]:
    result = validate_task(state["task"])
    if not result.allowed:
        return {
            "status": "failed",
            "error": result.reason,
            "response": f"Request rejected: {result.reason}",
            "audit": state.get("audit", []) + ["guardrails:rejected"],
        }
    return {"status": "received", "audit": state.get("audit", []) + ["guardrails:passed"]}


def build_plan(task: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    metadata = metadata or {}
    lowered = task.lower()
    if any(term in lowered for term in ("travel", "trip", "itinerary", "vacation")):
        trip = {
            "origin": metadata.get("origin", "Berlin"),
            "destination": metadata.get("destination", "Paris"),
            "days": metadata.get("days", 3),
            "travelers": metadata.get("travelers", 1),
            "budget": metadata.get("budget", 1500),
            "currency": metadata.get("currency", "EUR"),
        }
        return [
            {"tool": "search_flights", "arguments": trip},
            {"tool": "search_hotels", "arguments": trip},
            {"tool": "search_activities", "arguments": trip},
            {"tool": "assemble_itinerary", "arguments": {"trip": trip}},
        ]
    if "create" in lowered and "task" in lowered:
        return [{"tool": "create_task", "arguments": {"title": task[:120]}}]
    return [{"tool": "get_project_status", "arguments": {}}]


def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    travel = state.get("travel") or {}
    if travel:
        plan = [
            {"tool": "search_flights", "parallel": True},
            {"tool": "search_hotels", "parallel": True},
            {"tool": "search_activities", "parallel": True},
            {"tool": "validate_budget"},
            {"tool": "review_itinerary"},
            {"tool": "assemble_itinerary"},
        ]
    else:
        plan = build_plan(state["task"], state.get("metadata"))
    plan = plan[: get_settings().max_plan_steps]
    return {
        "plan": plan,
        "status": "planned",
        "audit": state.get("audit", []) + [f"planner:created:{len(plan)}-step-plan"],
    }


def approval_node(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "awaiting_approval",
        "audit": state.get("audit", []) + ["approval:required"],
    }


async def execute_node(state: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    audit = state.get("audit", []) + ["executor:started"]
    travel = state.get("travel") or {}
    if travel:
        research_steps = [
            ("search_flights", {"trip": travel}),
            ("search_hotels", {"trip": travel}),
            ("search_activities", {"trip": travel}),
        ]
        research = await asyncio.gather(
            *(
                asyncio.to_thread(execute_tool, name, arguments)
                for name, arguments in research_steps
            )
        )
        results.extend(research)
        audit.extend(
            [f"executor:completed:{result['tool']}" for result in research]
            + ["executor:parallel-research-completed"]
        )
        flight = next(item for item in research if item["tool"] == "search_flights")
        hotel = next(item for item in research if item["tool"] == "search_hotels")
        budget_check = execute_tool(
            "validate_budget",
            {
                "trip": travel,
                "flight_price": flight["options"][0]["price"],
                "hotel_nightly_price": hotel["options"][0]["nightly_price"],
            },
        )
        results.append(budget_check)
        itinerary = execute_tool(
            "assemble_itinerary",
            {"trip": travel, "research": research, "budget_check": budget_check},
        )
        results.append(itinerary)
        review = execute_tool("review_itinerary", {"itinerary": itinerary})
        results.append(review)
        audit.extend(
            [
                "executor:completed:validate_budget",
                "executor:completed:assemble_itinerary",
                "executor:completed:review_itinerary",
            ]
        )
        return {
            "status": "completed",
            "results": results,
            "audit": audit,
        }
    for step in state.get("plan", []):
        try:
            arguments = dict(step.get("arguments", {}))
            if step["tool"] == "assemble_itinerary":
                arguments["research"] = results
            results.append(execute_tool(step["tool"], arguments))
            audit.append(f"executor:completed:{step['tool']}")
        except (KeyError, TypeError, ValueError) as exc:
            audit.append(f"executor:failed:{step.get('tool', 'unknown')}")
            return fallback_node({**state, "audit": audit, "error": str(exc)})
    return {"status": "completed", "results": results, "audit": audit}


def fallback_node(state: dict[str, Any]) -> dict[str, Any]:
    message = (
        "The requested workflow could not complete through its primary tool path. "
        "Fallback response: the request was recorded for manual follow-up."
    )
    return {
        "status": "completed",
        "response": message,
        "audit": state.get("audit", []) + ["fallback:manual-follow-up"],
    }


def response_node(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("response"):
        return state
    results = state.get("results", [])
    itinerary = next(
        (result for result in results if result.get("tool") == "assemble_itinerary"), None
    )
    if itinerary:
        budget = next(
            (result for result in results if result.get("tool") == "validate_budget"), {}
        )
        review = next(
            (result for result in results if result.get("tool") == "review_itinerary"), {}
        )
        return {
            "status": "completed",
            "response": (
                f"Travel plan for {itinerary['days']} days in {itinerary['destination']}: "
                f"{itinerary['flight'].get('airline', 'flight')} at "
                f"{itinerary['flight'].get('price', 'N/A')} "
                f"{itinerary['flight'].get('currency', '')}, staying at "
                f"{itinerary['hotel'].get('name', 'recommended hotel')}. "
                f"Daily activities: "
                + "; ".join(
                    f"Day {item['day']}: {item['activity']}"
                    for item in itinerary["daily_plan"]
                )
                + f" Estimated total: {budget.get('estimated_total', 'N/A')} "
                f"{budget.get('currency', '')}. Budget status: {budget.get('status', 'unknown')}. "
                f"Review: {review.get('message', 'not reviewed')}"
            ),
            "audit": state.get("audit", []) + ["response:travel-itinerary-generated"],
        }
    return {
        "status": "completed",
        "response": f"Workflow completed successfully with {len(results)} tool result(s).",
        "audit": state.get("audit", []) + ["response:generated"],
    }


def route_after_guardrails(state: dict[str, Any]) -> str:
    return "end" if state.get("status") == "failed" else "plan"
