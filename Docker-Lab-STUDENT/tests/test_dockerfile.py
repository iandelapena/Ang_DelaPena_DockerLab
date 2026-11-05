"""Docker lab, Parts A-B — structural checks on your Dockerfile & .dockerignore.

Docker runs on YOUR machine, not in pytest, so these can't build the image.
They read your Dockerfile and .dockerignore and check they're put together
right — a fast red->green guide before you build for real. The graded proof is
the image actually building and running (screenshots in Part D).

INSTRUCTOR note: all pass against the solved files.
"""
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
DOCKERFILE = os.path.join(ROOT, "Dockerfile")
DOCKERIGNORE = os.path.join(ROOT, ".dockerignore")


def _read(path):
    assert os.path.exists(path), f"Missing file: {os.path.basename(path)}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def _instructions(text):
    """[(INSTRUCTION, rest), ...] for real lines, joining backslash continuations."""
    out, buf = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        buf += line
        if buf.endswith("\\"):
            buf = buf[:-1] + " "
            continue
        parts = buf.split(None, 1)
        out.append((parts[0].upper(), parts[1] if len(parts) > 1 else ""))
        buf = ""
    return out


# ----- Part A -----
def test_dockerfile_starts_from_python():
    ins = _instructions(_read(DOCKERFILE))
    assert ins, "The Dockerfile has no instructions yet — start with a FROM line."
    froms = [rest for name, rest in ins if name == "FROM"]
    assert froms, "The Dockerfile needs a FROM line."
    assert any("python" in f.lower() for f in froms), \
        "Start FROM an official python image."


def test_base_image_is_slim_and_pinned():
    froms = [r for n, r in _instructions(_read(DOCKERFILE)) if n == "FROM"]
    base = froms[0].split()[0]
    assert ":" in base and "latest" not in base, \
        "Pin the base image to a version tag, e.g. python:3.12-slim (never :latest)."
    assert "slim" in base.lower() or "alpine" in base.lower(), \
        "Use a small base image (…-slim or …-alpine) to keep the image light."


def test_sets_workdir():
    assert any(n == "WORKDIR" for n, _ in _instructions(_read(DOCKERFILE))), \
        "Set a WORKDIR so the app has a home inside the image."


def test_installs_requirements():
    runs = " ".join(r for n, r in _instructions(_read(DOCKERFILE)) if n == "RUN")
    assert "pip install" in runs and "requirements.txt" in runs, \
        "A RUN step should: pip install -r requirements.txt"


def test_copies_requirements_before_source():
    """Layer caching: copy requirements and install BEFORE copying all the code."""
    ins = _instructions(_read(DOCKERFILE))
    copies = [(i, rest) for i, (n, rest) in enumerate(ins) if n == "COPY"]
    req_i = next((i for i, rest in copies if "requirements" in rest), None)
    src_i = next((i for i, rest in copies
                  if "requirements" not in rest and rest.split()[0] in (".", "./", "app")), None)
    assert req_i is not None, "COPY requirements.txt before installing."
    assert src_i is not None, "COPY the rest of your source in (e.g. COPY . .)."
    assert req_i < src_i, \
        "Copy requirements.txt and install FIRST, then COPY the code — so edits " \
        "to your code don't bust the cached dependency layer."


def test_declares_command():
    cmds = [r for n, r in _instructions(_read(DOCKERFILE)) if n in ("CMD", "ENTRYPOINT")]
    assert cmds, "Add a CMD that starts the app."
    joined = " ".join(cmds)
    assert "uvicorn" in joined, "The CMD should launch the API with uvicorn."
    assert "0.0.0.0" in joined, \
        "Bind uvicorn to 0.0.0.0 so the app is reachable from outside the container."


# ----- Part B -----
def test_runs_as_non_root_user():
    assert any(n == "USER" for n, _ in _instructions(_read(DOCKERFILE))), \
        "Add a USER instruction so the container doesn't run as root."


def test_dockerignore_excludes_junk():
    text = _read(DOCKERIGNORE)
    entries = {l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")}
    for needed in ("venv", ".git", "__pycache__"):
        assert any(needed in e for e in entries), \
            f".dockerignore should exclude {needed}/ so it never bloats the image."
