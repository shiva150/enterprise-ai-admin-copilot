"""POST /ingest/log — append a log entry to the live DB.

Reuses the same `logs` table that `fetch_logs_tool` queries, so newly
ingested entries are immediately visible to the agent on the next query.
This is the bridge between synthetic seed data and real-world log streams.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.db import queries as db
from app.models import LogIngestRequest, LogIngestResponse

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest/log", response_model=LogIngestResponse)
def ingest_log(req: LogIngestRequest) -> LogIngestResponse:
    conn = db.get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO logs (timestamp, service, user_id, message, severity) "
            "VALUES (?, ?, ?, ?, ?)",
            (req.timestamp, req.service, req.user_id, req.message, req.severity),
        )
        conn.commit()
        log_id = cursor.lastrowid
    except Exception as e:  # noqa: BLE001 — surface any schema/constraint failure as 400
        log.exception("ingest_log failed for %r", req.model_dump())
        raise HTTPException(status_code=400, detail=f"ingest failure: {e}") from e
    finally:
        conn.close()

    return LogIngestResponse(id=log_id, status="ingested")
