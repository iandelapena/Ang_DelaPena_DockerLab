"""API behaviour tests — the happy paths and the obvious error paths."""
from tests.conftest import login, auth


def test_home_ok(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["service"] == "SecureNotes API"


def test_register_then_login(client):
    client.post("/register", json={"username": "mia", "password": "s3cret!"})
    token = login(client, "mia", "s3cret!")
    assert token is not None
    assert token.count(".") == 2          # a JWT has three dot-separated parts


def test_login_wrong_password_is_401(client):
    res = client.post("/login", json={"username": "alice", "password": "nope"})
    assert res.status_code == 401


def test_register_duplicate_username_is_409(client):
    client.post("/register", json={"username": "mia", "password": "x12345"})
    res = client.post("/register", json={"username": "mia", "password": "y67890"})
    assert res.status_code == 409


def test_create_then_list_own_note(client):
    token = login(client, "alice", "alicepass")
    created = client.post("/notes", json={"title": "Todo", "body": "buy milk"}, headers=auth(token))
    assert created.status_code == 200
    listed = client.get("/notes", headers=auth(token))
    titles = [n["title"] for n in listed.json()]
    assert "Todo" in titles
