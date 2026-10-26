from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph.nodes import (
    approval_node,
    execute_node,
    guardrail_node,
    planner_node,
    response_node,
    route_after_guardrails,
)
from app.graph.state import WorkflowState


def build_workflow(require_approval: bool | None = None):
    if require_approval is None:
        require_approval = get_settings().approval_required
    graph = StateGraph(WorkflowState)
    graph.add_node("guardrails", guardrail_node)
    graph.add_node("planner", planner_node)
    graph.add_node("approval", approval_node)
    graph.add_node("executor", execute_node)
    graph.add_node("response", response_node)
    graph.add_edge(START, "guardrails")
    graph.add_conditional_edges(
        "guardrails", route_after_guardrails, {"plan": "planner", "end": "response"}
    )
    if require_approval:
        graph.add_edge("planner", "approval")
        graph.add_edge("approval", END)
    else:
        graph.add_edge("planner", "executor")
    graph.add_edge("executor", "response")
    graph.add_edge("response", END)
    return graph.compile()
