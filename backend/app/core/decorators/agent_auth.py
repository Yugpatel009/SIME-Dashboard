"""
©AngelaMos | 2026
agent_auth.py

Authentication decorator for external log agents

Extracts agent tokens from Authorization headers or X-Agent-Token,
validates the token hash against the stored hash in MongoDB, ensures the
agent is active and not revoked, and injects the Agent instance onto flask.g.

Key exports:
  agent_endpoint - decorator protecting endpoints that only external agents call
  resolve_agent_optional - helper to optionally identify an agent on shared endpoints

Connects to:
  models/Agent.py - Agent.find_by_agent_id, verify_token
  core/errors.py - raises AuthenticationError, AppError
"""

import functools
import re
from typing import Any
from collections.abc import Callable

import structlog
from flask import g, jsonify, request

from app.core.errors import AppError, AuthenticationError, ForbiddenError
from app.models.Agent import Agent

logger = structlog.get_logger()

TOKEN_PATTERN = re.compile(r"^siem_(agt_[0-9a-zA-Z]+)_[0-9a-zA-Z]+$")


def extract_raw_agent_token() -> str | None:
    """
    Extract agent token from Authorization header or X-Agent-Token
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    custom_header = request.headers.get("X-Agent-Token")
    if custom_header:
        return custom_header.strip()

    return None


def authenticate_agent(token: str) -> Agent:
    """
    Validate raw token and return the associated Agent instance
    """
    match = TOKEN_PATTERN.match(token)
    if not match:
        raise AuthenticationError("Invalid agent token format")

    agent_id = match.group(1)
    agent = Agent.find_by_agent_id(agent_id)
    if agent is None:
        raise AuthenticationError("Agent not found")

    if agent.is_revoked:
        raise ForbiddenError("Agent credential has been revoked")

    if not agent.verify_token(token):
        raise AuthenticationError("Invalid agent credentials")

    return agent


def resolve_agent_optional() -> Agent | None:
    """
    Attempt to authenticate agent if token is provided, without raising if omitted
    """
    token = extract_raw_agent_token()
    if not token:
        return None
    try:
        return authenticate_agent(token)
    except Exception:
        return None


def agent_endpoint() -> Callable[..., Any]:
    """
    Decorator requiring valid Agent bearer token authentication
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                token = extract_raw_agent_token()
                if not token:
                    raise AuthenticationError("Agent authentication required")

                agent = authenticate_agent(token)
                g.current_agent = agent

                return fn(*args, **kwargs)
            except AppError:
                raise
            except Exception:
                logger.exception("unhandled_agent_endpoint_error", endpoint=fn.__name__)
                return jsonify({
                    "error": "InternalServerError",
                    "message": "Internal server error",
                }), 500

        return wrapper

    return decorator
