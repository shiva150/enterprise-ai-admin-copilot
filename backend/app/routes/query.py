"""POST /query — invokes the agent and returns the structured response."""

import logging

from fastapi import APIRouter, HTTPException

from app.agent.agent import get_agent
from app.models import QueryRequest, QueryResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest) -> dict:
    try:
        agent = get_agent()
        return agent.invoke({"query": req.query})
    except Exception as e:  # noqa: BLE001 — surface a clean 500 instead of crashing worker
        log.exception("agent.invoke failed for query=%r", req.query)
        raise HTTPException(status_code=500, detail=f"agent failure: {e}") from e
