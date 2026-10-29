"""
©AngelaMos | 2026
Agent.py

MongoEngine model for registered external log agents

Stores identity, token hash, heartbeat timestamps, and event counters for
external agents (such as the Kali Linux server agent). Provides token creation,
hash verification, status computation (online, stale, offline, revoked),
and heartbeat tracking.

Key exports:
  Agent - agent document with lifecycle and token management methods
  AgentStatus - StrEnum for agent connection states

Connects to:
  models/Base.py - extends BaseDocument
  controllers/agent_ctrl.py - CRUD, token rotation, and heartbeat logic
  core/decorators/agent_auth.py - verifies tokens on incoming agent requests
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    IntField,
    StringField,
)

from app.models.Base import BaseDocument


class AgentStatus(StrEnum):
    """
    Computed agent connection states
    """
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"
    REVOKED = "revoked"


ONLINE_THRESHOLD_SECONDS = 60
STALE_THRESHOLD_SECONDS = 180


class Agent(BaseDocument):
    """
    Registered external log agent document
    """
    meta: dict[str, Any] = {  # noqa: RUF012
        "collection": "agents",
        "ordering": ["-created_at"],
        "indexes": ["agent_id", "is_revoked", "hostname"],
    }

    agent_id = StringField(required=True, unique=True)
    name = StringField(required=True)
    hostname = StringField(required=True)
    os_type = StringField(default="linux")
    agent_version = StringField(default="1.0.0")
    token_hash = StringField(required=True)
    ip_address = StringField()
    is_revoked = BooleanField(default=False)
    revoked_at = DateTimeField()
    last_heartbeat_at = DateTimeField()
    last_event_at = DateTimeField()
    total_events_received = IntField(default=0)
    last_error = StringField()
    registered_by = StringField()
    metrics = DictField()

    @classmethod
    def hash_token(cls, raw_token: str) -> str:
        """
        Compute SHA-256 hash of a raw token
        """
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def generate_credentials(cls, agent_id: str | None = None) -> tuple[str, str, str]:
        """
        Generate a unique agent_id, a secure random token, and its hash.
        Format: siem_agt_<agent_id>_<32_char_hex>
        """
        aid = agent_id or f"agt_{uuid.uuid4().hex[:12]}"
        secret = secrets.token_hex(16)
        raw_token = f"siem_{aid}_{secret}"
        token_hash = cls.hash_token(raw_token)
        return aid, raw_token, token_hash

    @classmethod
    def create_agent(
        cls,
        name: str,
        hostname: str,
        os_type: str = "linux",
        agent_version: str = "1.0.0",
        registered_by: str | None = None,
    ) -> tuple["Agent", str]:
        """
        Provision a new agent with unique credentials and return (agent, raw_token)
        """
        agent_id, raw_token, token_hash = cls.generate_credentials()
        agent = cls(
            agent_id=agent_id,
            name=name,
            hostname=hostname,
            os_type=os_type,
            agent_version=agent_version,
            token_hash=token_hash,
            registered_by=registered_by,
        )
        agent.save()
        return agent, raw_token

    @classmethod
    def find_by_agent_id(cls, agent_id: str) -> "Agent | None":
        """
        Lookup agent by agent_id
        """
        return cls.objects(agent_id=agent_id).first()  # type: ignore[no-untyped-call, no-any-return]

    def verify_token(self, raw_token: str) -> bool:
        """
        Constant-time verification of the presented token against stored hash
        """
        if self.is_revoked:
            return False
        computed = self.hash_token(raw_token)
        return hmac.compare_digest(computed, self.token_hash)

    def rotate_token(self) -> str:
        """
        Generate a new secret token for the agent, store its hash, and return raw token
        """
        _, raw_token, token_hash = self.generate_credentials(agent_id=self.agent_id)
        self.token_hash = token_hash
        self.is_revoked = False
        self.revoked_at = None
        self.save()
        return raw_token

    def revoke(self) -> None:
        """
        Revoke the agent's authentication credential
        """
        self.is_revoked = True
        self.revoked_at = datetime.now(UTC)
        self.save()

    def record_heartbeat(
        self,
        ip_address: str | None = None,
        agent_version: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """
        Update heartbeat timestamp, remote IP, agent version, and optional system metrics
        """
        self.last_heartbeat_at = datetime.now(UTC)
        if ip_address:
            self.ip_address = ip_address
        if agent_version:
            self.agent_version = agent_version
        if metrics is not None:
            self.metrics = metrics
        self.save()

    def record_event(self, error: str | None = None) -> None:
        """
        Update last event timestamp and increment event counter
        """
        self.last_event_at = datetime.now(UTC)
        self.total_events_received += 1
        if error:
            self.last_error = error
        self.save()

    @property
    def status(self) -> AgentStatus:
        """
        Compute live connection status based on heartbeat and event recency
        """
        if self.is_revoked:
            return AgentStatus.REVOKED

        timestamps = [
            ts for ts in (self.last_heartbeat_at, self.last_event_at)
            if ts is not None
        ]
        if not timestamps:
            return AgentStatus.OFFLINE

        most_recent = max(timestamps)
        if most_recent.tzinfo is None:
            most_recent = most_recent.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        elapsed = (now - most_recent).total_seconds()

        if elapsed <= ONLINE_THRESHOLD_SECONDS:
            return AgentStatus.ONLINE
        if elapsed <= STALE_THRESHOLD_SECONDS:
            return AgentStatus.STALE
        return AgentStatus.OFFLINE

    def to_dict(self) -> dict[str, Any]:
        """
        Return sanitized dictionary representation without sensitive hashes
        """
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "name": self.name,
            "hostname": self.hostname,
            "os_type": self.os_type,
            "agent_version": self.agent_version,
            "ip_address": self.ip_address,
            "status": self.status.value,
            "is_revoked": self.is_revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "last_heartbeat_at": (
                self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None
            ),
            "last_event_at": (
                self.last_event_at.isoformat() if self.last_event_at else None
            ),
            "total_events_received": self.total_events_received,
            "last_error": self.last_error,
            "registered_by": self.registered_by,
            "metrics": self.metrics or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
