"""Security tests — these encode the OWASP rules from Weeks 13-14 as behaviour.
If a future change reopens a hole, one of these turns red before it ships."""
from tests.conftest import login, auth


def test_protected_route_rejects_no_token(client):
    res = client.get("/notes")                       # no Authorization header
    assert res.status_code == 401                    # A07: auth required


def test_protected_route_rejects_bad_token(client):
    res = client.get("/notes", headers=auth("not.a.jwt"))
    assert res.status_code == 401                    # A07/A10: fail closed


def test_user_cannot_read_another_users_note(client):
    alice = login(client, "alice", "alicepass")
    res = client.get("/notes/2", headers=auth(alice))   # note 2 belongs to Bob
    assert res.status_code == 403                    # A01: ownership enforced


def test_user_can_read_own_note(client):
    alice = login(client, "alice", "alicepass")
    res = client.get("/notes/1", headers=auth(alice))   # note 1 is Alice's
    assert res.status_code == 200


def test_login_does_not_reveal_which_field_was_wrong(client):
    m1 = client.post("/login", json={"username": "ghost", "password": "x"}).json()
    m2 = client.post("/login", json={"username": "alice", "password": "x"}).json()
    assert m1 == m2                                  # A07: no user enumeration


def test_non_admin_cannot_list_users(client):
    alice = login(client, "alice", "alicepass")
    assert client.get("/admin/users", headers=auth(alice)).status_code == 403


def test_admin_can_list_users_without_password_leak(client):
    admin = login(client, "admin", "admin123")
    res = client.get("/admin/users", headers=auth(admin))
    assert res.status_code == 200
    assert all("password" not in u for u in res.json())   # A04: no hash leak
