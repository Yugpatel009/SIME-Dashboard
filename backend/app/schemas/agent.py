"""
©AngelaMos | 2026
agent.py

Pydantic schemas for Agent management, heartbeat, and event ingestion endpoints

Validates registration, updates, heartbeats, and event ingestion payloads.

Key exports:
  AgentRegisterRequest
  AgentUpdateRequest
  AgentHeartbeatRequest
  AgentEventIngestRequest
  AgentQueryParams
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings


class AgentRegisterRequest(BaseModel):
    """
    Payload for registering a new agent
    """
    name: str = Field(min_length=1, max_length=64, description="Human friendly agent name")
    hostname: str = Field(min_length=1, max_length=128, description="Host system name")
    os_type: str = Field(default="linux", max_length=32, description="Target OS (linux, windows)")
    agent_version: str = Field(default="1.0.0", max_length=32, description="Agent software version")


class AgentUpdateRequest(BaseModel):
    """
    Payload for updating agent metadata
    """
    name: str | None = Field(default=None, min_length=1, max_length=64)
    hostname: str | None = Field(default=None, min_length=1, max_length=128)
    os_type: str | None = Field(default=None, max_length=32)


class AgentHeartbeatRequest(BaseModel):
    """
    Payload for agent heartbeat reporting
    """
    agent_version: str | None = Field(default=None, max_length=32)
    metrics: dict[str, Any] | None = Field(default=None, description="System metrics (cpu, memory, queue)")


class AgentEventIngestRequest(BaseModel):
    """
    Payload for authenticated agent event ingestion
    """
    source_type: str = Field(default="auth", description="Log source category")
    event_type: str | None = Field(default=None, description="Specific event type, e.g. login_failure")
    source_ip: str | None = Field(default=None, description="Originating IP address")
    dest_ip: str | None = Field(default=None, description="Destination IP address")
    source_port: int | None = Field(default=None, ge=1, le=65535)
    dest_port: int | None = Field(default=None, ge=1, le=65535)
    hostname: str | None = Field(default=None, max_length=128)
    username: str | None = Field(default=None, max_length=128)
    event_id: str | None = Field(default=None, max_length=64, description="Client-generated unique event ID")
    timestamp: datetime | None = Field(default=None, description="Event occurrence timestamp")
    agent_version: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=4096, description="Raw or parsed log message")
    metadata: dict[str, Any] | None = Field(default=None)

    model_config = {"extra": "allow"}


class AgentQueryParams(BaseModel):
    """
    Query parameters for agent listing
    """
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE)
    status: str | None = Field(default=None, description="Filter: all, online, stale, offline, revoked")
    search: str | None = Field(default=None, description="Search term matching hostname or agent_id")
