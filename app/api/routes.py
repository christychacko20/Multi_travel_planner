from uuid import uuid4

from fastapi import APIRouter, HTTPException
from psycopg import Error

from app.api.schemas import ResumeRequest, RunRequest, RunResponse
from app.db import save_run
from app.graph.workflow import build_workflow

router = APIRouter(prefix="/runs", tags=["runs"])
workflows: dict[str, dict] = {}


def response_for(run_id: str, state: dict) -> RunResponse:
    return RunResponse(run_id=run_id, **{key: value for key, value in state.items() if key != "run_id"})


async def persist(run_id: str, state: dict) -> None:
    try:
        await save_run(run_id, state["task"], state["status"], state)
    except Error:
        # PostgreSQL is optional for the local demo; in production this should be monitored.
        return


@router.post("", response_model=RunResponse)
async def create_run(request: RunRequest) -> RunResponse:
    run_id = str(uuid4())
    initial = {
        "run_id": run_id,
        "task": request.task,
        "metadata": request.metadata,
        "travel": request.travel.model_dump(mode="json") if request.travel else {},
        "audit": [],
    }
    state = await build_workflow().ainvoke(initial)
    workflows[run_id] = state
    await persist(run_id, state)
    return response_for(run_id, state)


@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(run_id: str, request: ResumeRequest) -> RunResponse:
    state = workflows.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if state.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Run is not awaiting approval.")
    if not request.approved:
        state = {
            **state,
            "status": "completed",
            "response": "Workflow cancelled by human approval.",
            "audit": state.get("audit", []) + ["approval:rejected"],
        }
    else:
        state = await build_workflow(require_approval=False).ainvoke(
            {**state, "audit": state["audit"] + ["approval:approved"]}
        )
    workflows[run_id] = state
    await persist(run_id, state)
    return response_for(run_id, state)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    state = workflows.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return response_for(run_id, state)
