"""
©AngelaMos | 2026
test_agent_auth.py

Unit and integration tests for Agent authentication, token hashing,
constant-time verification, and endpoint access control.
"""

from app.models.Agent import Agent, AgentStatus


def test_agent_token_structure(registered_agent: tuple[Agent, str]) -> None:
    """Verify generated agent token format and attributes"""
    agent, raw_token = registered_agent
    assert raw_token.startswith("siem_agt_")
    assert agent.agent_id in raw_token
    assert agent.token_hash is not None
    assert len(agent.token_hash) == 64  # SHA-256 hex digest length
    assert agent.is_revoked is False
    assert agent.revoked_at is None


def test_agent_token_verification(registered_agent: tuple[Agent, str]) -> None:
    """Verify cryptographic token validation using timing-safe comparison"""
    agent, raw_token = registered_agent

    # Correct token
    assert agent.verify_token(raw_token) is True

    # Tampered secret
    tampered = raw_token[:-4] + "ffff"
    assert agent.verify_token(tampered) is False

    # Random string
    assert agent.verify_token("invalid_token_string") is False
    assert agent.verify_token("") is False


def test_agent_token_rotation(registered_agent: tuple[Agent, str]) -> None:
    """Verify token rotation invalidates old token and validates new one"""
    agent, old_token = registered_agent
    old_hash = agent.token_hash

    new_token = agent.rotate_token()
    agent.reload()

    # New token is generated and hash updated
    assert new_token != old_token
    assert agent.token_hash != old_hash

    # Old token fails, new token succeeds
    assert agent.verify_token(old_token) is False
    assert agent.verify_token(new_token) is True


def test_agent_endpoint_missing_auth(client) -> None:
    """Verify agent endpoint rejects requests without Authorization header"""
    res = client.post(
        "/v1/agents/heartbeat",
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert "required" in data.get("message", "").lower()


def test_agent_endpoint_invalid_token_format(client) -> None:
    """Verify agent endpoint rejects invalid token structure"""
    res = client.post(
        "/v1/agents/heartbeat",
        headers={"Authorization": "Bearer not_a_valid_agent_token"},
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert "format" in data.get("message", "").lower()


def test_agent_endpoint_unknown_agent_id(client) -> None:
    """Verify agent endpoint returns 401 when agent_id is not found"""
    fake_token = "siem_agt_unknown999_abcdef0123456789abcdef0123456789"
    res = client.post(
        "/v1/agents/heartbeat",
        headers={"Authorization": f"Bearer {fake_token}"},
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert "not found" in data.get("message", "").lower()


def test_agent_endpoint_wrong_secret(client, registered_agent: tuple[Agent, str]) -> None:
    """Verify agent endpoint rejects token with valid agent_id but invalid secret"""
    agent, _ = registered_agent
    wrong_token = f"siem_{agent.agent_id}_00000000000000000000000000000000"
    res = client.post(
        "/v1/agents/heartbeat",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert "credentials" in data.get("message", "").lower()


def test_agent_endpoint_revoked_agent(client, registered_agent: tuple[Agent, str]) -> None:
    """Verify agent endpoint rejects revoked agent with 403 Forbidden"""
    agent, raw_token = registered_agent
    agent.revoke()

    res = client.post(
        "/v1/agents/heartbeat",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"agent_version": "1.0.0"},
    )
    assert res.status_code == 403
    data = res.get_json()
    assert "revoked" in data.get("message", "").lower()
