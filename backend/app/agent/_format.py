"""Shared formatting helpers for sources + trace entries.

Both MockAgentExecutor and OpenAIToolsAgentExecutor consume these so the
API shape is byte-identical across backends.
"""

from typing import Any

_PREVIEW_CAP = 5


def db_sources(table: str, filters: dict, results: Any) -> list[str]:
    """Specific per-row source ids, e.g. 'users_table:U002', 'jobs_table:J001'."""
    if not isinstance(results, list):
        return [f"{table}_table"]

    if table == "users" and filters and filters.get("id"):
        return [f"users_table:{filters['id']}"]
    if table == "jobs" and filters and filters.get("job_id"):
        return [f"jobs_table:{filters['job_id']}"]

    ids: list[str] = []
    for row in results[:5]:
        if not isinstance(row, dict):
            continue
        if table == "users":
            ids.append(f"users_table:{row.get('id','?')}")
        elif table == "jobs":
            ids.append(f"jobs_table:{row.get('job_id','?')}")
    return ids or [f"{table}_table"]


def logs_source(filters: dict) -> str:
    """One source id per fetch_logs call, encoding the filter."""
    parts: list[str] = []
    filters = filters or {}
    if filters.get("user_id"):
        parts.append(f"user={filters['user_id']}")
    if filters.get("service"):
        parts.append(f"svc={filters['service']}")
    if filters.get("severity"):
        parts.append(f"sev={filters['severity']}")
    return f"logs:{'+'.join(parts) if parts else 'all'}"


def rag_source(doc: Any) -> str:
    """Short slugified id: 'rag:rbac:auditor' or 'rag:system:etl-restart'."""
    if not isinstance(doc, dict):
        return "rag:doc"
    meta = doc.get("metadata", {}) or {}
    if meta.get("role"):
        return f"rag:rbac:{meta['role']}"
    if meta.get("service"):
        svc = (meta.get("service") or "").split("-")[0]
        tpc = (meta.get("topic") or "").split()[0] if meta.get("topic") else ""
        slug = "-".join(p for p in (svc, tpc) if p)
        return f"rag:system:{slug}" if slug else "rag:system"
    return "rag:doc"


def _preview_for_tool(tool: str, results: list) -> list[str]:
    """Short identifier list for a tool's returned rows — not full data."""
    preview: list[str] = []
    for r in results[:_PREVIEW_CAP]:
        if not isinstance(r, dict):
            continue
        if tool == "query_db":
            preview.append(str(r.get("id") or r.get("job_id") or "?"))
        elif tool == "fetch_logs":
            sev = r.get("severity", "")
            ts = r.get("timestamp", "")
            preview.append(f"{sev}@{ts}" if (sev and ts) else f"log#{r.get('id','?')}")
        elif tool == "retrieve_context":
            preview.append(rag_source(r))
    return preview


def trace_entry(tool: str, args: dict, observation: Any) -> dict:
    """One row of the structured trace: tool, args, result_count, result_preview."""
    entry: dict = {"tool": tool, "args": args}
    if isinstance(observation, list):
        entry["result_count"] = len(observation)
        preview = _preview_for_tool(tool, observation)
        if preview:
            entry["result_preview"] = preview
    elif isinstance(observation, dict):
        entry["result_count"] = 1
    return entry
