# Agent Orchestration Platform

This directory is **Version 2**, copied from the original `Multi_travel_agent` project.
Version 1 remains unchanged in the sibling directory.

## Version 2: structured multi-agent travel planner

This copy upgrades the original demo into a structured travel-planning workflow:

```text
Structured travel request
        |
        v
Parallel flight, hotel, and activity agents
        |
        v
Budget validation agent
        |
        v
Itinerary assembly
        |
        v
Review agent
        |
        v
Human approval
        |
        v
Final itinerary
```

Version 2 keeps the deterministic local data from Version 1, so it runs without external
travel API keys. The independent flight, hotel, and activity searches run concurrently,
then the budget and review agents run after the research results are available.

### Version 2 API request

```powershell
$run = Invoke-RestMethod -Method Post http://127.0.0.1:8000/runs `
  -ContentType "application/json" `
  -Body '{
    "task": "Plan my trip",
    "travel": {
      "origin": "Berlin",
      "destination": "Paris",
      "days": 4,
      "travelers": 2,
      "budget": 2000,
      "currency": "EUR",
      "preferences": ["museums", "local food"]
    }
  }'
```

The response should initially have:

```text
status: awaiting_approval
```

Review the generated plan and approve it manually:

```powershell
Invoke-RestMethod -Method Post `
  "http://127.0.0.1:8000/runs/$($run.run_id)/resume" `
  -ContentType "application/json" `
  -Body '{"approved":true}'
```

The final response includes the selected flight, hotel, daily activities, estimated total,
budget status, and review result.

### Interactive demo script

Start the API, then run:

```powershell
.\run_travel_demo.ps1
```

The script creates the request and asks:

```text
Approve this travel plan? (y/n)
```

Your answer is sent to the approval endpoint, so the human-in-the-loop behavior remains
visible during the demonstration.

### Version 2 improvements

- Structured `TravelRequest` validation with destination, dates, travelers, budget, and preferences
- Parallel specialist research for flights, hotels, and activities
- Budget agent calculating estimated trip cost and remaining budget
- Review agent checking that the itinerary is complete
- Human approval remains mandatory before specialist tools execute
- New MCP budget-validation tool
- Additional tests for the complete Version 2 workflow

## Overview

Agent Orchestration Platform is a production-oriented reference application for building
reliable multi-agent AI workflows with Python. It combines **LangGraph**, **FastAPI**,
**MCP**, and **PostgreSQL** to coordinate planning, tool execution, approvals, guardrails,
fallbacks, and audit history.

The project demonstrates how an AI system can do more than generate a response: it can
break a request into bounded steps, select tools, wait for a human decision before taking
action, recover from tool failures, and preserve the complete workflow state for review.

The current implementation uses a deterministic planner so it can run without an external
LLM provider or API key. The planner can be replaced with an LLM-backed planner without
changing the workflow's core safety and orchestration boundaries.

## Key features

- **Multi-agent workflow orchestration** with LangGraph state transitions
- **Automated planning** with bounded plan steps
- **Tool execution** through a central, typed tool registry
- **MCP integration** for exposing safe tools to MCP-compatible clients
- **FastAPI REST API** with OpenAPI documentation
- **Human-in-the-loop approvals** before planned actions execute
- **Guardrails** for empty, oversized, or destructive requests
- **Fallback mechanisms** for failed or unavailable tools
- **PostgreSQL persistence** for workflow runs, status, state, and audit data
- **Audit trail** showing guardrail, planning, approval, execution, fallback, and response events
- **Docker Compose support** for local PostgreSQL development
- **Automated tests and linting** with pytest and Ruff
- **Provider-neutral design** that can be extended with OpenAI, Anthropic, local models,
  or other AI providers

## Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| API | FastAPI | HTTP endpoints, validation, and OpenAPI docs |
| Orchestration | LangGraph | Stateful workflow graph and node routing |
| Agent tools | MCP | Standardized tool exposure for AI clients |
| Persistence | PostgreSQL | Durable run state and audit history |
| Database driver | psycopg | Async PostgreSQL connectivity |
| Validation | Pydantic | Typed request and configuration validation |
| Testing | pytest | Automated behavior tests |
| Quality | Ruff | Python linting and code quality |

## System architecture

```text
                           +----------------------+
                           |   MCP-compatible      |
                           |   Client / AI Agent   |
                           +----------+-----------+
                                      |
                                      v
+-------------+       +--------------+---------------+
| REST Client | ---->  | FastAPI Application          |
+-------------+       |                              |
                      |  Run API + Approval API       |
                      +--------------+---------------+
                                     |
                                     v
                      +--------------+---------------+
                      | LangGraph Workflow           |
                      |                              |
                      | Guardrails                   |
                      |      |                       |
                      |      v                       |
                      | Planner                      |
                      |      |                       |
                      |      v                       |
                      | Human Approval               |
                      |      |                       |
                      |      v                       |
                      | Tool Executor --------------+ |
                      |      |                     | |
                      |      v                     | |
                      | Fallback <-----------------+ |
                      |      |                       |
                      |      v                       |
                      | Response Builder             |
                      +--------------+---------------+
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
          +---------+----------+             +--------+---------+
          | MCP Tool Registry |             | PostgreSQL        |
          | project_status    |             | workflow_runs     |
          | create_task       |             | state + audit     |
          +--------------------+             +------------------+
```

### Main modules

| Module | Purpose |
|---|---|
| `app/main.py` | Creates the FastAPI application and startup lifecycle |
| `app/api/routes.py` | Run creation, approval, resume, and status endpoints |
| `app/api/schemas.py` | Typed API request and response models |
| `app/graph/workflow.py` | Defines and compiles the LangGraph state machine |
| `app/graph/nodes.py` | Guardrails, planning, approval, execution, fallback, and response nodes |
| `app/graph/state.py` | Shared workflow state contract |
| `app/tools.py` | Safe tool registry and tool execution boundary |
| `app/mcp_server.py` | MCP server exposing approved tools |
| `app/db.py` | PostgreSQL schema initialization and run persistence |
| `app/guardrails.py` | Input validation and destructive-request filtering |

## Agent interaction flow

The workflow follows a controlled sequence:

```text
User request
    |
    v
1. FastAPI validates request shape
    |
    v
2. Guardrails inspect task content
    |-- rejected --> failed response + audit event
    |
    v
3. Planner creates a bounded execution plan
    |
    v
4. Human approval checkpoint
    |-- rejected --> cancelled response + audit event
    |
    |-- approved
    v
5. Executor selects and runs registered tools
    |-- tool error --> fallback/manual follow-up response
    |
    v
6. Response node creates the final result
    |
    v
7. PostgreSQL stores state and audit history
```

### Example interaction

For the request `Summarize the current project status`:

1. The API creates a new `run_id`.
2. Guardrails approve the request.
3. The planner selects `get_project_status`.
4. The workflow enters `awaiting_approval`.
5. A human calls the resume endpoint with `{"approved": true}`.
6. The executor runs the selected tool.
7. The response node returns a successful completion message.
8. The run state and audit events are persisted to PostgreSQL.

## API reference

### Create a workflow run

```http
POST /runs
Content-Type: application/json
```

```json
{
  "task": "Summarize the current project status",
  "metadata": {
    "requested_by": "demo-user"
  }
}
```

### Approve or reject a run

```http
POST /runs/{run_id}/resume
Content-Type: application/json
```

Approve:

```json
{
  "approved": true
}
```

Reject:

```json
{
  "approved": false
}
```

### Get workflow status

```http
GET /runs/{run_id}
```

### Health check

```http
GET /health
```

Interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Local setup

### 1. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -e ".[dev]"
```

### 3. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Important settings:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Local PostgreSQL URL |
| `APPROVAL_REQUIRED` | Enables the human approval boundary | `true` |
| `MAX_PLAN_STEPS` | Maximum number of actions in a generated plan | `5` |
| `ENVIRONMENT` | Runtime environment name | `development` |

### 4. Start PostgreSQL

```powershell
docker compose up -d postgres
```

PostgreSQL is optional when running the demo locally. The API can still start without it,
but durable persistence will not be available until the database is running.

### 5. Start the API

```powershell
uvicorn app.main:app --reload
```

## Running the MCP server

The MCP server exposes safe tools independently from the REST API:

```powershell
py -m app.mcp_server
```

Available MCP tools include:

- `project_status`: read-only project status information

The same tool registry can be expanded with additional tools after adding input validation,
authorization rules, and tests.

## Testing and quality checks

Run the test suite:

```powershell
py -m pytest -q
```

Run lint checks:

```powershell
py -m ruff check .
```

## Extending the system

### Add a new tool

1. Implement the tool in `app/tools.py`.
2. Register it in `TOOL_REGISTRY`.
3. Add the tool to the planner's allowed plan mapping.
4. Expose it through MCP if external MCP clients need access.
5. Add success, failure, and guardrail tests.

### Replace the deterministic planner

The `build_plan` function in `app/graph/nodes.py` can be replaced by an LLM-backed planner.
The replacement should continue to:

- Return only registered tools
- Respect `MAX_PLAN_STEPS`
- Validate tool arguments
- Preserve the approval boundary
- Record planning decisions in the audit trail
- Return an explicit failure instead of silently selecting an unsafe fallback

### Production hardening

For production deployment, add authentication and authorization, request rate limiting,
secret management, structured logging, distributed tracing, a real PostgreSQL connection
pool, durable LangGraph checkpoints, idempotency keys, and a background job queue for
long-running workflows.

## Project structure

```text
.
├── app/
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── graph/
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── workflow.py
│   ├── config.py
│   ├── db.py
│   ├── guardrails.py
│   ├── main.py
│   ├── mcp_server.py
│   └── tools.py
├── tests/
│   └── test_graph.py
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Portfolio summary

This project demonstrates practical experience in:

- Designing multi-agent AI systems
- Orchestrating stateful workflows with LangGraph
- Building reliable tool-calling boundaries
- Integrating MCP for reusable agent tools
- Creating typed async APIs with FastAPI
- Implementing human-in-the-loop controls
- Applying guardrails and fallback strategies
- Persisting workflow state and audit history in PostgreSQL

## Travel planner demo

The project also includes a deterministic multi-agent travel-planning demo that does not
require external travel API keys. A travel request is routed to three specialist agents:

1. **Flight agent** - returns demo flight options.
2. **Hotel agent** - returns demo accommodation options.
3. **Activity agent** - returns destination activities.
4. **Itinerary agent** - combines the specialist results into a day-by-day itinerary.

The workflow still pauses at the existing human-approval checkpoint before these tools execute.
The demo data is intentionally local and repeatable; replace the tool implementations in
`app/tools.py` with real provider integrations when API credentials are available.

Example request:

```powershell
$run = Invoke-RestMethod -Method Post http://127.0.0.1:8000/runs `
  -ContentType "application/json" `
  -Body '{"task":"Plan a trip to Paris","metadata":{"origin":"Berlin","destination":"India","days":4,"travelers":2,"budget":2000,"currency":"EUR"}}'

$run
```

Approve the generated travel plan:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/runs/$($run.run_id)/resume" `
  -ContentType "application/json" `
  -Body '{"approved":true}'
```

For a one-command demo that creates and approves the request automatically, keep the API
running in one terminal and run this in another:

```powershell
.\run_travel_demo.ps1
```

The MCP server also exposes a `travel_options` tool:

```powershell
python -m app.mcp_server
#explorer.exe "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude"
```

An MCP client can call `travel_options` with `origin`, `destination`, and `days` to receive
the same demo itinerary.
