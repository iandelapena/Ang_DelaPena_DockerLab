"""Docker lab, Part C — structural checks on your docker-compose.yml.

Parses the compose file and checks it wires the api and db together correctly.
Running it for real (`docker compose up`) happens on your machine; the proof is
`/health/db` returning {"database":"ok"} and both containers up (Part D).

INSTRUCTOR note: all pass against the solved docker-compose.yml.
"""
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(__file__))
COMPOSE = os.path.join(ROOT, "docker-compose.yml")


def _services():
    """The compose services, or {} if the file is still a stub — so the checks
    fail as clear assertions instead of crashing."""
    assert os.path.exists(COMPOSE), "Missing file: docker-compose.yml"
    with open(COMPOSE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    services = data.get("services")
    return services if isinstance(services, dict) else {}


def test_compose_has_two_services():
    assert len(_services()) >= 2, \
        "Compose needs at least two services — the api and a database."


def test_api_service_builds_locally():
    assert any("build" in s for s in _services().values()), \
        "One service (the api) should `build:` from your Dockerfile."


def test_db_service_uses_postgres():
    images = " ".join(str(s.get("image", "")) for s in _services().values())
    assert "postgres" in images, "A service should use the postgres image."


def test_api_maps_port_8000():
    ports = str([s.get("ports") for s in _services().values()])
    assert "8000" in ports, "Map the api's port 8000 out to your machine."


def test_api_depends_on_db():
    assert any("depends_on" in s for s in _services().values()), \
        "The api should depends_on the db so it starts after the database."


def test_db_has_a_volume():
    assert any(s.get("volumes") for s in _services().values()), \
        "Give the database a volume so its data survives restarts."


def test_api_gets_database_url():
    """The api must be told where the db is, via DATABASE_URL."""
    env_blob = "".join(str(s.get("environment")) for s in _services().values())
    assert "DATABASE_URL" in env_blob, \
        "Pass DATABASE_URL to the api so it can reach the db service."
