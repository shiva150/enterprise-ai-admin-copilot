"""Data-access functions for users/jobs/logs.

Module-level DB_PATH is intentionally readable-by-reference so tests can
monkey-patch `app.db.queries.DB_PATH` to a tmp file without touching callers.
"""

import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH: Path = (
    Path(__file__).resolve().parent.parent.parent / "data" / "mock.db"
)

_ALLOWED_TABLES: set[str] = {"users", "jobs"}
_MAX_QUERY_LIMIT = 50
_MAX_LOG_LIMIT = 100


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _check_col_name(col: str) -> None:
    if not col.replace("_", "").isalnum():
        raise ValueError(f"Invalid column name: {col!r}")


def query_table(
    table: str, filters: Optional[dict[str, Any]] = None, limit: int = 10
) -> list[dict]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(
            f"table must be one of {sorted(_ALLOWED_TABLES)}, got: {table!r}"
        )
    limit = max(1, min(int(limit), _MAX_QUERY_LIMIT))

    conditions: list[str] = []
    params: list[Any] = []
    for col, val in (filters or {}).items():
        _check_col_name(col)
        conditions.append(f"{col} = ?")
        params.append(val)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM {table} {where} LIMIT ?"
    params.append(limit)

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def fetch_logs(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    limit = max(1, min(int(limit), _MAX_LOG_LIMIT))

    conditions: list[str] = []
    params: list[Any] = []
    if service is not None:
        conditions.append("service = ?")
        params.append(service)
    if severity is not None:
        conditions.append("severity = ?")
        params.append(severity)
    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
