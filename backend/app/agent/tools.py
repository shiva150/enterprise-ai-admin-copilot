"""LangChain tools for the admin copilot.

Each tool is a thin wrapper around a pure-Python data-access or retrieval
function. Tools are directly callable via `tool.invoke({...})` — no agent,
no LLM, no framework ceremony. That lets Phase 2 tests cover the tool
surface without depending on model behavior.
"""

from typing import Any, Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db import queries as db
from app.rag.store import retrieve as rag_retrieve


# --------- query_db ---------

class QueryDBInput(BaseModel):
    table: Literal["users", "jobs"] = Field(
        ..., description="Which table to read. Only 'users' and 'jobs' are allowed."
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Exact-match filters. Keys must be column names. "
                    "Example: {'status': 'failed'} or {'id': 'U002'}.",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max rows to return.")


@tool("query_db", args_schema=QueryDBInput)
def query_db_tool(
    table: str, filters: dict[str, Any], limit: int = 10
) -> list[dict]:
    """Query the users or jobs table with exact-match filters.

    Examples:
      table='users', filters={'id': 'U002'}        -> that one user
      table='users', filters={'status': 'suspended'} -> all suspended users
      table='jobs',  filters={'status': 'failed'}   -> all failed jobs
    """
    return db.query_table(table, filters, limit)


# --------- fetch_logs ---------

class FetchLogsInput(BaseModel):
    service: Optional[str] = Field(
        default=None,
        description="Filter by service name (e.g., 'auth-service', 'etl-pipeline').",
    )
    severity: Optional[Literal["INFO", "WARN", "ERROR"]] = Field(
        default=None, description="Filter by severity."
    )
    user_id: Optional[str] = Field(
        default=None, description="Filter by user id (e.g., 'U002')."
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max log entries.")


@tool("fetch_logs", args_schema=FetchLogsInput)
def fetch_logs_tool(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch recent log entries, newest first. Optional filters: service, severity, user_id."""
    return db.fetch_logs(
        service=service, severity=severity, user_id=user_id, limit=limit
    )


# --------- trigger_action ---------

ActionName = Literal[
    "restart_job",
    "reassign_role",
    "reset_password",
    "suspend_user",
    "unsuspend_user",
]


class TriggerActionInput(BaseModel):
    action: ActionName = Field(..., description="Which admin action to simulate.")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters. "
                    "restart_job: {'job_id': 'J001'}. "
                    "reassign_role: {'user_id': 'U002', 'new_role': 'support'}.",
    )


@tool("trigger_action", args_schema=TriggerActionInput)
def trigger_action_tool(action: str, params: dict[str, Any]) -> dict:
    """Simulate execution of an admin action. Does NOT mutate state; returns
    a synthetic result so reasoning can continue deterministically."""
    return {
        "executed": True,
        "action": action,
        "params": params,
        "result": f"Simulated {action} with params {params}",
    }


# --------- retrieve_context ---------

class RetrieveContextInput(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language query.")
    k: int = Field(default=3, ge=1, le=10, description="Top-k docs to return.")


@tool("retrieve_context", args_schema=RetrieveContextInput)
def retrieve_context_tool(query: str, k: int = 3) -> list[dict]:
    """Retrieve RBAC policies and system-doc snippets relevant to the query."""
    docs = rag_retrieve(query, k=k)
    return [{"content": d.page_content, "metadata": d.metadata} for d in docs]


TOOLS = [
    query_db_tool,
    fetch_logs_tool,
    trigger_action_tool,
    retrieve_context_tool,
]
