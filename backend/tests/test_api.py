"""End-to-end API tests via TestClient — exercises FastAPI routes, pydantic
validation, and response serialization. Covers both /query and /action.
"""

import pytest
from fastapi.testclient import TestClient

from app.agent.agent import get_agent
from app.db.seed import seed
from app.main import app
from app.rag.ingest import load_mock_docs
from app.rag.store import build_index


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    seed(reset=True)
    build_index(load_mock_docs())
    # Clear cached agent so it picks up the patched (test) DB / index paths
    get_agent.cache_clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------- /health ----------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mock_llm"] is True


# ---------- /query: happy paths ----------

def test_query_user_access(client):
    r = client.post("/query", json={"query": "Why did user U002 lose access?"})
    assert r.status_code == 200
    data = r.json()
    assert "U002" in data["answer"]
    assert "suspended" in data["answer"].lower()
    assert data["executed"] is False
    assert "users_table:U002" in data["sources"]
    assert data["suggested_action"] == {
        "action": "unsuspend_user",
        "params": {"user_id": "U002"},
    }
    # Full response shape
    assert set(data.keys()) == {
        "answer", "reasoning", "sources", "trace",
        "suggested_action", "executed", "metrics",
    }
    # Metrics present
    assert "latency_ms" in data["metrics"]
    assert data["metrics"]["tools_called"] == len(data["trace"])


def test_query_failed_jobs(client):
    r = client.post("/query", json={"query": "Show failed jobs"})
    assert r.status_code == 200
    data = r.json()
    assert ("J001" in data["answer"]) or ("J004" in data["answer"])
    assert any(s.startswith("jobs_table:") for s in data["sources"])


def test_query_chained_etl(client):
    r = client.post("/query", json={"query": "Why did ETL fail and what should I do?"})
    assert r.status_code == 200
    data = r.json()
    tools = [t["tool"] for t in data["trace"]]
    assert {"query_db", "fetch_logs", "retrieve_context"} <= set(tools)
    assert data["suggested_action"] is not None
    assert data["suggested_action"]["action"] == "restart_job"
    assert "job_id" in data["suggested_action"]["params"]


# ---------- /query: validation ----------

def test_query_rejects_empty_string(client):
    r = client.post("/query", json={"query": ""})
    assert r.status_code == 422


def test_query_rejects_missing_field(client):
    r = client.post("/query", json={})
    assert r.status_code == 422


def test_query_rejects_oversized(client):
    r = client.post("/query", json={"query": "x" * 3000})
    assert r.status_code == 422


# ---------- /action: happy paths ----------

def test_action_restart_job(client):
    r = client.post(
        "/action",
        json={"action": "restart_job", "params": {"job_id": "J001"}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["action"] == "restart_job"
    assert data["executed"] is True
    assert data["result"]["params"] == {"job_id": "J001"}
    assert "Simulated" in data["result"]["result"]


def test_action_reassign_role(client):
    r = client.post(
        "/action",
        json={
            "action": "reassign_role",
            "params": {"user_id": "U002", "new_role": "support"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["executed"] is True
    assert data["result"]["params"] == {"user_id": "U002", "new_role": "support"}


def test_action_reset_password(client):
    r = client.post(
        "/action",
        json={"action": "reset_password", "params": {"user_id": "U002"}},
    )
    assert r.status_code == 200
    assert r.json()["executed"] is True


# ---------- /action: validation ----------

def test_action_rejects_unknown(client):
    r = client.post(
        "/action",
        json={"action": "delete_everything", "params": {}},
    )
    assert r.status_code == 422


def test_action_rejects_missing_action(client):
    r = client.post("/action", json={"params": {}})
    assert r.status_code == 422


# ---------- End-to-end chain: /query -> /action ----------

def test_query_then_execute_suggested_action(client):
    """Happy-path demo flow: /query returns a structured suggestion that is
    already shaped like /action's request body — the UI forwards it as-is."""
    q = client.post("/query", json={"query": "Restart failed ETL job"})
    assert q.status_code == 200
    suggested = q.json()["suggested_action"]
    assert suggested and suggested["action"] == "restart_job"

    # No parsing — suggested_action is the /action body.
    a = client.post("/action", json=suggested)
    assert a.status_code == 200
    data = a.json()
    assert data["action"] == "restart_job"
    assert data["executed"] is True
    assert data["result"]["params"]["job_id"] == suggested["params"]["job_id"]
