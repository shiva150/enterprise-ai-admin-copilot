"""Agent factory. Single entry point: `get_agent()` returns an object with
`.invoke({"query": "..."}) -> dict` regardless of which backend is active.

Both backends emit the same dict shape so the FastAPI layer and the React
frontend never need to know whether they are talking to the mock or to
real Gemini. Flipping USE_MOCK_LLM in .env is the only change.

Response shape (see app.models.QueryResponse for the pydantic schema):
    {
      "answer": str,
      "reasoning": str,
      "sources": list[str],
      "trace": list[dict],
      "suggested_action": dict | None,   # {"action": str, "params": dict}
      "executed": False,                  # execution happens via /action
      "metrics": dict,                    # {"latency_ms": int, "tools_called": int}
    }
"""

import time
from functools import lru_cache
from typing import Protocol


class AgentExecutor(Protocol):
    def invoke(self, inputs: dict) -> dict: ...


class _TimedAgent:
    """Wraps an agent to stamp per-invocation latency and tool-call count.
    Kept as a separate layer so both mock and real backends get metrics for free."""

    def __init__(self, inner: AgentExecutor) -> None:
        self._inner = inner

    def invoke(self, inputs: dict) -> dict:
        from app.eval.metrics import evaluate_response

        start = time.perf_counter()
        result = self._inner.invoke(inputs)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        if isinstance(result, dict):
            metrics = result.get("metrics") or {}
            metrics["latency_ms"] = elapsed_ms
            metrics["tools_called"] = len(result.get("trace") or [])
            metrics.update(evaluate_response(result))
            result["metrics"] = metrics
        return result


@lru_cache(maxsize=1)
def get_agent() -> AgentExecutor:
    """Returns a cached agent instance. Safe to call on every request —
    construction happens at most once per process."""
    from app.config import settings

    if settings.use_mock_llm:
        from app.agent.mock_agent import MockAgentExecutor
        from app.agent.tools import TOOLS

        return _TimedAgent(MockAgentExecutor(TOOLS))

    from app.agent.gemini_agent import GeminiAgentExecutor
    from app.agent.tools import TOOLS

    return _TimedAgent(GeminiAgentExecutor(TOOLS))
