"""Tests for POST /ingest/log — the live-log ingestion surface.

Verifies the end-to-end contract: a POSTed log row is immediately visible
to fetch_logs (so the agent sees it on the next /query).
"""

import pytest
from fastapi.testclient import TestClient

from app.agent.tools import fetch_logs_tool
from app.db.seed import seed
from app.main import app


@pytest.fixture(scope="module", autouse=True)
def _seeded():
    seed(reset=True)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_ingest_log_happy_path(client):
    r = client.post(
        "/ingest/log",
        json={
            "timestamp": "2026-04-24T12:00:00",
            "service": "notification-service",
            "user_id": "U003",
            "message": "Digest email bounced: invalid recipient",
            "severity": "ERROR",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ingested"
    assert isinstance(data["id"], int) and data["id"] > 0


def test_ingested_log_is_visible_to_fetch_logs(client):
    """This is the point of the endpoint: the agent sees real logs on next read."""
    r = client.post(
        "/ingest/log",
        json={
            "timestamp": "2026-04-24T12:05:00",
            "service": "notification-service",
            "user_id": "U003",
            "message": "Digest email bounced a second time: invalid recipient",
            "severity": "ERROR",
        },
    )
    assert r.status_code == 200

    # fetch_logs_tool hits the same SQLite table.
    logs = fetch_logs_tool.invoke({"user_id": "U003", "limit": 20})
    messages = [l["message"] for l in logs]
    assert any("Digest email bounced a second time" in m for m in messages)


def test_ingest_rejects_unknown_severity(client):
    r = client.post(
        "/ingest/log",
        json={
            "timestamp": "2026-04-24T12:00:00",
            "service": "auth-service",
            "message": "hi",
            "severity": "FATAL",  # not in Literal[INFO,WARN,ERROR]
        },
    )
    assert r.status_code == 422


def test_ingest_rejects_missing_required_fields(client):
    r = client.post(
        "/ingest/log",
        json={"service": "auth-service", "severity": "INFO"},  # missing timestamp + message
    )
    assert r.status_code == 422


def test_ingest_allows_null_user_id(client):
    r = client.post(
        "/ingest/log",
        json={
            "timestamp": "2026-04-24T12:10:00",
            "service": "etl-pipeline",
            "message": "system-level event, no user",
            "severity": "INFO",
        },
    )
    assert r.status_code == 200
