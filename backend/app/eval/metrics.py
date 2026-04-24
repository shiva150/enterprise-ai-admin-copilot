"""Per-response evaluation metrics.

These are cheap structural scores computed on *every* response (dev + prod)
and embedded into `response['metrics']`. They are intentionally simple — a
deeper LLM-as-judge / golden-fixture harness lives behind a dedicated
CI-only eval runner (see docs/PRD.md §6).

All scores are floats in [0.0, 1.0]. Aggregated across the fixture set
they yield the headline numbers reported in README.md.
"""

from typing import Any


def evaluate_response(response: dict[str, Any]) -> dict[str, float]:
    """Score a QueryResponse-shaped dict on three cheap structural signals.

    - tool_correctness:  did the agent call any tools at all?
                         (a tool-using agent that answers without calling
                         anything is degenerate — it either guessed or
                         hit the canned fallback.)
    - grounding_score:   how many distinct data planes were cited?
                         0 sources → 0.0, 1 plane → 0.6, ≥2 planes → 1.0.
    - hallucination_risk: inverse of grounding. 0.0 when sources exist.
    """
    trace = response.get("trace") or []
    sources = response.get("sources") or []

    tool_correctness = 1.0 if len(trace) > 0 else 0.0

    # A "plane" is the prefix of a source id — e.g. 'users_table', 'logs',
    # 'jobs_table', 'rag'. Counting distinct planes captures corroboration
    # better than raw source count.
    planes: set[str] = set()
    for s in sources:
        if isinstance(s, str):
            planes.add(s.split(":", 1)[0])

    if len(planes) >= 2:
        grounding_score = 1.0
    elif len(planes) == 1:
        grounding_score = 0.6
    else:
        grounding_score = 0.0

    hallucination_risk = 0.0 if sources else 1.0

    return {
        "tool_correctness": tool_correctness,
        "grounding_score": grounding_score,
        "hallucination_risk": hallucination_risk,
    }
