# Containerize It — Docker Lab (STUDENT)

Package the finished SecureNotes API into a Docker image, then run it together
with a Postgres database using Docker Compose.

**Start with `TASKS.md`** — it lists every task in order with the exact commands.

You write three files:
```
Dockerfile            <- Part A (TASKs A1-A5) + Part B (B1)
.dockerignore         <- Part B (B2)
docker-compose.yml    <- Part C (C1-C2)
```
The app in `app/`, `requirements.txt`, and the tests stay as given.

## Quick start
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest -q                          # 12 app tests pass; 15 Docker checks red

docker --version                   # need Docker Desktop running
```

## Accounts (the app)
| username | password  | role |
|----------|-----------|------|
| admin    | admin123  | admin |
| alice    | alicepass | owns note 1 |
| bob      | bobpass   | owns note 2 |

Keep the `bcrypt==4.0.1` pin in `requirements.txt` — newer bcrypt breaks passlib.
