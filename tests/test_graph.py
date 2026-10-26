import pytest

from app.api.schemas import TravelRequest
from app.graph.nodes import build_plan
from app.guardrails import validate_task


def test_guardrails_reject_destructive_request():
    result = validate_task("drop database production")
    assert result.allowed is False


def test_planner_selects_project_status_tool():
    plan = build_plan("Summarize project status")
    assert plan == [{"tool": "get_project_status", "arguments": {}}]


def test_planner_creates_multi_agent_travel_plan():
    plan = build_plan(
        "Plan a trip to Paris",
        {"origin": "Berlin", "destination": "Paris", "days": 4},
    )
    assert [step["tool"] for step in plan] == [
        "search_flights",
        "search_hotels",
        "search_activities",
        "assemble_itinerary",
    ]


@pytest.mark.asyncio
async def test_api_workflow_waits_for_approval(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("APPROVAL_REQUIRED", "true")
    from app.graph.workflow import build_workflow

    state = await build_workflow().ainvoke(
        {"run_id": "test-run", "task": "Summarize project status", "audit": []}
    )
    assert state["status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_v2_parallel_travel_workflow_reviews_budget_and_itinerary():
    from app.graph.workflow import build_workflow

    request = TravelRequest(
        origin="Berlin",
        destination="Paris",
        days=4,
        travelers=2,
        budget=2000,
    )
    state = await build_workflow(require_approval=False).ainvoke(
        {
            "run_id": "v2-travel-run",
            "task": "Plan my trip",
            "travel": request.model_dump(mode="json"),
            "audit": [],
        }
    )
    tools = [result["tool"] for result in state["results"]]
    assert tools[:3] == ["search_flights", "search_hotels", "search_activities"]
    assert "validate_budget" in tools
    assert "review_itinerary" in tools
    assert "within_budget" in state["response"]


@pytest.mark.asyncio
async def test_travel_workflow_builds_itinerary_after_approval():
    from app.graph.workflow import build_workflow

    state = await build_workflow(require_approval=False).ainvoke(
        {
            "run_id": "travel-run",
            "task": "Plan a trip to Paris",
            "metadata": {"destination": "Paris", "days": 2},
            "audit": [],
        }
    )
    assert state["status"] == "completed"
    assert "Travel plan for 2 days in Paris" in state["response"]
