"""
©AngelaMos | 2026
test_agent_crud.py

Tests for Agent management CRUD APIs, role-based authorization,
pagination, filtering, status derivation, and credential rotation.
"""

from datetime import datetime, timedelta, UTC
from app.models.Agent import Agent, AgentStatus


def test_register_agent_unauthenticated(client) -> None:
    """Verify registration requires user authentication"""
    res = client.post(
        "/v1/agents/register",
        json={"name": "test-agent", "hostname": "host-1"},
    )
    assert res.status_code == 401


def test_register_agent_analyst_forbidden(client, analyst_headers: dict[str, str]) -> None:
    """Verify only admin users can register new agents"""
    res = client.post(
        "/v1/agents/register",
        headers=analyst_headers,
        json={"name": "test-agent", "hostname": "host-1"},
    )
    assert res.status_code == 403


def test_register_agent_admin_success(client, admin_headers: dict[str, str]) -> None:
    """Verify admin can register agent and receive one-time bearer token"""
    res = client.post(
        "/v1/agents/register",
        headers=admin_headers,
        json={
            "name": "Production Kali Ingestion",
            "hostname": "kali-primary",
            "os_type": "Kali Linux 2024.1",
            "agent_version": "1.0.0",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert "agent" in data
    assert "token" in data
    assert data["token"].startswith("siem_agt_")

    agent_id = data["agent"]["agent_id"]
    agent = Agent.find_by_agent_id(agent_id)
    assert agent is not None
    assert agent.hostname == "kali-primary"
    # Verify plaintext token is never stored in DB
    assert agent.token_hash is not None
    assert "token" not in agent.to_mongo()


def test_list_agents_and_filtering(client, admin_headers: dict[str, str]) -> None:
    """Verify agent list endpoint with pagination and filtering"""
    # Create test agents
    Agent.create_agent(name="agt-alpha", hostname="host-alpha", os_type="linux")
    Agent.create_agent(name="agt-beta", hostname="host-beta", os_type="windows")

    # List all
    res = client.get("/v1/agents", headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Filter by search
    res_filtered = client.get("/v1/agents?search=host-beta", headers=admin_headers)
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.get_json()
    assert data_filtered["total"] == 1
    assert data_filtered["items"][0]["hostname"] == "host-beta"


def test_get_agent_details(client, admin_headers: dict[str, str], registered_agent: tuple[Agent, str]) -> None:
    """Verify getting single agent details and 404 for missing agent"""
    agent, _ = registered_agent

    res = client.get(f"/v1/agents/{agent.agent_id}", headers=admin_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["agent_id"] == agent.agent_id
    assert data["hostname"] == "kali-vm"

    # Non-existent agent
    res_404 = client.get("/v1/agents/agt_nonexistent123", headers=admin_headers)
    assert res_404.status_code == 404


def test_update_agent_metadata(client, admin_headers: dict[str, str], registered_agent: tuple[Agent, str]) -> None:
    """Verify updating agent metadata"""
    agent, _ = registered_agent

    res = client.patch(
        f"/v1/agents/{agent.agent_id}",
        headers=admin_headers,
        json={"name": "Updated Agent Name", "hostname": "kali-qa"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["name"] == "Updated Agent Name"
    assert data["hostname"] == "kali-qa"


def test_revoke_agent_and_rotate_token(client, admin_headers: dict[str, str], registered_agent: tuple[Agent, str]) -> None:
    """Verify revocation and token rotation endpoints"""
    agent, old_token = registered_agent

    # Revoke agent
    res_revoke = client.post(f"/v1/agents/{agent.agent_id}/revoke", headers=admin_headers)
    assert res_revoke.status_code == 200
    data_revoke = res_revoke.get_json()
    assert data_revoke["is_revoked"] is True
    assert data_revoke["status"] == "revoked"

    # Rotate token (un-revokes and issues new credential)
    res_rotate = client.post(f"/v1/agents/{agent.agent_id}/rotate-token", headers=admin_headers)
    assert res_rotate.status_code == 200
    data_rotate = res_rotate.get_json()
    new_token = data_rotate["token"]
    assert new_token != old_token
    assert new_token.startswith("siem_agt_")

    agent.reload()
    assert agent.is_revoked is False
    assert agent.verify_token(new_token) is True


def test_delete_agent(client, admin_headers: dict[str, str], registered_agent: tuple[Agent, str]) -> None:
    """Verify deleting an agent"""
    agent, _ = registered_agent

    res = client.delete(f"/v1/agents/{agent.agent_id}", headers=admin_headers)
    assert res.status_code == 200

    # Ensure document is removed
    assert Agent.find_by_agent_id(agent.agent_id) is None


def test_dynamic_status_calculation() -> None:
    """Verify connection status is calculated from heartbeat timestamps"""
    agent, _ = Agent.create_agent(name="status-test", hostname="status-host")

    # Never contacted -> offline
    assert agent.status == AgentStatus.OFFLINE

    # Heartbeat 10 seconds ago -> online
    agent.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=10)
    assert agent.status == AgentStatus.ONLINE

    # Heartbeat 120 seconds ago -> stale
    agent.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=120)
    assert agent.status == AgentStatus.STALE

    # Heartbeat 300 seconds ago -> offline
    agent.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=300)
    assert agent.status == AgentStatus.OFFLINE

    # Revoked always overrides timestamp
    agent.is_revoked = True
    assert agent.status == AgentStatus.REVOKED
