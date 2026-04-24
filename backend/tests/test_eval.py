"""Unit tests for app/eval/metrics.py and its integration into the agent."""

import pytest

from app.agent.agent import get_agent
from app.db.seed import seed
from app.eval.metrics import evaluate_response
from app.rag.ingest import load_mock_docs
from app.rag.store import build_index


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    seed(reset=True)
    build_index(load_mock_docs())
    get_agent.cache_clear()
    yield


# ---------- unit: evaluate_response ----------

def test_eval_rewards_multi_plane_grounding():
    resp = {
        "answer": "…",
        "trace": [{"tool": "query_db"}, {"tool": "fetch_logs"}],
        "sources": ["users_table:U002", "logs:user=U002"],
    }
    m = evaluate_response(resp)
    assert m["tool_correctness"] == 1.0
    assert m["grounding_score"] == 1.0  # 2 distinct planes
    assert m["hallucination_risk"] == 0.0


def test_eval_partial_grounding_single_plane():
    resp = {
        "trace": [{"tool": "query_db"}],
        "sources": ["users_table:U002"],
    }
    m = evaluate_response(resp)
    assert m["grounding_score"] == 0.6  # one plane only


def test_eval_flags_ungrounded_response():
    resp = {
        "trace": [],
        "sources": [],
        "answer": "Plausible-sounding but unsupported claim.",
    }
    m = evaluate_response(resp)
    assert m["tool_correctness"] == 0.0
    assert m["grounding_score"] == 0.0
    assert m["hallucination_risk"] == 1.0


def test_eval_handles_missing_keys_gracefully():
    m = evaluate_response({})
    assert set(m.keys()) == {"tool_correctness", "grounding_score", "hallucination_risk"}
    assert m["tool_correctness"] == 0.0


# ---------- integration: metrics land on agent responses ----------

def test_agent_response_carries_eval_scores():
    agent = get_agent()
    res = agent.invoke({"query": "Why did user U002 lose access?"})
    m = res["metrics"]
    # Original metrics still present
    assert "latency_ms" in m
    assert "tools_called" in m
    # New eval metrics attached
    assert "tool_correctness" in m
    assert "grounding_score" in m
    assert "hallucination_risk" in m
    # A grounded response scores well
    assert m["tool_correctness"] == 1.0
    assert m["grounding_score"] >= 0.6
    assert m["hallucination_risk"] == 0.0


def test_agent_unknown_query_scores_low_grounding():
    """A fully unresolved query falls back to RAG only; hallucination risk
    stays low because at least the RAG plane is cited, but tool_correctness
    and grounding reflect the weaker signal."""
    agent = get_agent()
    res = agent.invoke({"query": "tell me about the weather"})
    m = res["metrics"]
    assert m["tool_correctness"] == 1.0  # retrieve_context was called
    # Only one plane (rag) — partial grounding, not full.
    assert m["grounding_score"] in (0.0, 0.6)
