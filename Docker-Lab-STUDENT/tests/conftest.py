"""Shared pytest fixtures and helpers for the SecureNotes test suite."""
import pytest
from fastapi.testclient import TestClient
from app.main import app, reset_database


@pytest.fixture
def client():
    """A fresh, seeded database and a TestClient for each test (independence)."""
    reset_database()
    return TestClient(app, raise_server_exceptions=False)


def login(client, username, password):
    """Log in and return the access token (or None if login failed)."""
    res = client.post("/login", json={"username": username, "password": password})
    if res.status_code != 200:
        return None
    return res.json()["access_token"]


def auth(token):
    """Build the Authorization header for a bearer token."""
    return {"Authorization": f"Bearer {token}"}
