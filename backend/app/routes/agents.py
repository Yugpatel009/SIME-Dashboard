"""
©AngelaMos | 2026
agents.py

Route handlers for the Agent management, heartbeat, and ingestion API (/v1/agents)

Mounts administrative endpoints for agent lifecycle management (register, list,
stats, inspect, update, revoke, rotate-token, delete) as well as agent-authenticated
endpoints for heartbeats and event ingestion.

Connects to:
  controllers/agent_ctrl.py - business logic
  schemas/agent.py - AgentRegisterRequest, AgentUpdateRequest, etc.
  core/decorators/ - endpoint, agent_endpoint, S, R
  models/User.py - UserRole
  routes/__init__.py - agents_bp registered here
"""

from typing import Any

from flask import Blueprint

from app.controllers import agent_ctrl
from app.core.decorators import (
    R,
    S,
    agent_endpoint,
    endpoint,
)
from app.models.User import UserRole
from app.schemas.agent import (
    AgentEventIngestRequest,
    AgentHeartbeatRequest,
    AgentQueryParams,
    AgentRegisterRequest,
    AgentUpdateRequest,
)

agents_bp = Blueprint("agents", __name__)

ADMIN = [UserRole.ADMIN]


@agents_bp.post("/register")
@endpoint(roles=ADMIN)
@S(AgentRegisterRequest)
@R(status=201)
def register_agent() -> Any:
    """
    Register a new agent and receive its one-time authentication token (admin only)
    """
    return agent_ctrl.register_agent()


@agents_bp.get("")
@endpoint()
@S(AgentQueryParams, source="query")
@R()
def list_agents() -> Any:
    """
    List all agents with status and filtering (analyst and admin)
    """
    return agent_ctrl.list_agents()


@agents_bp.get("/stats")
@endpoint()
@R()
def get_agent_stats() -> Any:
    """
    Return high-level agent fleet metrics (online, stale, offline, events)
    """
    return agent_ctrl.get_agent_stats()


@agents_bp.get("/<agent_id>")
@endpoint()
@R()
def get_agent(agent_id: str) -> Any:
    """
    Retrieve single agent details and statistics
    """
    return agent_ctrl.get_agent(agent_id)


@agents_bp.patch("/<agent_id>")
@endpoint(roles=ADMIN)
@S(AgentUpdateRequest)
@R()
def update_agent(agent_id: str) -> Any:
    """
    Update agent metadata (admin only)
    """
    return agent_ctrl.update_agent(agent_id)


@agents_bp.post("/<agent_id>/revoke")
@endpoint(roles=ADMIN)
@R()
def revoke_agent(agent_id: str) -> Any:
    """
    Revoke an agent's credentials immediately (admin only)
    """
    return agent_ctrl.revoke_agent(agent_id)


@agents_bp.post("/<agent_id>/rotate-token")
@endpoint(roles=ADMIN)
@R()
def rotate_agent_token(agent_id: str) -> Any:
    """
    Rotate agent credentials and return new one-time token (admin only)
    """
    return agent_ctrl.rotate_agent_token(agent_id)


@agents_bp.delete("/<agent_id>")
@endpoint(roles=ADMIN)
@R()
def delete_agent(agent_id: str) -> Any:
    """
    Delete an agent record permanently (admin only)
    """
    return agent_ctrl.delete_agent(agent_id)


@agents_bp.post("/heartbeat")
@agent_endpoint()
@S(AgentHeartbeatRequest)
@R()
def agent_heartbeat() -> Any:
    """
    Agent heartbeat ping updating live connection state
    """
    return agent_ctrl.process_heartbeat()


@agents_bp.post("/ingest")
@agent_endpoint()
@S(AgentEventIngestRequest)
@R(status=201)
def agent_ingest() -> Any:
    """
    Authenticated event ingestion from an active agent with deduplication
    """
    return agent_ctrl.ingest_agent_events()
