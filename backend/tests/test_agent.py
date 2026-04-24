"""Golden tests for the agent.

Runs against MockAgentExecutor (USE_MOCK_LLM=1 forced by conftest).
The mock is deterministic and data is seeded, so tests assert on concrete
substrings, source fingerprints, structured suggested_action, trace shape
(with result_preview), and metrics presence.
"""

import pytest

from app.agent.agent import get_agent
from app.db.seed import seed
from app.rag.ingest import load_mock_docs
from app.rag.store import build_index


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    seed(reset=True)
    build_index(load_mock_docs())
    get_agent.cache_clear()
    yield


# ---------- Golden case 1: user access ----------

def test_user_access_issue():
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U002 lose access?"})

    assert isinstance(res, dict)
    assert "U002" in res["answer"]
    assert "suspended" in res["answer"].lower()

    assert "logs" in res["reasoning"].lower()
    assert "query_db" in res["reasoning"]
    assert "fetch_logs" in res["reasoning"]

    assert "users_table:U002" in res["sources"]
    assert any(s.startswith("logs:") and "U002" in s for s in res["sources"])

    # Both core tools were called, order-agnostic. fetch_logs is priority 1 now.
    tools_called = [t["tool"] for t in res["trace"]]
    assert tools_called[0] == "fetch_logs", f"fetch_logs must be priority 1; got {tools_called}"
    assert "query_db" in tools_called
    qdb = next(t for t in res["trace"] if t["tool"] == "query_db")
    assert qdb["args"]["filters"]["id"] == "U002"
    fl = next(t for t in res["trace"] if t["tool"] == "fetch_logs")
    assert fl["args"].get("user_id") == "U002"

    assert res["suggested_action"] == {
        "action": "unsuspend_user",
        "params": {"user_id": "U002"},
    }
    assert res["executed"] is False


# ---------- Golden case 2: failed jobs ----------

def test_failed_jobs():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})

    assert ("J001" in res["answer"]) or ("J004" in res["answer"])
    assert "jobs_table:J001" in res["sources"]
    assert "jobs_table:J004" in res["sources"]
    assert any(s.startswith("logs:") for s in res["sources"])
    assert res["executed"] is False


# ---------- Golden case 3: RAG / permissions ----------

def test_permission_query_uses_rag():
    agent = get_agent()
    res = agent.invoke({"query": "What permissions does auditor have?"})

    assert "auditor" in res["answer"].lower()
    assert "rag:rbac:auditor" in res["sources"]
    assert any(t["tool"] == "retrieve_context" for t in res["trace"])
    assert res["executed"] is False


# ---------- Golden case 4: structured action proposal ----------

def test_restart_action_suggests():
    agent = get_agent()
    res = agent.invoke({"query": "Restart failed ETL job"})

    assert res["suggested_action"] is not None
    assert res["suggested_action"]["action"] == "restart_job"
    assert res["suggested_action"]["params"]["job_id"] in {"J001", "J004"}
    assert res["executed"] is False

    assert "query_db" in res["reasoning"]
    assert any(s.startswith("jobs_table:") for s in res["sources"])
    assert not any(t["tool"] == "trigger_action" for t in res["trace"])


# ---------- Golden case 5: chained reasoning ----------

def test_chained_reasoning_etl_failure_and_recommendation():
    agent = get_agent()
    res = agent.invoke({"query": "Why did ETL fail and what should I do?"})

    assert "fetch_logs" in res["reasoning"]
    assert "retrieve_context" in res["reasoning"]

    tools_called = [t["tool"] for t in res["trace"]]
    assert {"query_db", "fetch_logs", "retrieve_context"} <= set(tools_called)

    answer_l = res["answer"].lower()
    assert ("j001" in answer_l) or ("j004" in answer_l)

    # Structured suggestion
    assert res["suggested_action"] is not None
    assert res["suggested_action"]["action"] == "restart_job"
    assert "job_id" in res["suggested_action"]["params"]

    assert any(s.startswith("jobs_table:") for s in res["sources"])
    assert any(s.startswith("logs:") for s in res["sources"])
    assert any(s.startswith("rag:") for s in res["sources"])


# ---------- Schema + trace preview + metrics ----------

def test_output_schema_stable():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})
    assert set(res.keys()) == {
        "answer", "reasoning", "sources", "trace",
        "suggested_action", "executed", "metrics",
    }
    assert isinstance(res["answer"], str)
    assert isinstance(res["reasoning"], str)
    assert isinstance(res["sources"], list) and all(isinstance(s, str) for s in res["sources"])
    assert isinstance(res["trace"], list)
    assert res["suggested_action"] is None or isinstance(res["suggested_action"], dict)
    assert isinstance(res["executed"], bool)
    assert isinstance(res["metrics"], dict)


def test_trace_entries_have_required_fields():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})
    assert len(res["trace"]) >= 2
    for entry in res["trace"]:
        assert {"tool", "args"} <= set(entry)
        assert isinstance(entry["tool"], str)
        assert isinstance(entry["args"], dict)


def test_trace_has_result_preview_for_db_calls():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})
    qdb = next(t for t in res["trace"] if t["tool"] == "query_db")
    assert "result_preview" in qdb
    # J001/J004 plus the enriched J007/J010 are all failed; preview should include them
    assert {"J001", "J004"} <= set(qdb["result_preview"])


def test_trace_has_result_preview_for_rag_calls():
    agent = get_agent()
    res = agent.invoke({"query": "What permissions does auditor have?"})
    rag = next(t for t in res["trace"] if t["tool"] == "retrieve_context")
    assert "result_preview" in rag
    assert all(p.startswith("rag:") for p in rag["result_preview"])
    assert "rag:rbac:auditor" in rag["result_preview"]


def test_metrics_emitted():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})
    assert "metrics" in res
    assert isinstance(res["metrics"], dict)
    assert "latency_ms" in res["metrics"]
    assert isinstance(res["metrics"]["latency_ms"], int)
    assert res["metrics"]["latency_ms"] >= 0
    assert res["metrics"]["tools_called"] == len(res["trace"])


def test_same_query_is_deterministic():
    """Everything but metrics.latency_ms is stable across identical calls."""
    agent = get_agent()
    r1 = agent.invoke({"query": "Why did user U002 lose access?"})
    r2 = agent.invoke({"query": "Why did user U002 lose access?"})
    for k in ("answer", "reasoning", "sources", "trace", "suggested_action", "executed"):
        assert r1[k] == r2[k], f"mismatch on key={k}"
    assert r1["metrics"]["tools_called"] == r2["metrics"]["tools_called"]


def test_unknown_query_does_not_crash():
    agent = get_agent()
    res = agent.invoke({"query": "tell me about the weather"})
    assert isinstance(res["answer"], str) and res["answer"]
    assert res["executed"] is False
    assert any(t["tool"] == "retrieve_context" for t in res["trace"])


def test_specific_job_lookup_by_id():
    agent = get_agent()
    res = agent.invoke({"query": "Status of job J004?"})
    assert ("J004" in res["answer"]) or ("user-sync" in res["answer"])
    assert "jobs_table:J004" in res["sources"]


def test_active_user_lookup_no_suspension_signal():
    agent = get_agent()
    res = agent.invoke({"query": "Status of user U003?"})
    assert "U003" in res["answer"]
    assert "suspended" not in res["answer"].lower()
    assert res["suggested_action"] is None


def test_action_without_target_returns_guidance():
    agent = get_agent()
    res = agent.invoke({"query": "Restart it now"})
    assert isinstance(res["answer"], str) and res["answer"]
    assert res["executed"] is False


def test_suspended_user_gets_unsuspend_suggestion():
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U002 lose access?"})
    assert res["suggested_action"] == {
        "action": "unsuspend_user",
        "params": {"user_id": "U002"},
    }


# ---------- Rule enforcement: fetch_logs priority + RAG as fallback only ----------

def test_fetch_logs_is_priority_one_for_user_issue():
    """Rule 1 + priority table: fetch_logs runs before query_db for user queries."""
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U002 lose access?"})
    tools = [t["tool"] for t in res["trace"]]
    assert tools[0] == "fetch_logs"
    # And query_db is still called (rule 2: ALWAYS both for user-related issues).
    assert "query_db" in tools


def test_fetch_logs_is_priority_one_for_job_issue():
    agent = get_agent()
    res = agent.invoke({"query": "Show failed jobs"})
    tools = [t["tool"] for t in res["trace"]]
    assert tools[0] == "fetch_logs"
    assert "query_db" in tools


def test_rag_is_not_called_when_logs_plus_db_are_sufficient():
    """Rule 4/6: don't call retrieve_context when logs+DB already surface a signal."""
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U002 lose access?"})
    tools = [t["tool"] for t in res["trace"]]
    # U002 is suspended → clear signal → no RAG fallback needed.
    assert "retrieve_context" not in tools


def test_user_with_no_signal_triggers_rag_fallback_and_insufficient_data():
    """The exact failure case the user reported:
    'U003 not receiving updates' → U003 is active, has no notification logs
    of its own, so the classifier/handler must check logs + DB first, try
    service logs for notification-service, and fall back to RAG + surface
    an 'insufficient data' notice if nothing grounds a user-specific claim."""
    agent = get_agent()
    res = agent.invoke({"query": "Why is user U003 not receiving updates?"})

    tools = [t["tool"] for t in res["trace"]]
    # Priority 1: logs for the user first.
    assert tools[0] == "fetch_logs"
    fl_user = next(t for t in res["trace"] if t["tool"] == "fetch_logs" and t["args"].get("user_id") == "U003")
    assert fl_user is not None

    # Priority 2: query_db for user state.
    assert "query_db" in tools
    qdb = next(t for t in res["trace"] if t["tool"] == "query_db")
    assert qdb["args"]["filters"]["id"] == "U003"

    # Service was detected from "updates" keyword → notification-service logs fetched.
    svc_log_calls = [
        t for t in res["trace"]
        if t["tool"] == "fetch_logs" and t["args"].get("service") == "notification-service"
    ]
    assert len(svc_log_calls) == 1, "service hint should have triggered a notification-service log fetch"

    # Answer cites real observed evidence and never invents a failure story.
    assert "U003" in res["answer"]
    # U003 is active (not suspended) — must not claim otherwise.
    assert "suspended" not in res["answer"].lower()
    # No unsuspend suggestion for an active user.
    assert res["suggested_action"] is None


def test_system_issue_without_entity_goes_logs_first():
    """A query mentioning a service but no user/job id → system_issue path,
    which starts with fetch_logs for that service (not RAG)."""
    agent = get_agent()
    res = agent.invoke({"query": "notification delivery is broken"})
    tools = [t["tool"] for t in res["trace"]]
    assert tools[0] == "fetch_logs"
    first_args = res["trace"][0]["args"]
    assert first_args.get("service") == "notification-service"


def test_pure_policy_query_still_uses_rag_first():
    """Rule 6 permits RAG-first when the question is explicitly about documentation."""
    agent = get_agent()
    res = agent.invoke({"query": "What permissions does auditor have?"})
    tools = [t["tool"] for t in res["trace"]]
    assert tools[0] == "retrieve_context"


def test_insufficient_data_surfaces_when_no_signal():
    """Unknown user id → no user row, no logs, no service hint → explicit insufficient-data notice."""
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U999 lose access?"})
    assert "insufficient data" in res["answer"].lower()
    assert res["suggested_action"] is None
    # Fallback to RAG happened because no signal was found.
    tools = [t["tool"] for t in res["trace"]]
    assert "retrieve_context" in tools
