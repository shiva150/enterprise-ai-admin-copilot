import pytest

from app.agent.tools import (
    fetch_logs_tool,
    query_db_tool,
    retrieve_context_tool,
    trigger_action_tool,
)
from app.db.seed import seed
from app.rag.ingest import load_mock_docs
from app.rag.store import build_index


@pytest.fixture(scope="module", autouse=True)
def _seeded_state():
    seed(reset=True)
    build_index(load_mock_docs())
    yield


# -------- query_db --------

def test_query_db_lists_all_users():
    rows = query_db_tool.invoke({"table": "users", "filters": {}, "limit": 50})
    assert len(rows) == 10
    ids = {r["id"] for r in rows}
    assert {"U001", "U002", "U003", "U004", "U005"} <= ids


def test_query_db_filters_single_user():
    rows = query_db_tool.invoke({"table": "users", "filters": {"id": "U002"}, "limit": 10})
    assert len(rows) == 1
    assert rows[0]["status"] == "suspended"
    assert rows[0]["role"] == "intern"


def test_query_db_filters_failed_jobs():
    rows = query_db_tool.invoke({"table": "jobs", "filters": {"status": "failed"}, "limit": 50})
    # J001, J004, J007, J010 are seeded as failed; assert the known set is present
    assert {"J001", "J004", "J007", "J010"} <= {r["job_id"] for r in rows}
    assert all(r["status"] == "failed" for r in rows)


def test_query_db_rejects_unknown_table():
    # pydantic Literal rejects anything not in {'users','jobs'}
    with pytest.raises(Exception):
        query_db_tool.invoke({"table": "secrets", "filters": {}, "limit": 10})


# -------- fetch_logs --------

def test_fetch_logs_by_service():
    logs = fetch_logs_tool.invoke({"service": "etl-pipeline", "limit": 20})
    assert len(logs) == 4
    assert all(l["service"] == "etl-pipeline" for l in logs)


def test_fetch_logs_orders_newest_first():
    logs = fetch_logs_tool.invoke({"service": "etl-pipeline", "limit": 20})
    timestamps = [l["timestamp"] for l in logs]
    assert timestamps == sorted(timestamps, reverse=True)


def test_fetch_logs_by_user():
    logs = fetch_logs_tool.invoke({"user_id": "U002", "limit": 20})
    # U002 has: 1 suspended WARN + 2 login-denied ERROR + 1 access-denied WARN = 4
    assert len(logs) == 4
    assert all(l["user_id"] == "U002" for l in logs)


def test_fetch_logs_errors_only():
    logs = fetch_logs_tool.invoke({"severity": "ERROR", "limit": 20})
    assert all(l["severity"] == "ERROR" for l in logs)
    # Expect at least the 2 login denials + 2 ETL failures
    assert len(logs) >= 4


def test_fetch_logs_combined_filters():
    logs = fetch_logs_tool.invoke(
        {"service": "auth-service", "severity": "ERROR", "limit": 20}
    )
    assert all(l["service"] == "auth-service" and l["severity"] == "ERROR" for l in logs)


# -------- trigger_action --------

def test_trigger_action_returns_simulated_result():
    out = trigger_action_tool.invoke(
        {"action": "restart_job", "params": {"job_id": "J001"}}
    )
    assert out["executed"] is True
    assert out["action"] == "restart_job"
    assert out["params"] == {"job_id": "J001"}
    assert "Simulated" in out["result"]


def test_trigger_action_rejects_unknown_action():
    with pytest.raises(Exception):
        trigger_action_tool.invoke({"action": "delete_everything", "params": {}})


def test_trigger_action_does_not_mutate_db():
    before = query_db_tool.invoke({"table": "jobs", "filters": {"job_id": "J001"}, "limit": 1})
    trigger_action_tool.invoke({"action": "restart_job", "params": {"job_id": "J001"}})
    after = query_db_tool.invoke({"table": "jobs", "filters": {"job_id": "J001"}, "limit": 1})
    assert before == after


# -------- retrieve_context --------

def test_retrieve_context_returns_docs_with_metadata():
    out = retrieve_context_tool.invoke({"query": "auditor", "k": 1})
    assert len(out) == 1
    assert "content" in out[0]
    assert "metadata" in out[0]
    assert out[0]["metadata"].get("role") == "auditor"
