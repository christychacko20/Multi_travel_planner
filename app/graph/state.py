from typing import Any, Literal, TypedDict


class WorkflowState(TypedDict, total=False):
    run_id: str
    task: str
    metadata: dict[str, Any]
    travel: dict[str, Any]
    status: Literal["received", "planned", "awaiting_approval", "running", "completed", "failed"]
    plan: list[dict[str, Any]]
    results: list[dict[str, Any]]
    response: str
    error: str
    audit: list[str]
