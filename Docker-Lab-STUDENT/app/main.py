"""
SecureNotes API  —  Week 14 Lab (INSTRUCTOR / ANSWER KEY)
Web Systems and Technologies

The complete, secure version. Real authentication and authorization:
  - passwords are salted + hashed with bcrypt (passlib)       [TASK 1]
  - login issues a signed, expiring JSON Web Token            [TASK 2]
  - a dependency validates the token on protected routes       [TASK 3]
  - get_note enforces OWNERSHIP (A01)                          [TASK 4]
  - /admin/users enforces the admin ROLE (A01)                 [TASK 5]

Run it:
    uvicorn app.main:app --reload
Docs:
    http://127.0.0.1:8000/docs
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError

app = FastAPI(title="SecureNotes API (Week 14 — secured)", version="2.0")

# --- config ---------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")   # real deploy: set this
ALGORITHM = "HS256"
TOKEN_MINUTES = 30

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

oauth2 = OAuth2PasswordBearer(tokenUrl="login")

# --- TASK 1: password hashing (bcrypt) ------------------------------------
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw: str) -> str:
    return pwd.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return pwd.verify(raw, hashed)

# --- TASK 2: JSON Web Tokens ----------------------------------------------
def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    claims = {"sub": username, "exp": expire}
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

def read_token(token: str):
    """Return the username from a valid token, or None if invalid/expired."""
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return claims.get("sub")
    except JWTError:
        return None

# --- database (in-memory SQLite, seeded on startup) -----------------------
db = sqlite3.connect(":memory:", check_same_thread=False)
db.row_factory = sqlite3.Row

def init_db():
    db.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL
        );
        """
    )
    db.execute("INSERT INTO users (username,password,is_admin) VALUES (?,?,1)", ("admin", hash_password("admin123")))
    db.execute("INSERT INTO users (username,password,is_admin) VALUES (?,?,0)", ("alice", hash_password("alicepass")))
    db.execute("INSERT INTO users (username,password,is_admin) VALUES (?,?,0)", ("bob", hash_password("bobpass")))
    db.execute("INSERT INTO notes (owner_id,title,body) VALUES (2,'Alice diary','Alice secret note')")
    db.execute("INSERT INTO notes (owner_id,title,body) VALUES (3,'Bob plans','Bob secret note')")
    db.commit()

def reset_database():
    """Used by the test suite (Week 15) to start from a clean, seeded state."""
    db.execute("DROP TABLE IF EXISTS users")
    db.execute("DROP TABLE IF EXISTS notes")
    init_db()

init_db()

# --- models ---------------------------------------------------------------
class Credentials(BaseModel):
    username: str
    password: str

class NewNote(BaseModel):
    title: str
    body: str

# --- TASK 3: the auth dependency (fails closed) ---------------------------
def get_current_user(token: str = Depends(oauth2)):
    username = read_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return row

def require_admin(user=Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admins only")
    return user

# --- routes ---------------------------------------------------------------
@app.post("/register")
def register(creds: Credentials):
    existing = db.execute("SELECT id FROM users WHERE username = ?", (creds.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    db.execute(
        "INSERT INTO users (username,password,is_admin) VALUES (?,?,0)",
        (creds.username, hash_password(creds.password)),
    )
    db.commit()
    return {"message": f"user {creds.username} created"}

@app.post("/login")
def login(creds: Credentials):
    row = db.execute(
        "SELECT id, username, password FROM users WHERE username = ?", (creds.username,)
    ).fetchone()
    # one generic message — no user enumeration (A07)
    if row is None or not verify_password(creds.password, row["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_token(row["username"]), "token_type": "bearer"}

@app.get("/notes")
def list_my_notes(user=Depends(get_current_user)):
    rows = db.execute("SELECT * FROM notes WHERE owner_id = ?", (user["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.get("/notes/{note_id}")
def get_note(note_id: int, user=Depends(get_current_user)):
    row = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    # TASK 4: ownership check (A01)
    if row["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your note")
    return dict(row)

@app.post("/notes")
def create_note(note: NewNote, user=Depends(get_current_user)):
    cur = db.execute(
        "INSERT INTO notes (owner_id,title,body) VALUES (?,?,?)",
        (user["id"], note.title, note.body),
    )
    db.commit()
    return {"id": cur.lastrowid, "title": note.title}

@app.get("/admin/users")
def list_all_users(admin=Depends(require_admin)):   # TASK 5: role check (A01)
    rows = db.execute("SELECT id, username, is_admin FROM users").fetchall()
    return [dict(r) for r in rows]   # never return password hashes

@app.get("/")
def home():
    return {"service": "SecureNotes API", "docs": "/docs"}


# --- database health check (used in the Docker Compose part of the lab) -----
# Notes are still stored in SQLite inside the container. This endpoint exists so
# that when docker-compose brings up a Postgres service next to the API, you can
# PROVE the two containers can talk: the API reads DATABASE_URL (set by compose)
# and opens a real connection to the db service.
#   - DATABASE_URL unset  -> {"database": "not configured"}  (Parts A-B, stand-alone)
#   - DATABASE_URL set    -> {"database": "ok"} once the db container is reachable
# It never crashes the app, so the image still runs with no database attached.
@app.get("/health/db")
def health_db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return {"database": "not configured"}
    try:
        import psycopg
        with psycopg.connect(url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return {"database": "ok"}
    except Exception as e:
        return {"database": "error", "detail": str(e)[:150]}
