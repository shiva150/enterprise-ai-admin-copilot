"""POST /action — executes (simulates) an admin action via trigger_action_tool.

This is the *only* path where actions are "executed" — the agent only ever
proposes. The UI collects operator confirmation and calls this endpoint.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.agent.tools import trigger_action_tool
from app.models import ActionRequest, ActionResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/action", response_model=ActionResponse)
def action_endpoint(req: ActionRequest) -> ActionResponse:
    try:
        result = trigger_action_tool.invoke(
            {"action": req.action, "params": req.params}
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid action: {e.errors()}") from e
    except Exception as e:  # noqa: BLE001
        log.exception("trigger_action failed for action=%r params=%r", req.action, req.params)
        raise HTTPException(status_code=400, detail=f"action failure: {e}") from e

    return ActionResponse(
        action=req.action,
        executed=bool(result.get("executed", False)),
        result=result,
    )
