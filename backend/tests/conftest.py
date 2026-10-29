"""
©AngelaMos | 2026
conftest.py

Shared pytest fixtures for the SIEM backend test suite
"""

import os
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Ensure test settings before importing app
os.environ["MONGO_DB"] = "siem_test"
os.environ["DEBUG"] = "true"

from app import create_app
from app.core.auth import create_access_token, hash_password
from app.models.Agent import Agent
from app.models.LogEvent import LogEvent
from app.models.User import User, UserRole


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """
    Create Flask test application
    """
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "MONGO_DB": "siem_test",
    })
    yield test_app


@pytest.fixture(scope="function")
def client(app: Flask) -> FlaskClient:
    """
    Flask test client fixture
    """
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app: Flask) -> Generator[None, None, None]:
    """
    Clean up test collections before and after each test function
    """
    # Clean before
    User.objects.delete()
    Agent.objects.delete()
    LogEvent.objects.delete()
    yield
    # Clean after
    User.objects.delete()
    Agent.objects.delete()
    LogEvent.objects.delete()


@pytest.fixture
def admin_user() -> User:
    """
    Create and persist an admin user
    """
    return User.create_user(
        username="admin_tester",
        email="admin_tester@siem.local",
        password_hash=hash_password("AdminSecurePassword123!"),
        role=UserRole.ADMIN,
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """
    JWT token for the test admin user
    """
    return create_access_token(
        user_id=str(admin_user.id),
        extra_claims={"username": admin_user.username, "role": admin_user.role},
    )


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """
    Authorization headers for admin
    """
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def analyst_user() -> User:
    """
    Create and persist an analyst user
    """
    return User.create_user(
        username="analyst_tester",
        email="analyst_tester@siem.local",
        password_hash=hash_password("AnalystPassword123!"),
        role=UserRole.ANALYST,
    )


@pytest.fixture
def analyst_token(analyst_user: User) -> str:
    """
    JWT token for the test analyst user
    """
    return create_access_token(
        user_id=str(analyst_user.id),
        extra_claims={"username": analyst_user.username, "role": analyst_user.role},
    )


@pytest.fixture
def analyst_headers(analyst_token: str) -> dict[str, str]:
    """
    Authorization headers for analyst
    """
    return {
        "Authorization": f"Bearer {analyst_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def registered_agent() -> tuple[Agent, str]:
    """
    Create a registered agent document and return (agent, raw_token)
    """
    agent, raw_token = Agent.create_agent(
        name="kali-lab-agent",
        hostname="kali-vm",
        os_type="Linux (Kali 2024)",
        agent_version="1.0.0",
        registered_by="admin_tester",
    )
    return agent, raw_token


@pytest.fixture
def agent_headers(registered_agent: tuple[Agent, str]) -> dict[str, str]:
    """
    Authorization headers for the registered agent
    """
    _, raw_token = registered_agent
    return {
        "Authorization": f"Bearer {raw_token}",
        "Content-Type": "application/json",
    }
