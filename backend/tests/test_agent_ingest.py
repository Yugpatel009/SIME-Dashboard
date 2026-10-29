"""
©AngelaMos | 2026
test_agent_ingest.py

Tests for Agent heartbeat processing, authenticated log event ingestion,
idempotent deduplication prevention, and backward compatibility.
"""

from unittest.mock import patch
from app.models.Agent import Agent, AgentStatus
from app.models.LogEvent import LogEvent


def test_agent_heartbeat(client, agent_headers: dict[str, str], registered_agent: tuple[Agent, str]) -> None:
    """Verify heartbeat updates agent status, version, and telemetry metrics"""
    agent, _ = registered_agent
    assert agent.status == AgentStatus.OFFLINE

    payload = {
        "agent_version": "1.0.1",
        "metrics": {
            "cpu_percent": 15.5,
            "memory_percent": 42.0,
            "disk_percent": 68.2,
            "queue_depth": 0,
        },
    }

    res = client.post("/v1/agents/heartbeat", headers=agent_headers, json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "acknowledged"

    agent.reload()
    assert agent.agent_version == "1.0.1"
    assert agent.metrics["cpu_percent"] == 15.5
    assert agent.metrics["memory_percent"] == 42.0
    assert agent.metrics["disk_percent"] == 68.2
    assert agent.metrics["queue_depth"] == 0
    assert agent.last_heartbeat_at is not None
    assert agent.status == AgentStatus.ONLINE


@patch("app.controllers.agent_ctrl.publish_event")
def test_agent_event_ingest_and_deduplication(
    mock_publish,
    client,
    agent_headers: dict[str, str],
    registered_agent: tuple[Agent, str],
) -> None:
    """Verify event ingestion, deduplication idempotency, and counters"""
    agent, _ = registered_agent

    event_payload = {
        "event_id": "evt-kali-1001",
        "source_type": "auth",
        "event_type": "login_failure",
        "source_ip": "192.168.56.101",
        "dest_ip": "192.168.56.1",
        "username": "root",
        "message": "Failed password for root from 192.168.56.101 port 54321 ssh2",
    }

    # First ingestion attempt
    res = client.post("/v1/agents/ingest", headers=agent_headers, json=event_payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "created"
    assert data["event_id"] == "evt-kali-1001"
    assert mock_publish.call_count == 1

    agent.reload()
    assert agent.total_events_received == 1
    assert agent.last_event_at is not None

    # Verify record in MongoDB
    saved_event = LogEvent.objects(agent_id=agent.agent_id, event_id="evt-kali-1001").first()
    assert saved_event is not None
    assert saved_event.source_type == "auth"
    assert saved_event.event_type == "login_failure"
    assert saved_event.source_ip == "192.168.56.101"

    # Second ingestion attempt with same event ID (Deduplication Test)
    mock_publish.reset_mock()
    res_dup = client.post("/v1/agents/ingest", headers=agent_headers, json=event_payload)
    assert res_dup.status_code == 200
    data_dup = res_dup.get_json()
    assert data_dup["status"] == "duplicate"
    assert data_dup["event_id"] == "evt-kali-1001"
    # Ensure duplicate does NOT re-publish to Redis stream
    assert mock_publish.call_count == 0

    # Ensure total documents in MongoDB remains 1
    assert LogEvent.objects(agent_id=agent.agent_id).count() == 1


def test_agent_event_ingest_invalid_schema_rejected(client, agent_headers: dict[str, str]) -> None:
    """Verify invalid port number is rejected with 422"""
    res = client.post(
        "/v1/agents/ingest",
        headers=agent_headers,
        json={"source_port": 999999},  # exceeds 65535 limit
    )
    assert res.status_code == 422


@patch("app.controllers.log_ctrl.publish_event")
def test_legacy_log_ingest_backward_compatibility(
    mock_publish,
    client,
    agent_headers: dict[str, str],
    registered_agent: tuple[Agent, str],
) -> None:
    """Verify legacy /v1/logs/ingest works and binds agent_id if agent token is supplied"""
    agent, _ = registered_agent

    legacy_payload = {
        "source_type": "auth",
        "event_type": "login_failure",
        "source_ip": "10.0.0.99",
        "username": "testuser",
        "message": "SSH login failure",
    }

    # Ingestion without agent token
    res_public = client.post("/v1/logs/ingest", json=legacy_payload)
    assert res_public.status_code == 201

    # Ingestion with agent token
    res_agent = client.post("/v1/logs/ingest", headers=agent_headers, json=legacy_payload)
    assert res_agent.status_code == 201
    data_agent = res_agent.get_json()
    assert "id" in data_agent

    # Verify agent_id was populated on the created LogEvent
    created_id = data_agent["id"]
    event = LogEvent.objects(id=created_id).first()
    assert event is not None
    assert event.agent_id == agent.agent_id
