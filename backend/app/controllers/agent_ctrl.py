"""
©AngelaMos | 2026
agent_ctrl.py

Business logic for Agent management, heartbeat, and authenticated ingestion

Provides CRUD operations for agents, token generation/rotation/revocation,
health tracking (heartbeats), and deduplicated event ingestion into the
MongoDB + Redis Stream pipeline.

Key exports:
  register_agent, list_agents, get_agent, update_agent, revoke_agent,
  rotate_agent_token, delete_agent, get_agent_stats, process_heartbeat,
  ingest_agent_events

Connects to:
  models/Agent.py - Agent document
  models/LogEvent.py - LogEvent document for event persistence & deduplication
  engine/normalizer.py - calls normalize
  engine/severity.py - calls classify
  core/streaming.py - calls publish_event to Redis Stream
  core/errors.py - NotFoundError
"""

from datetime import datetime, UTC
from typing import Any

from flask import g, request
from mongoengine.errors import NotUniqueError

from app.config import settings
from app.core.errors import NotFoundError
from app.core.streaming import publish_event
from app.engine.normalizer import normalize
from app.engine.severity import classify
from app.models.Agent import Agent
from app.models.LogEvent import LogEvent
from app.schemas.agent import (
    AgentEventIngestRequest,
    AgentHeartbeatRequest,
    AgentQueryParams,
    AgentRegisterRequest,
    AgentUpdateRequest,
)


def register_agent() -> tuple[dict[str, Any], int]:
    """
    Provision a new agent and return its one-time credentials
    """
    data: AgentRegisterRequest = g.validated
    admin_username = g.current_user.username if getattr(g, "current_user", None) else "admin"

    agent, raw_token = Agent.create_agent(
        name=data.name,
        hostname=data.hostname,
        os_type=data.os_type,
        agent_version=data.agent_version,
        registered_by=admin_username,
    )

    return {
        "agent": agent.to_dict(),
        "token": raw_token,
        "instructions": {
            "agent_id": agent.agent_id,
            "auth_header": f"Bearer {raw_token}",
        },
    }, 201


def list_agents() -> dict[str, Any]:
    """
    Return paginated agent list with computed status and search filtering
    """
    params: AgentQueryParams = g.validated
    qs = Agent.objects()

    if params.search:
        term = params.search.strip()
        qs = qs.filter(
            __raw__={
                "$or": [
                    {"hostname": {"$regex": term, "$options": "i"}},
                    {"agent_id": {"$regex": term, "$options": "i"}},
                    {"name": {"$regex": term, "$options": "i"}},
                ]
            }
        )

    all_agents = list(qs)

    # Filter by computed status if requested
    if params.status and params.status.lower() != "all":
        target_status = params.status.lower()
        all_agents = [a for a in all_agents if a.status.value == target_status]

    total = len(all_agents)
    offset = (params.page - 1) * params.per_page
    paged = all_agents[offset : offset + params.per_page]
    pages = (total + params.per_page - 1) // params.per_page if total > 0 else 1

    return {
        "items": [a.to_dict() for a in paged],
        "total": total,
        "page": params.page,
        "per_page": params.per_page,
        "pages": pages,
    }


def get_agent(agent_id: str) -> dict[str, Any]:
    """
    Return detailed metadata for a single agent
    """
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise NotFoundError(f"Agent '{agent_id}' not found")
    return agent.to_dict()


def update_agent(agent_id: str) -> dict[str, Any]:
    """
    Update metadata of an existing agent
    """
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise NotFoundError(f"Agent '{agent_id}' not found")

    data: AgentUpdateRequest = g.validated
    if data.name is not None:
        agent.name = data.name
    if data.hostname is not None:
        agent.hostname = data.hostname
    if data.os_type is not None:
        agent.os_type = data.os_type

    agent.save()
    return agent.to_dict()


def revoke_agent(agent_id: str) -> dict[str, Any]:
    """
    Revoke an agent's credentials
    """
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise NotFoundError(f"Agent '{agent_id}' not found")

    agent.revoke()
    return agent.to_dict()


def rotate_agent_token(agent_id: str) -> dict[str, Any]:
    """
    Rotate an agent's credentials and return new one-time token
    """
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise NotFoundError(f"Agent '{agent_id}' not found")

    new_token = agent.rotate_token()
    return {
        "agent": agent.to_dict(),
        "token": new_token,
    }


def delete_agent(agent_id: str) -> dict[str, Any]:
    """
    Permanently delete an agent record
    """
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise NotFoundError(f"Agent '{agent_id}' not found")

    agent.delete()
    return {"deleted": True, "agent_id": agent_id}


def get_agent_stats() -> dict[str, Any]:
    """
    Aggregate counts of agents by status and total events received
    """
    agents = list(Agent.objects())
    online = sum(1 for a in agents if a.status.value == "online")
    stale = sum(1 for a in agents if a.status.value == "stale")
    offline = sum(1 for a in agents if a.status.value == "offline")
    revoked = sum(1 for a in agents if a.status.value == "revoked")
    total_events = sum(a.total_events_received for a in agents)

    return {
        "total": len(agents),
        "online": online,
        "stale": stale,
        "offline": offline,
        "revoked": revoked,
        "total_events": total_events,
    }


def process_heartbeat() -> dict[str, Any]:
    """
    Handle authenticated agent heartbeat and update live status
    """
    agent: Agent = g.current_agent
    data: AgentHeartbeatRequest = g.validated

    forwarded = request.headers.get("X-Forwarded-For")
    ip_address = forwarded.split(",")[0].strip() if forwarded else request.remote_addr

    agent.record_heartbeat(
        ip_address=ip_address,
        agent_version=data.agent_version,
        metrics=data.metrics,
    )

    return {
        "status": "acknowledged",
        "agent_id": agent.agent_id,
        "server_time": datetime.now(UTC).isoformat(),
    }


def ingest_agent_events() -> tuple[dict[str, Any], int]:
    """
    Validate, deduplicate, persist, and publish an event submitted by an agent
    """
    agent: Agent = g.current_agent
    data: AgentEventIngestRequest = g.validated

    # Deduplication check
    if data.event_id:
        existing = LogEvent.objects(agent_id=agent.agent_id, event_id=data.event_id).first()
        if existing:
            return {
                "status": "duplicate",
                "message": "Event already processed",
                "id": str(existing.id),
                "event_id": data.event_id,
            }, 200

    raw = data.model_dump(exclude_none=True)
    raw["agent_id"] = agent.agent_id
    if not raw.get("hostname"):
        raw["hostname"] = agent.hostname

    normalized = normalize(raw)
    severity = classify(normalized)
    normalized["severity"] = severity
    normalized["agent_id"] = agent.agent_id
    if data.event_id:
        normalized["event_id"] = data.event_id

    try:
        event = LogEvent.create_event(**normalized)
    except NotUniqueError:
        # Concurrent submission of identical event_id
        existing = LogEvent.objects(agent_id=agent.agent_id, event_id=data.event_id).first()
        return {
            "status": "duplicate",
            "message": "Event already processed",
            "id": str(existing.id) if existing else None,
            "event_id": data.event_id,
        }, 200

    agent.record_event()

    publish_event(
        settings.LOG_STREAM_KEY,
        {
            "id": str(event.id),
            "timestamp": str(event.timestamp),
            "source_type": event.source_type,
            "severity": event.severity,
            "event_type": event.event_type,
            "source_ip": event.source_ip,
            "dest_ip": event.dest_ip,
            "hostname": event.hostname,
            "username": event.username,
            "agent_id": agent.agent_id,
        },
    )

    return {
        "status": "created",
        "id": str(event.id),
        "event_id": data.event_id,
        "severity": severity,
    }, 201
