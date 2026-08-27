# Voice Store Service + Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `bubthegreat/voice-store`: an authenticated FastAPI service that stores each user's voice profiles + corpus, a `voicectl` HTTP client, and the `voice` skill moved out of madskillz.

**Architecture:** One repo, three parts. `server/` is a skill-matrix-shaped FastAPI app (SQLAlchemy async, MySQL, Alembic) with four tables and opaque bearer tokens. `client/` is the existing `voicectl` package with its git transport replaced by an httpx client (`api.py`) and a thin `store.py` for token/state files. `skills/voice/` is the skill, unchanged except for setup docs and the installer. Server never calls an LLM; all judgment runs locally through the skill.

**Tech Stack:** Python 3.12 (server) / ≥3.11 (client), FastAPI, SQLAlchemy 2 async, aiomysql + aiosqlite, Alembic, passlib/bcrypt 4.0.1, httpx, pytest-asyncio + xdist, uv, Docker, Kustomize, ArgoCD, GitHub Actions → Docker Hub.

**Spec:** `docs/superpowers/specs/2026-08-26-voice-store-service-design.md` (in madskillz; copied into the new repo in Task 1)

## Global Constraints

- New repo `bubthegreat/voice-store`, **private** for now. Default branch `main`. All work on `main` via small commits (single developer, pre-release) — no feature branches needed until the first tag.
- Server: `requires-python = ">=3.12"`; FastAPI `root_path="/api"`; settings via `os.getenv`; **missing `DB_PASSWORD` raises at import unless `DATABASE_URL` is set**; ruff line-length 120; `asyncio_mode = "auto"`; tests run `uv run pytest -q` from `server/` (per-worker SQLite).
- Client: `requires-python = ">=3.11"`, dependency `httpx>=0.28`; hooks `capture`/`gate` keep exit-0 / no-stdout / errors-to-`sync.log`; tests run `uv run pytest -q` from `client/`.
- Token: `"vs_" + secrets.token_urlsafe(32)`, stored `sha256(raw).hexdigest()`. Header `Authorization: Bearer <raw>`.
- `If-Match` accepts `"3"` or `3`; `ETag` is returned quoted `"3"`.
- Corpus sha: `hashlib.sha256(f"{ts}\n{text}".encode()).hexdigest()`.
- Corpus rows and profile versions are never updated or deleted; no route does.
- Password policy: `len(password) >= 12`, nothing else.
- Commit messages: plain Conventional Commits.
- Every task ends with tests green in the project it touches.

---

## File map

| Path | Responsibility |
|---|---|
| `.claude-plugin/plugin.json` | plugin manifest `voice` |
| `skills/voice/**` | skill (moved), setup docs rewritten in Task 12 |
| `client/pyproject.toml`, `client/voicectl/*` | `voicectl` CLI; `api.py` (HTTP), `store.py` (token/state files), rest as today |
| `client/tests/*` | unit tests + `live_server` fixture (uvicorn thread over the server package on SQLite) |
| `server/pyproject.toml` | `voice-store` package |
| `server/src/voice_store/{db,main}.py` | engine/session, app + health + handlers |
| `server/src/voice_store/models/{base,user,token,profile,corpus}.py` | ORM |
| `server/src/voice_store/utils/auth.py` | `HTTPBearer`, `hash_token`, `get_current_user` |
| `server/src/voice_store/services/{password_service,token_service,profile_service,corpus_service}.py` | logic |
| `server/src/voice_store/routes/{auth,me,profiles,corpus}.py` | routers |
| `server/src/voice_store/types/*.py` | pydantic models |
| `server/src/voice_store/vendor/{profile,merge}.py` | verbatim copies from client |
| `server/src/voice_store/scripts/create_user.py` | bootstrap CLI |
| `server/alembic/**` | migrations |
| `server/tests/*` | API tests |
| `Dockerfile`, `docker-entrypoint.sh`, `k8s/**`, `argocd/**`, `.github/workflows/*` | deploy |
| `scripts/check_vendor.sh` | vendor-diff CI check |

---

### Task 1: Repo scaffold — move skill + client, plugin manifest

**Files:**
- Create: repo `bubthegreat/voice-store` (private), `README.md`, `.gitignore`, `.claude-plugin/plugin.json`, `docs/superpowers/specs/2026-08-26-voice-store-service-design.md` (copy), `scripts/check_vendor.sh`
- Move: `skills/voice/**` and `client/**` from madskillz commit `f1eab52` (`plugins/madskillz/skills/voice/`)

**Interfaces:**
- Produces: `client/voicectl/` package identical to madskillz `f1eab52` except `cli/` → `client/` rename; `skills/voice/` identical for now.

- [ ] **Step 1: Create the repo and skeleton**

```bash
cd ~/Development
gh repo create bubthegreat/voice-store --private --description "Voice store: authenticated profile + corpus service and the voice skill/client" --clone
cd voice-store
git checkout -b main 2>/dev/null || true
mkdir -p .claude-plugin skills client server docs/superpowers/specs scripts
cp ~/Development/madskillz/docs/superpowers/specs/2026-08-26-voice-store-service-design.md docs/superpowers/specs/
cp ~/Development/madskillz/docs/superpowers/plans/2026-08-26-voice-store-service.md docs/superpowers/plans/ 2>/dev/null || mkdir -p docs/superpowers/plans && cp ~/Development/madskillz/docs/superpowers/plans/2026-08-26-voice-store-service.md docs/superpowers/plans/
```

- [ ] **Step 2: Extract the skill and client from madskillz**

```bash
git -C ~/Development/madskillz archive f1eab52 plugins/madskillz/skills/voice | tar -x -C /tmp
mv /tmp/plugins/madskillz/skills/voice/cli client
mv /tmp/plugins/madskillz/skills/voice skills/voice
rm -rf /tmp/plugins
ls client skills/voice
```

Expected: `client/{pyproject.toml,uv.lock,voicectl,tests}`, `skills/voice/{SKILL.md,references,hooks,scripts,evals}`.

- [ ] **Step 3: Write the manifest, gitignore, README, vendor check**

`.claude-plugin/plugin.json`:

```json
{
  "name": "voice",
  "description": "Owner voice profiles: capture, render, update, and sync through the voice-store service",
  "version": "0.1.0",
  "author": { "name": "Bub Taylor" },
  "skills": ["./skills/voice"]
}
```

`.gitignore`:

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
.coverage*
test_*.db
*.egg-info/
.superpowers/
server/.env
```

`scripts/check_vendor.sh`:

```bash
#!/usr/bin/env bash
# CI guard: server/vendor copies must match the client modules byte-for-byte after the header.
set -eu
root="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
for m in profile merge; do
  src="$root/client/voicectl/$m.py"
  dst="$root/server/src/voice_store/vendor/$m.py"
  # first 3 lines of the vendored file are the provenance header
  if ! diff -q "$src" <(tail -n +4 "$dst") >/dev/null; then
    echo "vendor drift: $dst != $src"; fail=1
  fi
done
exit $fail
```

`README.md`:

```markdown
# voice-store

One repo, three parts:

- `skills/voice/` - the Claude Code skill (this repo is a plugin; install it from the madskillz marketplace).
- `client/` - `voicectl`, the CLI the skill drives. Captures prompts locally, renders profiles, runs the local
  "update my voice" pass, and syncs with the service.
- `server/` - the voice-store API: username/password accounts, opaque bearer tokens, per-user profiles
  (versioned) and corpus (append-only). No LLM calls on the server.

Spec: `docs/superpowers/specs/2026-08-26-voice-store-service-design.md`.
```

- [ ] **Step 4: Verify the client suite still runs in its new home, commit**

```bash
cd client && uv sync --quiet && uv run pytest -q; cd ..
chmod +x scripts/check_vendor.sh
git add -A && git commit -m "chore: scaffold voice-store; move voice skill and voicectl from madskillz" && git push -u origin main
```

Expected: 70 passed (the git-store tests still pass here; they are deleted in Task 8).

---

### Task 2: Server skeleton — models, db, app, alembic, test harness

**Files:**
- Create: `server/pyproject.toml`, `server/src/voice_store/__init__.py`, `server/src/voice_store/models/{__init__,base,user,token,profile,corpus}.py`, `server/src/voice_store/db.py`, `server/src/voice_store/main.py`, `server/alembic.ini`, `server/alembic/env.py`, `server/alembic/script.py.mako`, `server/alembic/versions/0001_initial.py`, `server/tests/conftest.py`, `server/tests/test_health.py`

**Interfaces:**
- Produces: `Base`, `User`, `Token`, `Profile`, `CorpusItem` ORM classes; `get_session()` dependency; `engine`; `app`; `DATABASE_URL` env override; conftest fixtures `client` (httpx ASGI), `test_session`.

- [ ] **Step 1: `server/pyproject.toml`**

```toml
[project]
name = "voice-store"
version = "0.1.0"
description = "Voice store API: per-user voice profiles and prompt corpus behind bearer tokens"
requires-python = ">=3.12"
dependencies = [
    "aiomysql>=0.2.0",
    "aiosqlite>=0.20.0",
    "alembic>=1.13",
    "bcrypt==4.0.1",
    "fastapi[all]>=0.115",
    "passlib[bcrypt]>=1.7.4",
    "pymysql<1.3.0",
    "sqlalchemy>=2.0",
    "typer>=0.12",
]

[dependency-groups]
dev = ["httpx>=0.28", "pytest>=8", "pytest-asyncio>=0.25", "pytest-xdist>=3.6", "ruff>=0.6"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/voice_store"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-n auto --dist loadfile"

[tool.ruff]
line-length = 120
```

- [ ] **Step 2: Models**

`models/base.py`:

```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()
```

`models/user.py`:

```python
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from voice_store.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, server_default="1")
    # ISO-8601 Z timestamp of the newest corpus line folded into core.md; shared by every machine.
    processed_through = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

`models/token.py`:

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from voice_store.models.base import Base


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(64), nullable=False, default="default")
    token_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
```

`models/profile.py`:

```python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.sql import func

from voice_store.models.base import Base

LongText = Text().with_variant(MEDIUMTEXT(), "mysql")


class Profile(Base):
    """Append-only. The current profile for (user, context) is the row with the highest version."""

    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", "context", "version", name="uq_profile_version"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    context = Column(String(32), nullable=False)
    version = Column(Integer, nullable=False)
    body = Column(LongText, nullable=False)
    source = Column(String(16), nullable=False, default="user")  # user | updater | seed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

`models/corpus.py`:

```python
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from voice_store.models.base import Base
from voice_store.models.profile import LongText


class CorpusItem(Base):
    """Append-only, never updated or deleted."""

    __tablename__ = "corpus"
    __table_args__ = (
        UniqueConstraint("user_id", "sha", name="uq_corpus_sha"),
        Index("ix_corpus_user_ts", "user_id", "ts"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ts = Column(String(32), nullable=False)
    text = Column(LongText, nullable=False)
    machine = Column(String(64), nullable=True)
    sha = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

`models/__init__.py`:

```python
from voice_store.models.base import Base
from voice_store.models.corpus import CorpusItem
from voice_store.models.profile import Profile
from voice_store.models.token import Token
from voice_store.models.user import User

__all__ = ["Base", "CorpusItem", "Profile", "Token", "User"]
```

- [ ] **Step 3: `db.py` and `main.py`**

`db.py`:

```python
"""Engine + session dependency. DATABASE_URL overrides the MySQL assembly (tests, local SQLite);
otherwise DB_PASSWORD is required so a misconfigured deployment fails at import."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from voice_store.models import Base


def database_url() -> str:
    override = os.getenv("DATABASE_URL")
    if override:
        return override
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "voice")
    password = os.getenv("DB_PASSWORD")
    if password is None:
        raise RuntimeError("DB_PASSWORD is required (or set DATABASE_URL); refusing a default password")
    name = os.getenv("DB_NAME", "voice_store")
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = database_url()
_mysql = DATABASE_URL.startswith("mysql")
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=_mysql,
    pool_recycle=1800 if _mysql else -1,
    connect_args={"connect_timeout": 30, "charset": "utf8mb4"} if _mysql else {},
)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

`main.py`:

```python
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from voice_store.db import init_db


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(handler)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    yield


app = FastAPI(
    title="voice-store",
    description="Per-user voice profiles (versioned) and prompt corpus (append-only) behind bearer tokens.",
    root_path="/api",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"message": str(exc)})


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "voice-store"}
```

Routers are included in later tasks with:

```python
from voice_store.routes import auth_router, corpus_router, me_router, profiles_router
for r in (auth_router, me_router, profiles_router, corpus_router):
    app.include_router(r)
```

(Add the block now with an empty `routes/__init__.py` exporting nothing yet? No — add the block in Task 3 when `auth_router` exists; keep `main.py` minimal here.)

- [ ] **Step 4: Alembic**

`server/alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = src
sqlalchemy.url = driver://user:pass@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
qualname =
[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
[logger_alembic]
level = INFO
handlers =
qualname = alembic
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`server/alembic/env.py`:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine

from voice_store.db import database_url
from voice_store.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", database_url())
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except (ValueError, KeyError):
        pass
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = AsyncEngine(engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.",
                                                 poolclass=pool.NullPool, future=True))
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

`server/alembic/script.py.mako` — the stock template (`alembic init` output). Generate it with `cd server && uv run alembic init /tmp/alembic-skel && cp /tmp/alembic-skel/script.py.mako alembic/`.

`server/alembic/versions/0001_initial.py`:

```python
"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-08-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

LongText = sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("processed_through", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("context", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", LongText, nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "context", "version", name="uq_profile_version"),
    )
    op.create_table(
        "corpus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.String(32), nullable=False),
        sa.Column("text", LongText, nullable=False),
        sa.Column("machine", sa.String(64), nullable=True),
        sa.Column("sha", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "sha", name="uq_corpus_sha"),
    )
    op.create_index("ix_corpus_user_ts", "corpus", ["user_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_corpus_user_ts", table_name="corpus")
    op.drop_table("corpus")
    op.drop_table("profiles")
    op.drop_table("tokens")
    op.drop_table("users")
```

- [ ] **Step 5: Test harness + first test**

`server/tests/conftest.py`:

```python
import os

# Must precede any voice_store import: db.py assembles the URL at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_master.db")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from voice_store.db import get_session
from voice_store.main import app
from voice_store.models import Base


@pytest.fixture(scope="session")
def test_database_url(worker_id: str) -> str:
    return f"sqlite+aiosqlite:///./test_{worker_id}.db"


@pytest.fixture(scope="session")
async def test_engine(test_database_url):
    engine = create_async_engine(test_database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(test_session):
    import httpx
    from httpx import ASGITransport

    async def override():
        yield test_session

    app.dependency_overrides[get_session] = override
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def cleanup_database(test_session):
    yield
    for table in reversed(Base.metadata.sorted_tables):
        await test_session.execute(table.delete())
    await test_session.commit()
```

`server/tests/test_health.py`:

```python
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "service": "voice-store"}
```

- [ ] **Step 6: Run, then verify alembic against SQLite, commit**

```bash
cd server && uv sync --quiet && uv run pytest -q
DATABASE_URL=sqlite+aiosqlite:///./alembic_check.db uv run alembic upgrade head && rm -f alembic_check.db
cd .. && git add server && git commit -m "feat(server): models, db, app skeleton, alembic initial migration, test harness"
```

Expected: `1 passed`; alembic prints `Running upgrade  -> 0001, initial tables`.

---

### Task 3: Auth — password service, token service, bearer dependency, `/auth` routes

**Files:**
- Create: `server/src/voice_store/services/{__init__,password_service,token_service}.py`, `server/src/voice_store/utils/{__init__,auth}.py`, `server/src/voice_store/types/{__init__,auth}.py`, `server/src/voice_store/routes/{__init__,auth}.py`
- Modify: `server/src/voice_store/main.py` (include routers)
- Test: `server/tests/test_auth.py`

**Interfaces:**
- Produces:
  - `password_service.hash_password(pw) -> str`, `verify_password(pw, hashed) -> bool`, `validate_password(pw)` raises `HTTPException(400)` if `< 12` chars, `async set_password(session, user, pw)` (hash + delete all tokens + commit).
  - `token_service.issue(session, user, name) -> tuple[str, Token]` (raw once), `hash_token(raw) -> str`.
  - `utils.auth.get_current_user(credentials=Depends(HTTPBearer(auto_error=False)), session) -> User` — 401 `{"detail": "Could not validate credentials"}` + `WWW-Authenticate: Bearer`; 403 inactive.
  - Routes under `/auth` (tag `Authentication`): `POST /register`, `POST /login`, `GET /tokens`, `DELETE /tokens/{id}`, `POST /change-password`.
  - Env `REGISTRATION_OPEN` read at request time (so tests can flip it with monkeypatch).

- [ ] **Step 1: Write failing tests** — `server/tests/test_auth.py`:

```python
import pytest

REG = {"username": "alice", "password": "correct-horse-battery"}


async def register(client, monkeypatch, payload=REG):
    monkeypatch.setenv("REGISTRATION_OPEN", "true")
    return await client.post("/auth/register", json=payload)


async def login(client, username="alice", password="correct-horse-battery", token_name=None):
    body = {"username": username, "password": password}
    if token_name:
        body["token_name"] = token_name
    return await client.post("/auth/login", json=body)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def test_register_gated_by_env(client, monkeypatch):
    monkeypatch.delenv("REGISTRATION_OPEN", raising=False)
    r = await client.post("/auth/register", json=REG)
    assert r.status_code == 403


async def test_register_login_and_token_roundtrip(client, monkeypatch):
    r = await register(client, monkeypatch)
    assert r.status_code == 201 and r.json()["username"] == "alice"
    r = await register(client, monkeypatch)
    assert r.status_code == 409
    r = await login(client, token_name="laptop")
    assert r.status_code == 200
    tok = r.json()
    assert tok["token"].startswith("vs_") and tok["name"] == "laptop"
    r = await client.get("/auth/tokens", headers=bearer(tok["token"]))
    assert [t["name"] for t in r.json()] == ["laptop"]
    assert "token" not in r.json()[0]


async def test_short_password_rejected(client, monkeypatch):
    r = await register(client, monkeypatch, {"username": "bob", "password": "short"})
    assert r.status_code == 400


async def test_bad_login(client, monkeypatch):
    await register(client, monkeypatch)
    r = await login(client, password="wrong-password-here")
    assert r.status_code == 401
    r = await login(client, username="nobody")
    assert r.status_code == 401


async def test_missing_or_unknown_token_401(client):
    r = await client.get("/auth/tokens")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.get("/auth/tokens", headers=bearer("vs_nope"))
    assert r.status_code == 401


async def test_delete_token_404_then_401(client, monkeypatch):
    await register(client, monkeypatch)
    tok = (await login(client)).json()
    r = await client.delete("/auth/tokens/9999", headers=bearer(tok["token"]))
    assert r.status_code == 404
    r = await client.delete(f"/auth/tokens/{tok['id']}", headers=bearer(tok["token"]))
    assert r.status_code == 204
    r = await client.get("/auth/tokens", headers=bearer(tok["token"]))
    assert r.status_code == 401


async def test_cannot_delete_other_users_token(client, monkeypatch):
    await register(client, monkeypatch)
    await register(client, monkeypatch, {"username": "bob", "password": "another-long-password"})
    a = (await login(client)).json()
    b = (await login(client, "bob", "another-long-password")).json()
    r = await client.delete(f"/auth/tokens/{a['id']}", headers=bearer(b["token"]))
    assert r.status_code == 404


async def test_change_password_drops_all_tokens(client, monkeypatch):
    await register(client, monkeypatch)
    t1 = (await login(client)).json()["token"]
    t2 = (await login(client)).json()["token"]
    r = await client.post("/auth/change-password",
                          json={"current_password": REG["password"], "new_password": "brand-new-password-1"},
                          headers=bearer(t1))
    assert r.status_code == 204
    for t in (t1, t2):
        assert (await client.get("/auth/tokens", headers=bearer(t))).status_code == 401
    assert (await login(client, password="brand-new-password-1")).status_code == 200


async def test_change_password_wrong_current(client, monkeypatch):
    await register(client, monkeypatch)
    t = (await login(client)).json()["token"]
    r = await client.post("/auth/change-password",
                          json={"current_password": "nope-nope-nope-nope", "new_password": "brand-new-password-1"},
                          headers=bearer(t))
    assert r.status_code == 400
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_auth.py -q` → 404s / import errors.

- [ ] **Step 3: Implement**

`services/password_service.py`:

```python
"""Single owner of password writes."""

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.models import Token, User

MIN_LENGTH = 12
_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _ctx.verify(password, hashed)


def validate_password(password: str) -> None:
    if len(password) < MIN_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"password must be at least {MIN_LENGTH} characters")


async def set_password(session: AsyncSession, user: User, password: str) -> None:
    """Hash, store, and drop every token the user holds."""
    validate_password(password)
    user.hashed_password = hash_password(password)
    await session.execute(delete(Token).where(Token.user_id == user.id))
    await session.commit()
```

`services/token_service.py`:

```python
import hashlib
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.models import Token, User


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def issue(session: AsyncSession, user: User, name: str) -> tuple[str, Token]:
    raw = "vs_" + secrets.token_urlsafe(32)
    token = Token(user_id=user.id, name=name, token_hash=hash_token(raw))
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return raw, token
```

`utils/auth.py`:

```python
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import get_session
from voice_store.models import Token, User
from voice_store.services.token_service import hash_token

bearer = HTTPBearer(auto_error=False)
_CREDENTIALS = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                             headers={"WWW-Authenticate": "Bearer"})


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                           session: AsyncSession = Depends(get_session)) -> User:
    if credentials is None or not credentials.credentials:
        raise _CREDENTIALS
    row = (await session.execute(
        select(Token, User).join(User, User.id == Token.user_id).where(Token.token_hash == hash_token(credentials.credentials))
    )).first()
    if row is None:
        raise _CREDENTIALS
    token, user = row
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")
    now = datetime.now(timezone.utc)
    last = token.last_used_at
    if last is None or (now - last.replace(tzinfo=timezone.utc)) > timedelta(minutes=1):
        token.last_used_at = now
        await session.commit()
    return user


async def get_current_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                            session: AsyncSession = Depends(get_session)) -> Token:
    if credentials is None:
        raise _CREDENTIALS
    token = (await session.execute(select(Token).where(Token.token_hash == hash_token(credentials.credentials)))).scalar_one_or_none()
    if token is None:
        raise _CREDENTIALS
    return token
```

`types/auth.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Register(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class Login(BaseModel):
    username: str
    password: str
    token_name: str | None = Field(default=None, max_length=64)


class TokenIssued(BaseModel):
    token: str
    id: int
    name: str


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime | None
    last_used_at: datetime | None


class ChangePassword(BaseModel):
    current_password: str
    new_password: str
```

`routes/auth.py`:

```python
import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import get_session
from voice_store.models import Token, User
from voice_store.services import password_service, token_service
from voice_store.types.auth import ChangePassword, Login, Register, TokenIssued, TokenOut, UserOut
from voice_store.utils.auth import get_current_user

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


def _registration_open() -> bool:
    return os.getenv("REGISTRATION_OPEN", "false").lower() in ("1", "true", "yes", "on")


@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: Register, session: AsyncSession = Depends(get_session)):
    if not _registration_open():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="registration is closed")
    password_service.validate_password(body.password)
    if (await session.execute(select(User).where(User.username == body.username))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username taken")
    user = User(username=body.username, hashed_password=password_service.hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@auth_router.post("/login", response_model=TokenIssued)
async def login(body: Login, session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if user is None or not password_service.verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")
    raw, token = await token_service.issue(session, user, body.token_name or "default")
    return TokenIssued(token=raw, id=token.id, name=token.name)


@auth_router.get("/tokens", response_model=list[TokenOut])
async def list_tokens(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Token).where(Token.user_id == user.id).order_by(Token.id))).scalars().all()


@auth_router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token(token_id: int, user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    token = (await session.execute(select(Token).where(Token.id == token_id, Token.user_id == user.id))).scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    await session.delete(token)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@auth_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(body: ChangePassword, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    if not password_service.verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current password is wrong")
    await password_service.set_password(session, user, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

`routes/__init__.py`: `from voice_store.routes.auth import auth_router` + `__all__`. `main.py`: add `from voice_store.routes import auth_router` and `app.include_router(auth_router)` after the app is created. `services/__init__.py`, `utils/__init__.py`, `types/__init__.py`: empty.

- [ ] **Step 4: Run, commit**

```bash
uv run pytest -q
git add server && git commit -m "feat(server): username/password accounts with opaque bearer tokens"
```

Expected: 10 passed.

---

### Task 4: Bootstrap script `create_user`

**Files:**
- Create: `server/src/voice_store/scripts/{__init__,create_user}.py`
- Test: `server/tests/test_create_user.py`

**Interfaces:**
- Produces: `async create_or_reset(session, username, password, reset) -> User` (raises `ValueError` on exists-without-reset / missing-with-reset / short password); Typer command `python -m voice_store.scripts.create_user --username U [--password P] [--reset-password]`.

- [ ] **Step 1: Test**

```python
import pytest

from voice_store.scripts.create_user import create_or_reset
from voice_store.services.password_service import verify_password


async def test_create_then_reset(test_session):
    u = await create_or_reset(test_session, "carol", "a-long-enough-password", reset=False)
    assert u.username == "carol" and verify_password("a-long-enough-password", u.hashed_password)
    with pytest.raises(ValueError):
        await create_or_reset(test_session, "carol", "another-long-password", reset=False)
    u2 = await create_or_reset(test_session, "carol", "another-long-password", reset=True)
    assert u2.id == u.id and verify_password("another-long-password", u2.hashed_password)
    with pytest.raises(ValueError):
        await create_or_reset(test_session, "dave", "x", reset=False)
    with pytest.raises(ValueError):
        await create_or_reset(test_session, "nobody", "another-long-password", reset=True)
```

- [ ] **Step 2: Implement**

```python
"""Headless bootstrap: create a user or reset a password. Requires DB_* env (or DATABASE_URL).

    python -m voice_store.scripts.create_user --username bub            # prompts for password
    python -m voice_store.scripts.create_user --username bub --reset-password
"""

import asyncio
import getpass

import typer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import SessionLocal, engine
from voice_store.models import User
from voice_store.services import password_service

app = typer.Typer(add_completion=False)


async def create_or_reset(session: AsyncSession, username: str, password: str, reset: bool) -> User:
    if len(password) < password_service.MIN_LENGTH:
        raise ValueError(f"password must be at least {password_service.MIN_LENGTH} characters")
    user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if reset:
        if user is None:
            raise ValueError(f"no user {username!r}")
        await password_service.set_password(session, user, password)
        return user
    if user is not None:
        raise ValueError(f"user {username!r} exists (use --reset-password)")
    user = User(username=username, hashed_password=password_service.hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _run(username: str, password: str, reset: bool) -> User:
    try:
        async with SessionLocal() as session:
            return await create_or_reset(session, username, password, reset)
    finally:
        await engine.dispose()


@app.command()
def main(username: str = typer.Option(...), password: str | None = typer.Option(None),
         reset_password: bool = typer.Option(False, "--reset-password")):
    if not password:
        password = getpass.getpass("Password: ")
    try:
        user = asyncio.run(_run(username, password, reset_password))
    except ValueError as e:
        typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.secho(f"{'reset' if reset_password else 'created'} {user.username} (id={user.id})", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git commit -m "feat(server): create_user bootstrap script"`.

---

### Task 5: `/me` routes

**Files:**
- Create: `server/src/voice_store/routes/me.py`, `server/src/voice_store/types/me.py`
- Modify: `routes/__init__.py`, `main.py`
- Test: `server/tests/test_me.py`

**Interfaces:**
- `GET /me` → `{username, processed_through, profile_contexts, corpus_count, latest_corpus_ts}`; `PUT /me/processed-through {ts}` → `{processed_through}`; 422 if not `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` or older than current.
- Test helper module `server/tests/helpers.py` with `register_and_login(client, monkeypatch, username="alice") -> headers` reused by later tasks.

- [ ] **Step 1: Tests** — `tests/helpers.py`:

```python
async def register_and_login(client, monkeypatch, username="alice", password="correct-horse-battery"):
    monkeypatch.setenv("REGISTRATION_OPEN", "true")
    r = await client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    r = await client.post("/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {r.json()['token']}"}
```

`tests/test_me.py`:

```python
from tests.helpers import register_and_login


async def test_me_empty(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    r = await client.get("/me", headers=h)
    assert r.status_code == 200
    assert r.json() == {"username": "alice", "processed_through": None, "profile_contexts": [],
                        "corpus_count": 0, "latest_corpus_ts": None}


async def test_processed_through_monotonic(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    r = await client.put("/me/processed-through", json={"ts": "2026-08-26T19:59:03Z"}, headers=h)
    assert r.status_code == 200 and r.json()["processed_through"] == "2026-08-26T19:59:03Z"
    r = await client.put("/me/processed-through", json={"ts": "2026-08-20T00:00:00Z"}, headers=h)
    assert r.status_code == 422
    r = await client.put("/me/processed-through", json={"ts": "yesterday"}, headers=h)
    assert r.status_code == 422
    assert (await client.get("/me", headers=h)).json()["processed_through"] == "2026-08-26T19:59:03Z"
```

- [ ] **Step 2: Implement**

`types/me.py`:

```python
from pydantic import BaseModel, Field

TS_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


class Me(BaseModel):
    username: str
    processed_through: str | None
    profile_contexts: list[str]
    corpus_count: int
    latest_corpus_ts: str | None


class ProcessedThrough(BaseModel):
    ts: str = Field(pattern=TS_PATTERN)


class ProcessedThroughOut(BaseModel):
    processed_through: str
```

`routes/me.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import get_session
from voice_store.models import CorpusItem, Profile, User
from voice_store.types.me import Me, ProcessedThrough, ProcessedThroughOut
from voice_store.utils.auth import get_current_user

me_router = APIRouter(prefix="/me", tags=["Me"])


@me_router.get("", response_model=Me)
async def me(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    contexts = (await session.execute(
        select(distinct(Profile.context)).where(Profile.user_id == user.id).order_by(Profile.context))).scalars().all()
    count, latest = (await session.execute(
        select(func.count(CorpusItem.id), func.max(CorpusItem.ts)).where(CorpusItem.user_id == user.id))).one()
    return Me(username=user.username, processed_through=user.processed_through, profile_contexts=list(contexts),
              corpus_count=count, latest_corpus_ts=latest)


@me_router.put("/processed-through", response_model=ProcessedThroughOut)
async def set_processed_through(body: ProcessedThrough, user: User = Depends(get_current_user),
                                session: AsyncSession = Depends(get_session)):
    if user.processed_through and body.ts < user.processed_through:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"ts {body.ts} is older than current {user.processed_through}")
    user.processed_through = body.ts
    await session.commit()
    return ProcessedThroughOut(processed_through=user.processed_through)
```

Wire `me_router` into `routes/__init__.py` and `main.py`.

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git commit -m "feat(server): /me and processed-through marker"`.

---

### Task 6: Profiles — vendored `profile`/`merge`, versioned PUT, render

**Files:**
- Create: `server/src/voice_store/vendor/{__init__,profile,merge}.py`, `server/src/voice_store/services/profile_service.py`, `server/src/voice_store/routes/profiles.py`, `server/src/voice_store/types/profiles.py`
- Modify: `routes/__init__.py`, `main.py`
- Test: `server/tests/test_profiles.py`

**Interfaces:**
- `profile_service.current(session, user_id, ctx) -> Profile | None`, `create_version(session, user_id, ctx, body, source, expected_version) -> Profile` raising `StaleVersion(current)`; `parse_if_match(header) -> int` (strips quotes; `None` → 428).
- Routes under `/profiles` (tag `Profiles`) per spec table. `GET /profiles/{ctx}` returns `PlainTextResponse` media type `text/markdown`, headers `ETag: "<v>"`, `X-Version: <v>`.
- Vendor files: `cp client/voicectl/profile.py server/src/voice_store/vendor/profile.py` then prepend exactly three header lines:

```python
# VENDORED from client/voicectl/profile.py - do not edit here.
# scripts/check_vendor.sh fails CI if this drifts from the client copy.
#
```

Same for `merge.py`. `merge.py` imports `from .profile import ...` — that relative import works inside `vendor/` unchanged.

- [ ] **Step 1: Tests**

```python
from tests.helpers import register_and_login

CORE = """---
voice: core
owner: alice
purpose: test
status: personal
---

# Core

## Mechanics
- **trait one** - keep.

## Flagged overuse (tendencies to watch)
- x.

## AI-tells
- no em-dashes.

## Provenance & sync
- Processed through: none
- Repo-synced through: none
- Changelog:
  - seeded.
"""

BLOG = """---
voice: blog
owner: alice
purpose: blog
status: personal
extends: core
---

Blog preamble.

## Voice rules
- be funny.
"""

MD = {"Content-Type": "text/markdown"}


async def test_profile_create_version_chain_and_conflicts(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    assert (await client.get("/profiles/core", headers=h)).status_code == 404
    r = await client.put("/profiles/core", content=CORE, headers={**h, **MD})
    assert r.status_code == 428
    r = await client.put("/profiles/core", content=CORE, headers={**h, **MD, "If-Match": '"0"'})
    assert r.status_code == 200 and r.json() == {"context": "core", "version": 1}
    r = await client.get("/profiles/core", headers=h)
    assert r.status_code == 200 and r.text == CORE and r.headers["etag"] == '"1"' and r.headers["x-version"] == "1"
    r = await client.put("/profiles/core", content=CORE + "\n", headers={**h, **MD, "If-Match": "0"})
    assert r.status_code == 409 and r.json()["detail"]["current_version"] == 1
    r = await client.put("/profiles/core", content=CORE + "\n", headers={**h, **MD, "If-Match": "1", "X-Source": "updater"})
    assert r.status_code == 200 and r.json()["version"] == 2
    r = await client.get("/profiles/core/versions", headers=h)
    assert [(v["version"], v["source"]) for v in r.json()] == [(2, "updater"), (1, "user")]
    r = await client.get("/profiles/core/versions/1", headers=h)
    assert r.text == CORE
    r = await client.get("/profiles", headers=h)
    assert r.json() == [{"context": "core", "version": 2, "created_at": r.json()[0]["created_at"]}]


async def test_core_validation_422(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    r = await client.put("/profiles/core", content="# not a core\n", headers={**h, **MD, "If-Match": "0"})
    assert r.status_code == 422 and "missing required section" in str(r.json()["detail"])
    r = await client.put("/profiles/blog", content="# anything goes for overlays\n", headers={**h, **MD, "If-Match": "0"})
    assert r.status_code == 200


async def test_render_and_context_validation(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    assert (await client.get("/profiles/blog/render", headers=h)).status_code == 404
    await client.put("/profiles/core", content=CORE, headers={**h, **MD, "If-Match": "0"})
    await client.put("/profiles/blog", content=BLOG, headers={**h, **MD, "If-Match": "0"})
    r = await client.get("/profiles/blog/render", headers=h)
    assert r.status_code == 200 and "voice: blog" in r.text and "trait one" in r.text and "be funny" in r.text
    r = await client.put("/profiles/Bad Name", content="x", headers={**h, **MD, "If-Match": "0"})
    assert r.status_code == 422


async def test_profiles_are_per_user(client, monkeypatch):
    a = await register_and_login(client, monkeypatch, "alice")
    b = await register_and_login(client, monkeypatch, "bob")
    await client.put("/profiles/core", content=CORE, headers={**a, **MD, "If-Match": "0"})
    assert (await client.get("/profiles/core", headers=b)).status_code == 404
```

- [ ] **Step 2: Implement**

`services/profile_service.py`:

```python
import re

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.models import Profile

CONTEXT_RE = re.compile(r"^[a-z0-9-]{1,32}$")


class StaleVersion(Exception):
    def __init__(self, current: int):
        self.current = current


def validate_context(ctx: str) -> str:
    if not CONTEXT_RE.match(ctx):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="context must match [a-z0-9-]{1,32}")
    return ctx


def parse_if_match(header: str | None) -> int:
    if header is None:
        raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="If-Match header required")
    try:
        return int(header.strip().strip('"'))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="If-Match must be an integer version")


async def current_version(session: AsyncSession, user_id: int, ctx: str) -> int:
    v = (await session.execute(select(func.max(Profile.version)).where(Profile.user_id == user_id, Profile.context == ctx))).scalar()
    return v or 0


async def current(session: AsyncSession, user_id: int, ctx: str) -> Profile | None:
    return (await session.execute(
        select(Profile).where(Profile.user_id == user_id, Profile.context == ctx).order_by(Profile.version.desc()).limit(1)
    )).scalar_one_or_none()


async def create_version(session: AsyncSession, user_id: int, ctx: str, body: str, source: str, expected: int) -> Profile:
    cur = await current_version(session, user_id, ctx)
    if cur != expected:
        raise StaleVersion(cur)
    row = Profile(user_id=user_id, context=ctx, version=cur + 1, body=body, source=source)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
```

`types/profiles.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class ProfileSummary(BaseModel):
    context: str
    version: int
    created_at: datetime | None


class ProfileWritten(BaseModel):
    context: str
    version: int


class VersionSummary(BaseModel):
    version: int
    source: str
    created_at: datetime | None
    size: int
```

`routes/profiles.py`:

```python
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import get_session
from voice_store.models import Profile, User
from voice_store.services import profile_service as ps
from voice_store.types.profiles import ProfileSummary, ProfileWritten, VersionSummary
from voice_store.utils.auth import get_current_user
from voice_store.vendor.merge import RenderError, render
from voice_store.vendor.profile import validate_core

profiles_router = APIRouter(prefix="/profiles", tags=["Profiles"])
SOURCES = ("user", "updater", "seed")


def _md(body: str, version: int) -> PlainTextResponse:
    return PlainTextResponse(body, media_type="text/markdown",
                            headers={"ETag": f'"{version}"', "X-Version": str(version)})


@profiles_router.get("", response_model=list[ProfileSummary])
async def list_profiles(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    sub = (select(Profile.context, func.max(Profile.version).label("v"))
           .where(Profile.user_id == user.id).group_by(Profile.context).subquery())
    rows = (await session.execute(
        select(Profile).join(sub, (Profile.context == sub.c.context) & (Profile.version == sub.c.v))
        .where(Profile.user_id == user.id).order_by(Profile.context))).scalars().all()
    return [ProfileSummary(context=r.context, version=r.version, created_at=r.created_at) for r in rows]


@profiles_router.get("/{ctx}", response_class=PlainTextResponse)
async def get_profile(ctx: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ps.validate_context(ctx)
    row = await ps.current(session, user.id, ctx)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such profile")
    return _md(row.body, row.version)


@profiles_router.put("/{ctx}", response_model=ProfileWritten)
async def put_profile(ctx: str, request: Request, if_match: str | None = Header(default=None, alias="If-Match"),
                      x_source: str = Header(default="user", alias="X-Source"),
                      user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ps.validate_context(ctx)
    expected = ps.parse_if_match(if_match)
    if x_source not in SOURCES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"X-Source must be one of {SOURCES}")
    body = (await request.body()).decode("utf-8")
    if not body.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty body")
    if ctx == "core":
        problems = validate_core(body)
        if problems:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problems)
    try:
        row = await ps.create_version(session, user.id, ctx, body, x_source, expected)
    except ps.StaleVersion as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"current_version": e.current})
    return ProfileWritten(context=row.context, version=row.version)


@profiles_router.get("/{ctx}/versions", response_model=list[VersionSummary])
async def list_versions(ctx: str, limit: int = Query(default=50, ge=1, le=500), before: int | None = Query(default=None),
                        user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ps.validate_context(ctx)
    q = select(Profile).where(Profile.user_id == user.id, Profile.context == ctx)
    if before is not None:
        q = q.where(Profile.version < before)
    rows = (await session.execute(q.order_by(Profile.version.desc()).limit(limit))).scalars().all()
    return [VersionSummary(version=r.version, source=r.source, created_at=r.created_at, size=len(r.body)) for r in rows]


@profiles_router.get("/{ctx}/versions/{n}", response_class=PlainTextResponse)
async def get_version(ctx: str, n: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ps.validate_context(ctx)
    row = (await session.execute(select(Profile).where(Profile.user_id == user.id, Profile.context == ctx,
                                                       Profile.version == n))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no such version")
    return _md(row.body, row.version)


@profiles_router.get("/{ctx}/render", response_class=PlainTextResponse)
async def render_profile(ctx: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    ps.validate_context(ctx)
    core = await ps.current(session, user.id, "core")
    overlay = await ps.current(session, user.id, ctx)
    if core is None or overlay is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="core or overlay missing")
    try:
        out = render(core.body, overlay.body, ctx)
    except RenderError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return PlainTextResponse(out, media_type="text/markdown")
```

Route order matters: declare `/{ctx}/versions`, `/{ctx}/versions/{n}`, `/{ctx}/render` — FastAPI matches by path shape, so `/{ctx}` (GET) does not swallow them; keep as written.

Vendor step:

```bash
mkdir -p server/src/voice_store/vendor && touch server/src/voice_store/vendor/__init__.py
for m in profile merge; do
  { printf '# VENDORED from client/voicectl/%s.py - do not edit here.\n# scripts/check_vendor.sh fails CI if this drifts from the client copy.\n#\n' "$m"
    cat "client/voicectl/$m.py"; } > "server/src/voice_store/vendor/$m.py"
done
bash scripts/check_vendor.sh && echo vendor-ok
```

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git add -A && git commit -m "feat(server): versioned profiles with If-Match, history, render"`.

---

### Task 7: Corpus routes

**Files:**
- Create: `server/src/voice_store/services/corpus_service.py`, `server/src/voice_store/routes/corpus.py`, `server/src/voice_store/types/corpus.py`
- Modify: `routes/__init__.py`, `main.py`
- Test: `server/tests/test_corpus.py`

**Interfaces:**
- `corpus_service.sha(ts, text)`, `add_batch(session, user_id, items) -> (inserted, skipped)` — inserts rows whose sha is not already present for the user, in one transaction; `list_after(session, user_id, after_id, since, limit) -> list[CorpusItem]`.
- `POST /corpus` body `list[CorpusIn]` (max 1000) → `{inserted, skipped}`; `GET /corpus?since&after_id&limit` → `{items, next_after_id}`.

- [ ] **Step 1: Tests**

```python
from tests.helpers import register_and_login


def items(n, start=0, prefix="msg"):
    return [{"ts": f"2026-08-{(i % 28) + 1:02d}T00:00:{i % 60:02d}Z", "text": f"{prefix} {i}", "machine": "laptop"}
            for i in range(start, start + n)]


async def test_batch_idempotent_and_paged(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    r = await client.post("/corpus", json=items(5), headers=h)
    assert r.status_code == 200 and r.json() == {"inserted": 5, "skipped": 0}
    r = await client.post("/corpus", json=items(7), headers=h)
    assert r.json() == {"inserted": 2, "skipped": 5}
    r = await client.get("/corpus", params={"limit": 3}, headers=h)
    body = r.json()
    assert [i["text"] for i in body["items"]] == ["msg 0", "msg 1", "msg 2"] and body["next_after_id"] == body["items"][-1]["id"]
    r = await client.get("/corpus", params={"after_id": body["next_after_id"], "limit": 100}, headers=h)
    assert [i["text"] for i in r.json()["items"]] == ["msg 3", "msg 4", "msg 5", "msg 6"] and r.json()["next_after_id"] is None
    r = await client.get("/corpus", params={"since": "2026-08-06T00:00:00Z"}, headers=h)
    assert [i["text"] for i in r.json()["items"]] == ["msg 5", "msg 6"]
    me = (await client.get("/me", headers=h)).json()
    assert me["corpus_count"] == 7 and me["latest_corpus_ts"] == "2026-08-07T00:00:06Z"


async def test_malformed_batch_is_atomic(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    bad = items(2) + [{"ts": "not-a-ts", "text": "x"}]
    r = await client.post("/corpus", json=bad, headers=h)
    assert r.status_code == 422
    assert (await client.get("/me", headers=h)).json()["corpus_count"] == 0


async def test_batch_size_cap(client, monkeypatch):
    h = await register_and_login(client, monkeypatch)
    r = await client.post("/corpus", json=items(1001), headers=h)
    assert r.status_code == 422


async def test_corpus_is_per_user(client, monkeypatch):
    a = await register_and_login(client, monkeypatch, "alice")
    b = await register_and_login(client, monkeypatch, "bob")
    await client.post("/corpus", json=items(3), headers=a)
    assert (await client.get("/corpus", headers=b)).json()["items"] == []
    # same content from bob is a separate row (per-user sha uniqueness)
    assert (await client.post("/corpus", json=items(3), headers=b)).json()["inserted"] == 3
```

- [ ] **Step 2: Implement**

`types/corpus.py`:

```python
from pydantic import BaseModel, Field

from voice_store.types.me import TS_PATTERN


class CorpusIn(BaseModel):
    ts: str = Field(pattern=TS_PATTERN)
    text: str = Field(min_length=1)
    machine: str | None = Field(default=None, max_length=64)


class BatchResult(BaseModel):
    inserted: int
    skipped: int


class CorpusOut(BaseModel):
    id: int
    ts: str
    text: str
    machine: str | None


class CorpusPage(BaseModel):
    items: list[CorpusOut]
    next_after_id: int | None
```

`services/corpus_service.py`:

```python
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.models import CorpusItem


def sha(ts: str, text: str) -> str:
    return hashlib.sha256(f"{ts}\n{text}".encode("utf-8")).hexdigest()


async def add_batch(session: AsyncSession, user_id: int, items: list) -> tuple[int, int]:
    wanted = {sha(i.ts, i.text): i for i in items}
    existing = set((await session.execute(
        select(CorpusItem.sha).where(CorpusItem.user_id == user_id, CorpusItem.sha.in_(list(wanted))))).scalars().all())
    fresh = [CorpusItem(user_id=user_id, ts=i.ts, text=i.text, machine=i.machine, sha=s)
             for s, i in wanted.items() if s not in existing]
    session.add_all(fresh)
    await session.commit()
    return len(fresh), len(items) - len(fresh)


async def list_after(session: AsyncSession, user_id: int, after_id: int | None, since: str | None, limit: int):
    q = select(CorpusItem).where(CorpusItem.user_id == user_id)
    if since:
        q = q.where(CorpusItem.ts > since)
    if after_id is not None:
        q = q.where(CorpusItem.id > after_id)
    return (await session.execute(q.order_by(CorpusItem.ts, CorpusItem.id).limit(limit))).scalars().all()
```

Note on ordering + paging: `after_id` is only a strict cursor when ids increase with ts. Inserts happen in `ts` order per batch but a later batch from another machine can carry older `ts`. So `GET /corpus` pages by `id` when `after_id` is given (order by `id`) and by `ts` when only `since` is given. Implement: if `after_id is not None`: `order_by(CorpusItem.id)`, else `order_by(CorpusItem.ts, CorpusItem.id)`. `next_after_id` = last item's id when `len(items) == limit`, else `None`. Adjust `test_batch_idempotent_and_paged`'s expectations accordingly (ids are insertion order there, so the listed texts are unchanged).

`routes/corpus.py`:

```python
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voice_store.db import get_session
from voice_store.models import User
from voice_store.services import corpus_service as cs
from voice_store.types.corpus import BatchResult, CorpusIn, CorpusOut, CorpusPage
from voice_store.utils.auth import get_current_user

corpus_router = APIRouter(prefix="/corpus", tags=["Corpus"])
MAX_BATCH = 1000


@corpus_router.post("", response_model=BatchResult)
async def add(items: list[CorpusIn] = Body(...), user: User = Depends(get_current_user),
              session: AsyncSession = Depends(get_session)):
    if len(items) > MAX_BATCH:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"at most {MAX_BATCH} items per batch")
    inserted, skipped = await cs.add_batch(session, user.id, items)
    return BatchResult(inserted=inserted, skipped=skipped)


@corpus_router.get("", response_model=CorpusPage)
async def page(since: str | None = Query(default=None), after_id: int | None = Query(default=None),
               limit: int = Query(default=1000, ge=1, le=1000), user: User = Depends(get_current_user),
               session: AsyncSession = Depends(get_session)):
    rows = await cs.list_after(session, user.id, after_id, since, limit)
    out = [CorpusOut(id=r.id, ts=r.ts, text=r.text, machine=r.machine) for r in rows]
    return CorpusPage(items=out, next_after_id=out[-1].id if len(out) == limit else None)
```

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git commit -m "feat(server): append-only corpus with idempotent batches and paging"`.

---

### Task 8: Client — strip git store; `paths`, `config`, `api.py`, token/state files

**Files:**
- Modify: `client/pyproject.toml` (add `httpx>=0.28`; dev group adds `voice-store` path dep), `client/voicectl/paths.py`, `client/voicectl/config.py`
- Rewrite: `client/voicectl/store.py` (token + state files + `mode()`, no git)
- Create: `client/voicectl/api.py`
- Delete: git-store tests in `client/tests/test_store.py` (keep only `test_mode_local_only_without_git`-style logic rewritten), `test_cli.py` init-remote tests
- Test: `client/tests/test_api.py` (unit, with `httpx.MockTransport`), `client/tests/test_store.py` (rewritten)

**Interfaces:**
- `paths.token_path() = voice_dir()/"token"`, `state_path() = voice_dir()/".state.json"`, `config_path() = voice_dir()/"config.json"`, `templates_dir()` unchanged, `NON_OVERLAY = {"core.md","README.md","voice.md"}`.
- `config`: same `get/set/get_int/get_bool/all_values/DEFAULTS/ENV_ALIASES`, backed by `config.json`; `corpusSync` key **removed** entirely (`DEFAULTS = {"model","minCount","minInterval"}`).
- `store.Credentials(url, token, token_id)`; `store.load_credentials() -> Credentials | None`; `save_credentials(c)` (0600); `clear_credentials()`; `mode()`; `State` dataclass `{pushed_through_line:int, pulled_through_id:int|None, versions:dict, hashes:dict}` with `load_state()/save_state()`; `hostname()`, `owner_name()`, `scaffold` removed, `seed_templates(d, owner)` kept.
- `api.Api(url, token, timeout=30.0)`: `login(url, username, password, token_name) -> dict` (classmethod, no token), `logout(token_id)`, `me()`, `set_processed_through(ts)`, `list_profiles()`, `get_profile(ctx) -> (body, version)`, `put_profile(ctx, body, version, source) -> int`, `post_corpus(items) -> dict`, `get_corpus(after_id, limit) -> dict`, `render(ctx) -> str`. Errors: `ApiError(status, detail)`, subclasses `AuthError(401/403)`, `ConflictError(current_version)`, `NotFound`; `httpx.HTTPError` wrapped as `Offline`.

- [ ] **Step 1: Write failing tests**

`client/tests/test_api.py`:

```python
import json

import httpx
import pytest

from voicectl.api import Api, ApiError, AuthError, ConflictError, NotFound, Offline


def make(handler):
    return Api("http://srv/api", "vs_x", transport=httpx.MockTransport(handler))


def test_get_profile_returns_body_and_version():
    def h(req):
        assert req.headers["authorization"] == "Bearer vs_x" and req.url.path == "/api/profiles/core"
        return httpx.Response(200, text="BODY", headers={"ETag": '"7"'})
    assert make(h).get_profile("core") == ("BODY", 7)


def test_put_profile_conflict_and_success():
    def h(req):
        if req.headers["if-match"] == '"1"':
            return httpx.Response(409, json={"detail": {"current_version": 3}})
        assert req.headers["x-source"] == "updater"
        return httpx.Response(200, json={"context": "core", "version": 4})
    with pytest.raises(ConflictError) as e:
        make(h).put_profile("core", "x", 1, "updater")
    assert e.value.current_version == 3
    assert make(h).put_profile("core", "x", 3, "updater") == 4


def test_errors_map():
    for code, exc in ((401, AuthError), (403, AuthError), (404, NotFound), (500, ApiError)):
        api = make(lambda req, code=code: httpx.Response(code, json={"detail": "d"}))
        with pytest.raises(exc):
            api.me()
    def boom(req):
        raise httpx.ConnectError("down")
    with pytest.raises(Offline):
        make(boom).me()


def test_post_corpus_batches_of_1000():
    seen = []
    def h(req):
        seen.append(len(json.loads(req.content)))
        return httpx.Response(200, json={"inserted": 1, "skipped": 0})
    r = make(h).post_corpus([{"ts": "2026-01-01T00:00:00Z", "text": str(i)} for i in range(2500)])
    assert seen == [1000, 1000, 500] and r == {"inserted": 3, "skipped": 0}


def test_login_classmethod():
    def h(req):
        assert req.url.path == "/api/auth/login" and json.loads(req.content)["token_name"] == "box"
        return httpx.Response(200, json={"token": "vs_new", "id": 5, "name": "box"})
    assert Api.login("http://srv/api", "alice", "pw", "box", transport=httpx.MockTransport(h))["token"] == "vs_new"
```

`client/tests/test_store.py` (rewritten):

```python
import json
import stat

from voicectl import store


def test_mode_and_credentials_roundtrip(voice_env):
    assert store.mode() == "local-only" and store.load_credentials() is None
    store.save_credentials(store.Credentials("http://srv/api", "vs_abc", 3))
    assert store.mode() == "synced"
    c = store.load_credentials()
    assert (c.url, c.token, c.token_id) == ("http://srv/api", "vs_abc", 3)
    assert stat.S_IMODE((voice_env / "token").stat().st_mode) == 0o600
    store.clear_credentials()
    assert store.mode() == "local-only"


def test_state_roundtrip(voice_env):
    s = store.load_state()
    assert s.pushed_through_line == 0 and s.pulled_through_id is None and s.versions == {} and s.hashes == {}
    s.pushed_through_line = 12
    s.versions["core"] = 4
    store.save_state(s)
    assert json.loads((voice_env / ".state.json").read_text())["versions"] == {"core": 4}
    assert store.load_state().pushed_through_line == 12


def test_seed_templates_still_works(voice_env):
    (voice_env / "blog.md").unlink()
    assert store.seed_templates(voice_env, "alice") == ["blog.md", "chat.md"]
```

Config tests: rewrite `client/tests/test_config.py` for the JSON backend (same cases as before minus git; `set("corpusSync", ...)` → `KeyError`).

- [ ] **Step 2: Implement**

`paths.py` additions:

```python
def token_path() -> Path:
    return voice_dir() / "token"


def state_path() -> Path:
    return voice_dir() / ".state.json"


def config_path() -> Path:
    return voice_dir() / "config.json"
```

Remove `BACKUP_SUFFIX`, `store_branch()`. `NON_OVERLAY = {"core.md", "README.md", "voice.md"}`.

`config.py`:

```python
"""Per-machine tunables in ~/.madskillz/voice/config.json. Env aliases win."""

import json
import os

from . import paths

DEFAULTS: dict[str, str] = {"model": "opus", "minCount": "15", "minInterval": "720"}
ENV_ALIASES: dict[str, str] = {"model": "VOICE_SYNC_MODEL", "minCount": "VOICE_SYNC_MIN_COUNT",
                               "minInterval": "VOICE_SYNC_MIN_INTERVAL_SECONDS"}


class ConfigError(Exception):
    pass


def _read() -> dict:
    try:
        return json.loads(paths.config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get(key: str) -> str:
    if key not in DEFAULTS:
        raise KeyError(key)
    alias = ENV_ALIASES.get(key)
    if alias and os.environ.get(alias):
        return os.environ[alias]
    return str(_read().get(key, DEFAULTS[key]))


def set(key: str, value: str) -> None:  # noqa: A001
    if key not in DEFAULTS:
        raise KeyError(key)
    d = _read()
    d[key] = value
    paths.voice_dir().mkdir(parents=True, exist_ok=True)
    paths.config_path().write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


def get_bool(key: str) -> bool:
    return get(key).strip().lower() in ("1", "true", "yes", "on")


def get_int(key: str) -> int:
    return int(get(key))


def all_values() -> dict[str, str]:
    return {k: get(k) for k in DEFAULTS}
```

`api.py`:

```python
"""HTTP client for the voice-store service. Thin: one method per route, errors as exceptions."""

from __future__ import annotations

import httpx

BATCH = 1000


class ApiError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


class AuthError(ApiError):
    pass


class NotFound(ApiError):
    pass


class ConflictError(ApiError):
    def __init__(self, status: int, detail):
        super().__init__(status, detail)
        self.current_version = int(detail.get("current_version", 0)) if isinstance(detail, dict) else 0


class Offline(Exception):
    pass


def _raise(r: httpx.Response) -> None:
    if r.is_success:
        return
    try:
        detail = r.json().get("detail")
    except Exception:  # noqa: BLE001
        detail = r.text
    if r.status_code in (401, 403):
        raise AuthError(r.status_code, detail)
    if r.status_code == 404:
        raise NotFound(r.status_code, detail)
    if r.status_code == 409:
        raise ConflictError(r.status_code, detail)
    raise ApiError(r.status_code, detail)


class Api:
    def __init__(self, url: str, token: str, timeout: float = 30.0, transport=None):
        self.url = url.rstrip("/")
        self._c = httpx.Client(base_url=self.url, timeout=timeout, transport=transport,
                               headers={"Authorization": f"Bearer {token}"})

    def _call(self, method: str, path: str, **kw) -> httpx.Response:
        try:
            r = self._c.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise Offline(str(e)) from e
        _raise(r)
        return r

    @classmethod
    def login(cls, url: str, username: str, password: str, token_name: str, timeout: float = 30.0, transport=None) -> dict:
        try:
            r = httpx.Client(base_url=url.rstrip("/"), timeout=timeout, transport=transport).post(
                "/auth/login", json={"username": username, "password": password, "token_name": token_name})
        except httpx.HTTPError as e:
            raise Offline(str(e)) from e
        _raise(r)
        return r.json()

    def logout(self, token_id: int) -> None:
        try:
            self._call("DELETE", f"/auth/tokens/{token_id}")
        except NotFound:
            pass

    def me(self) -> dict:
        return self._call("GET", "/me").json()

    def set_processed_through(self, ts: str) -> str:
        return self._call("PUT", "/me/processed-through", json={"ts": ts}).json()["processed_through"]

    def list_profiles(self) -> list[dict]:
        return self._call("GET", "/profiles").json()

    def get_profile(self, ctx: str) -> tuple[str, int]:
        r = self._call("GET", f"/profiles/{ctx}")
        return r.text, int(r.headers["etag"].strip('"'))

    def put_profile(self, ctx: str, body: str, version: int, source: str = "user") -> int:
        r = self._call("PUT", f"/profiles/{ctx}", content=body.encode("utf-8"),
                       headers={"Content-Type": "text/markdown", "If-Match": f'"{version}"', "X-Source": source})
        return int(r.json()["version"])

    def post_corpus(self, items: list[dict]) -> dict:
        total = {"inserted": 0, "skipped": 0}
        for i in range(0, len(items), BATCH):
            r = self._call("POST", "/corpus", json=items[i:i + BATCH]).json()
            total["inserted"] += r["inserted"]
            total["skipped"] += r["skipped"]
        return total

    def get_corpus(self, after_id: int | None = None, limit: int = BATCH) -> dict:
        params = {"limit": limit}
        if after_id is not None:
            params["after_id"] = after_id
        return self._call("GET", "/corpus", params=params).json()

    def render(self, ctx: str) -> str:
        return self._call("GET", f"/profiles/{ctx}/render").text
```

`store.py` (full rewrite):

```python
"""Local voice dir bookkeeping: credentials, sync state, template seeding. No git."""

import json
import os
import socket
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import paths

LOCAL_ONLY_HINT = "local-only mode (no token); run 'voicectl login URL' to sync"


class StoreError(Exception):
    pass


@dataclass
class Credentials:
    url: str
    token: str
    token_id: int


@dataclass
class State:
    pushed_through_line: int = 0
    pulled_through_id: int | None = None
    versions: dict = field(default_factory=dict)
    hashes: dict = field(default_factory=dict)


def load_credentials() -> Credentials | None:
    try:
        lines = paths.token_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if len(lines) < 3:
        return None
    return Credentials(lines[0].strip(), lines[1].strip(), int(lines[2].strip()))


def save_credentials(c: Credentials) -> None:
    p = paths.token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"{c.url}\n{c.token}\n{c.token_id}\n")
    os.chmod(p, 0o600)


def clear_credentials() -> None:
    paths.token_path().unlink(missing_ok=True)


def mode() -> str:
    return "synced" if load_credentials() else "local-only"


def load_state() -> State:
    try:
        return State(**json.loads(paths.state_path().read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return State()


def save_state(s: State) -> None:
    paths.voice_dir().mkdir(parents=True, exist_ok=True)
    paths.state_path().write_text(json.dumps(asdict(s), indent=2) + "\n", encoding="utf-8")


def hostname() -> str:
    return socket.gethostname().split(".")[0]


def seed_templates(d: Path, owner: str) -> list[str]:
    src = paths.templates_dir()
    if not src.is_dir():
        raise StoreError(f"templates dir not found: {src}")
    seeded = []
    for t in sorted(src.glob("*.md")):
        dst = d / t.name
        if dst.exists():
            continue
        text = t.read_text(encoding="utf-8").replace("<handle>", owner).replace("status: template", "status: personal", 1)
        dst.write_text(text, encoding="utf-8")
        seeded.append(t.name)
    return seeded


def owner_name() -> str:
    import subprocess
    r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    return r.stdout.strip() or os.environ.get("USER") or "owner"
```

`client/pyproject.toml`:

```toml
[project]
name = "voicectl"
version = "0.2.0"
description = "Owner-voice pipeline CLI: corpus capture, core+overlay render, sync with the voice-store service."
requires-python = ">=3.11"
dependencies = ["httpx>=0.28"]

[project.scripts]
voicectl = "voicectl.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["voicectl"]

[dependency-groups]
dev = ["pytest>=8", "uvicorn>=0.30", "aiosqlite>=0.20", "voice-store"]

[tool.uv.sources]
voice-store = { path = "../server", editable = true }
```

Delete from `cli.py` everything that referenced git (`cmd_pull/push/sync/init/migrate` bodies get rewritten in Tasks 9-11; for this task make them print `not implemented` so the module imports). Delete `tests/test_cli.py` cases that used `--remote`.

- [ ] **Step 3: Run, commit** — `cd client && uv sync --quiet && uv run pytest -q` (expect only the rewritten files' tests + untouched profile/merge/corpus/update/gate tests; `test_sync_gate.py`'s sync tests are deleted here, gate tests stay). `git commit -m "refactor(client): drop git store; add HTTP api client, credentials and state files"`.

---

### Task 9: Client — `login`/`logout`/`whoami` + live-server test fixture

**Files:**
- Create: `client/tests/live_server.py` (fixture module imported by conftest), `client/tests/test_login.py`
- Modify: `client/tests/conftest.py` (register fixture), `client/voicectl/cli.py`

**Interfaces:**
- Fixture `live_server` (session scope): sets `DATABASE_URL=sqlite+aiosqlite:///<tmp>/live.db` and `REGISTRATION_OPEN=true` **before** importing `voice_store.main`, starts `uvicorn.Server` in a daemon thread on a free port, yields `base_url` `http://127.0.0.1:<port>/api`... — note the app has `root_path="/api"` which only affects docs/URL generation; routes are served at `/auth/login` etc. So the client base URL in tests is `http://127.0.0.1:<port>` and in production (behind the ingress that strips nothing and forwards `/api` to the pod) it is `https://voice.example/api`. **Ruling:** mount routes without prefix (as skill-matrix does); the ingress rewrites `/api/(.*)` → `/$1` — see Task 13. Client treats the URL as opaque.
- Fixture `account(live_server)` → `(username, password)` freshly registered via HTTP with a random suffix.
- CLI: `voicectl login URL [--username U] [--password-stdin]` (prompts otherwise) → writes credentials, seeds templates if the dir has no `core.md`, then runs `pull` (Task 10; stub prints nothing until then). `voicectl logout`. `voicectl whoami` prints `/me` fields.

- [ ] **Step 1: Fixture**

`client/tests/live_server.py`:

```python
import os
import socket
import threading
import time

import httpx
import pytest


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    db = tmp_path_factory.mktemp("srv") / "live.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db}"
    os.environ["REGISTRATION_OPEN"] = "true"
    import uvicorn
    from voice_store.main import app

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(url + "/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise RuntimeError("live server did not start")
    yield url
    server.should_exit = True
    t.join(timeout=5)


@pytest.fixture
def account(live_server):
    import secrets
    username = "u" + secrets.token_hex(4)
    password = "a-long-enough-password"
    r = httpx.post(live_server + "/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return username, password
```

`conftest.py`: add `from tests.live_server import live_server, account  # noqa: F401`.

- [ ] **Step 2: Tests** — `client/tests/test_login.py`:

```python
from voicectl import store
from voicectl.cli import main


def test_login_seeds_and_writes_token(voice_env, live_server, account, capsys, monkeypatch):
    (voice_env / "core.md").unlink()
    (voice_env / "blog.md").unlink()
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(account[1] + "\n"))
    assert main(["login", live_server, "--username", account[0], "--password-stdin"]) == 0
    c = store.load_credentials()
    assert c and c.url == live_server and c.token.startswith("vs_")
    assert (voice_env / "core.md").exists()
    assert "mode: synced" in capsys.readouterr().out
    assert main(["whoami"]) == 0
    assert f"username: {account[0]}" in capsys.readouterr().out
    assert main(["logout"]) == 0
    assert store.mode() == "local-only"
    # token is dead server-side too
    assert main(["whoami"]) == 1


def test_login_bad_password(voice_env, live_server, account, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("wrong-password-xx\n"))
    assert main(["login", live_server, "--username", account[0], "--password-stdin"]) == 1
    assert "bad credentials" in capsys.readouterr().err
```

- [ ] **Step 3: Implement in `cli.py`**

```python
def _api() -> "store.Credentials":
    c = store.load_credentials()
    if c is None:
        print(f"error: {store.LOCAL_ONLY_HINT}", file=sys.stderr)
        raise SystemExit(1)
    return c


def cmd_login(args) -> int:
    username = args.username or input("username: ")
    password = sys.stdin.readline().rstrip("\n") if args.password_stdin else getpass.getpass("password: ")
    try:
        tok = api.Api.login(args.url, username, password, store.hostname())
    except api.ApiError as e:
        print(f"error: {e.detail}", file=sys.stderr)
        return 1
    except api.Offline as e:
        print(f"error: cannot reach {args.url}: {e}", file=sys.stderr)
        return 1
    store.save_credentials(store.Credentials(args.url, tok["token"], tok["id"]))
    paths.voice_dir().mkdir(parents=True, exist_ok=True)
    if not paths.core_path().exists():
        seeded = store.seed_templates(paths.voice_dir(), store.owner_name())
        print(f"seeded: {', '.join(seeded) or 'nothing'}")
    print(f"mode: synced\nurl: {args.url}\nuser: {username}")
    return cmd_pull(args)  # Task 10 makes this real; until then cmd_pull returns 0


def cmd_logout(_args) -> int:
    c = store.load_credentials()
    if c:
        try:
            api.Api(c.url, c.token).logout(c.token_id)
        except (api.ApiError, api.Offline) as e:
            print(f"warning: server logout failed: {e}", file=sys.stderr)
        store.clear_credentials()
    print("logged out")
    return 0


def cmd_whoami(_args) -> int:
    c = _api()
    try:
        me = api.Api(c.url, c.token).me()
    except api.ApiError as e:
        print(f"error: {e.detail}", file=sys.stderr)
        return 1
    except api.Offline as e:
        print(f"error: offline: {e}", file=sys.stderr)
        return 1
    for k, v in me.items():
        print(f"{k}: {v}")
    return 0
```

Parsers: `login` (`url`, `--username`, `--password-stdin`), `logout`, `whoami`. Imports: `getpass`, `from . import api`.

- [ ] **Step 4: Run, commit** — `uv run pytest -q`; `git commit -m "feat(client): login/logout/whoami against a live server"`.

---

### Task 10: Client — `pull`, `push`, `sync`, `status`

**Files:**
- Create: `client/voicectl/sync.py` (rewrite), `client/tests/test_sync_http.py`
- Modify: `client/voicectl/cli.py`

**Interfaces:**
- `sync.pull(a: Api) -> dict` `{profiles: [ctx...], corpus_added: n, processed_through: ts|None}`; writes profiles atomically (tmp + rename) only after all GETs succeed; records `state.versions[ctx]` and `state.hashes[ctx] = sha256(body)`; appends corpus lines not present locally (dedupe via `corpus.entries` keys) and sets `pulled_through_id`; copies the server marker into the local core via `profile.set_marker(..., "processed", ts)` when the server has one.
- `sync.push_corpus(a, timeout=None) -> dict` `{inserted, skipped, lines}` for local lines after `pushed_through_line` (index into the raw file line list; the counter advances only after a 200).
- `sync.push_profiles(a) -> dict` `{created: [...], updated: [...], conflicts: [...]}`: for each local `*.md` not in `NON_OVERLAY`-minus-core (i.e. overlays **and** core): if the server has no such context → `PUT If-Match "0"`; else if it is an overlay and local sha ≠ `hashes[ctx]` → `PUT If-Match versions[ctx]`; core is never updated here. Conflicts collected, not raised.
- `sync.run() -> str` = pull, push_corpus, push_profiles; exit 2 if conflicts.
- `sync.status_info() -> dict` keys: `mode, url, username, processed_through_local, processed_through_remote, pending_since_processed, unpushed_lines, contexts, versions (ctx → {local, remote})`, `lock_held`, `config`.

- [ ] **Step 1: Tests** — `client/tests/test_sync_http.py`:

```python
import json

from voicectl import sync, store, paths
from voicectl.api import Api
from voicectl.cli import main
from voicectl.profile import get_marker
from tests.conftest import add_corpus


def logged_in(voice_env, live_server, account, monkeypatch):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(account[1] + "\n"))
    assert main(["login", live_server, "--username", account[0], "--password-stdin"]) == 0
    c = store.load_credentials()
    return Api(c.url, c.token)


def test_first_push_creates_profiles_and_uploads_corpus(voice_env, live_server, account, monkeypatch):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    add_corpus(voice_env, "2026-02-01T00:00:00Z", "hello")
    add_corpus(voice_env, "2026-02-02T00:00:00Z", "world")
    assert main(["push"]) == 0
    assert sorted(p["context"] for p in a.list_profiles()) == ["blog", "core"]
    assert a.me()["corpus_count"] == 2
    assert store.load_state().pushed_through_line == 2
    # second push is a no-op
    assert main(["push"]) == 0 and a.me()["corpus_count"] == 2


def test_overlay_edit_pushes_new_version_and_pull_overwrites(voice_env, live_server, account, monkeypatch):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    blog = voice_env / "blog.md"
    blog.write_text(blog.read_text() + "\n- new rule.\n")
    assert main(["push"]) == 0
    body, v = a.get_profile("blog")
    assert v == 2 and "new rule" in body
    # server-side edit (e.g. from another machine) is pulled down
    a.put_profile("blog", body + "\n- remote rule.\n", 2)
    assert main(["pull"]) == 0
    assert "remote rule" in blog.read_text() and store.load_state().versions["blog"] == 3


def test_pull_brings_remote_corpus_and_marker(voice_env, live_server, account, monkeypatch):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    a.post_corpus([{"ts": "2026-03-01T00:00:00Z", "text": "from other machine"}])
    a.set_processed_through("2026-03-01T00:00:00Z")
    assert main(["pull"]) == 0
    assert "from other machine" in (voice_env / "corpus.jsonl").read_text()
    assert get_marker((voice_env / "core.md").read_text(), "processed") == "2026-03-01T00:00:00Z"


def test_overlay_conflict_exit_2(voice_env, live_server, account, monkeypatch, capsys):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    body, v = a.get_profile("blog")
    a.put_profile("blog", body + "\n- remote first.\n", v)
    (voice_env / "blog.md").write_text(body + "\n- local second.\n")
    assert main(["push"]) == 2
    assert "conflict" in capsys.readouterr().out


def test_status_json(voice_env, live_server, account, monkeypatch, capsys):
    logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    capsys.readouterr()
    assert main(["status", "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["mode"] == "synced" and info["username"] == account[0] and info["unpushed_lines"] == 0
    assert info["versions"]["core"] == {"local": 1, "remote": 1}


def test_local_only_commands_print_hint(voice_env, capsys):
    assert main(["pull"]) == 0 and "local-only" in capsys.readouterr().out
    assert main(["push"]) == 0 and "local-only" in capsys.readouterr().out
```

- [ ] **Step 2: Implement `sync.py`**

```python
"""pull / push / status against the voice-store service."""

import hashlib
import json
import os
import tempfile

from . import api, config, paths, store
from .corpus import count_since, entries
from .profile import get_marker, set_marker


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_atomic(path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _local_profiles() -> dict[str, str]:
    d = paths.voice_dir()
    out = {}
    for p in sorted(d.glob("*.md")):
        if p.name in ("README.md", "voice.md"):
            continue
        out[p.stem] = p.read_text(encoding="utf-8")
    return out


def pull(a: api.Api) -> dict:
    state = store.load_state()
    fetched = {}
    for p in a.list_profiles():
        body, version = a.get_profile(p["context"])
        fetched[p["context"]] = (body, version)
    me = a.me()
    # all network done - now write
    for ctx, (body, version) in fetched.items():
        if ctx == "core" and me.get("processed_through"):
            try:
                body = set_marker(body, "processed", me["processed_through"])
            except ValueError:
                pass
        _write_atomic(paths.overlay_path(ctx) if ctx != "core" else paths.core_path(), body)
        state.versions[ctx] = version
        state.hashes[ctx] = _sha(body)
    known = {(e["ts"], e["text"]) for e in entries(paths.corpus_path())}
    added = 0
    after = state.pulled_through_id
    while True:
        page = a.get_corpus(after_id=after)
        with paths.corpus_path().open("a", encoding="utf-8") as f:
            for it in page["items"]:
                after = it["id"]
                if (it["ts"], it["text"]) in known:
                    continue
                f.write(json.dumps({"ts": it["ts"], "text": it["text"]}, ensure_ascii=False) + "\n")
                known.add((it["ts"], it["text"]))
                added += 1
        if page["next_after_id"] is None:
            break
    state.pulled_through_id = after
    store.save_state(state)
    return {"profiles": sorted(fetched), "corpus_added": added, "processed_through": me.get("processed_through")}


def push_corpus(a: api.Api) -> dict:
    state = store.load_state()
    try:
        lines = paths.corpus_path().read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    new = lines[state.pushed_through_line:]
    items = []
    for line in new:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(d.get("ts"), str) and isinstance(d.get("text"), str) and d["text"].strip():
            items.append({"ts": d["ts"], "text": d["text"], "machine": store.hostname()})
    result = {"inserted": 0, "skipped": 0, "lines": len(new)}
    if items:
        result.update(a.post_corpus(items))
    state.pushed_through_line = len(lines)
    store.save_state(state)
    return result


def push_profiles(a: api.Api) -> dict:
    state = store.load_state()
    remote = {p["context"]: p["version"] for p in a.list_profiles()}
    out = {"created": [], "updated": [], "conflicts": []}
    for ctx, body in _local_profiles().items():
        if ctx not in remote:
            v = a.put_profile(ctx, body, 0, "user")
            state.versions[ctx], state.hashes[ctx] = v, _sha(body)
            out["created"].append(ctx)
            continue
        if ctx == "core" or _sha(body) == state.hashes.get(ctx):
            continue
        try:
            v = a.put_profile(ctx, body, state.versions.get(ctx, remote[ctx]), "user")
        except api.ConflictError as e:
            out["conflicts"].append(f"{ctx} (server has v{e.current_version})")
            continue
        state.versions[ctx], state.hashes[ctx] = v, _sha(body)
        out["updated"].append(ctx)
    store.save_state(state)
    return out


def run(a: api.Api) -> tuple[str, int]:
    p = pull(a)
    c = push_corpus(a)
    r = push_profiles(a)
    msg = (f"sync: pulled {len(p['profiles'])} profile(s), +{p['corpus_added']} corpus line(s); "
           f"pushed {c['inserted']} new line(s); profiles created {r['created'] or 'none'}, updated {r['updated'] or 'none'}")
    if r["conflicts"]:
        return msg + f"; conflict: {', '.join(r['conflicts'])} - pull first", 2
    return msg, 0


def status_info() -> dict:
    core = paths.core_path()
    state = store.load_state()
    creds = store.load_credentials()
    info = {"voice_dir": str(paths.voice_dir()), "mode": store.mode(), "url": creds.url if creds else None,
            "username": None, "core_exists": core.is_file(), "contexts": paths.live_contexts(),
            "lock_held": (paths.voice_dir() / ".sync.lock").is_file(), "config": config.all_values(),
            "processed_through_local": None, "processed_through_remote": None, "pending_since_processed": 0,
            "unpushed_lines": 0, "versions": {}}
    if core.is_file():
        text = core.read_text(encoding="utf-8")
        info["processed_through_local"] = get_marker(text, "processed") or None
        info["pending_since_processed"] = count_since(paths.corpus_path(), get_marker(text, "processed"))
    try:
        info["unpushed_lines"] = max(0, len(paths.corpus_path().read_text(encoding="utf-8").splitlines()) - state.pushed_through_line)
    except OSError:
        pass
    if creds:
        try:
            a = api.Api(creds.url, creds.token, timeout=10)
            me = a.me()
            info["username"] = me["username"]
            info["processed_through_remote"] = me["processed_through"]
            remote = {p["context"]: p["version"] for p in a.list_profiles()}
            for ctx in sorted(set(remote) | set(state.versions)):
                info["versions"][ctx] = {"local": state.versions.get(ctx), "remote": remote.get(ctx)}
        except (api.ApiError, api.Offline) as e:
            info["remote_error"] = str(e)
    return info
```

`cli.py` commands: `cmd_pull`, `cmd_push`, `cmd_sync`, `cmd_status` call these; local-only → print `f"pull: {store.LOCAL_ONLY_HINT}"` and return 0; `api.Offline` → exit 1 with `error: offline: ...`; `api.AuthError` → exit 1 `error: token rejected; run 'voicectl login'`. `cmd_push` returns 2 when `push_profiles` reports conflicts and prints `conflict: ...`.

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git commit -m "feat(client): pull/push/sync/status over HTTP"`.

---

### Task 11: Client — `update-prep`/`update-apply` over HTTP, gate push, two-machine test

**Files:**
- Modify: `client/voicectl/update.py`, `client/voicectl/gate.py`, `client/tests/test_corpus_update.py`, `client/tests/test_sync_gate.py`
- Create: `client/tests/test_two_machines_http.py`

**Interfaces:**
- `update.prep()`: `pull` first via `sync.pull` when synced (`pull` key: `ok`/`offline`/`local-only`; the `conflict-remote-kept` value disappears — pull always overwrites local profiles); rest unchanged.
- `update.apply(candidate, processed_through=None)`: local validate + atomic install (unchanged) → if synced: `sync.push_corpus` → `PUT /profiles/core If-Match versions["core"]` `X-Source: updater` → on success record version/hash, `set_processed_through(ts)` and keep the local marker; on `ConflictError` → `sync.pull()` (remote core wins locally), return message with `; conflict: server core is v<n>; re-run update` and the CLI exits 2; on `Offline` → `; push failed: ... (local apply stands; run 'voicectl sync' later)`, exit 0.
- `gate._run()`: when synced, call `sync.push_corpus(api.Api(url, token, timeout=5))` inside try/except-all before the threshold check; log outcome.

- [ ] **Step 1: Tests**

Append to `test_corpus_update.py` (uses `live_server`, `account`, and the `logged_in` helper from `test_sync_http`):

```python
from tests.test_sync_http import logged_in


def test_apply_pushes_core_and_marker(voice_env, live_server, account, monkeypatch):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    add_corpus(voice_env, "2026-04-01T00:00:00Z", "fresh")
    cand = voice_env / "cand.md"
    cand.write_text((voice_env / "core.md").read_text().replace("- **trait one**", "- **trait zero**\n- **trait one**"))
    msg = update.apply(cand)
    assert "pushed core v2" in msg
    body, v = a.get_profile("core")
    assert v == 2 and "trait zero" in body
    assert a.me()["processed_through"] == "2026-04-01T00:00:00Z"
    assert not cand.exists()


def test_apply_conflict_pulls_remote_core(voice_env, live_server, account, monkeypatch):
    a = logged_in(voice_env, live_server, account, monkeypatch)
    main(["push"])
    body, v = a.get_profile("core")
    a.put_profile("core", body.replace("trait one", "REMOTE"), v, "updater")
    cand = voice_env / "cand.md"
    cand.write_text(body.replace("trait one", "LOCAL"))
    msg = update.apply(cand)
    assert "conflict" in msg and "REMOTE" in (voice_env / "core.md").read_text()
```

`test_sync_gate.py` gate addition:

```python
def test_gate_pushes_corpus_before_deciding(voice_env, live_server, account, monkeypatch):
    from tests.test_sync_http import logged_in
    a = logged_in(voice_env, live_server, account, monkeypatch)
    add_corpus(voice_env, "2026-01-02T00:00:00Z", "one")
    monkeypatch.setenv("VOICE_SYNC_MIN_COUNT", "99")
    gate.run()
    assert a.me()["corpus_count"] == 1
```

`test_two_machines_http.py`:

```python
from voicectl import update, store
from voicectl.cli import main
from tests.conftest import CORE, add_corpus
from tests.test_sync_http import logged_in


def test_two_machines_converge(tmp_path, monkeypatch, voice_env, live_server, account):
    a = voice_env
    logged_in(a, live_server, account, monkeypatch)
    main(["push"])
    b = tmp_path / "machine-b"
    monkeypatch.setenv("VOICE_DIR", str(b))
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(account[1] + "\n"))
    assert main(["login", live_server, "--username", account[0], "--password-stdin"]) == 0
    assert (b / "core.md").read_text() == (a / "core.md").read_text()

    monkeypatch.setenv("VOICE_DIR", str(a))
    add_corpus(a, "2026-03-01T00:00:00Z", "from A")
    update.prep()
    cand = a / "cand.md"
    cand.write_text(CORE.replace("- **trait one**", "- **trait A**\n- **trait one**"))
    assert "pushed core" in update.apply(cand)

    monkeypatch.setenv("VOICE_DIR", str(b))
    add_corpus(b, "2026-03-02T00:00:00Z", "from B")
    p = update.prep()
    assert p["pull"] == "ok" and [e["text"] for e in p["new_entries"]] == ["from B"]
    cand = b / "cand.md"
    cand.write_text((b / "core.md").read_text().replace("- **trait A**", "- **trait A**\n- **trait B**"))
    assert "pushed core" in update.apply(cand)

    monkeypatch.setenv("VOICE_DIR", str(a))
    assert main(["pull"]) == 0
    assert (a / "core.md").read_text() == (b / "core.md").read_text()
    for d in (a, b):
        text = (d / "corpus.jsonl").read_text()
        assert "from A" in text and "from B" in text
```

- [ ] **Step 2: Implement** — `update.py`:

```python
def _client():
    c = store.load_credentials()
    return api.Api(c.url, c.token) if c else None


def _pull_status() -> str:
    a = _client()
    if a is None:
        return "local-only"
    try:
        sync.pull(a)
        return "ok"
    except (api.Offline, api.ApiError):
        return "offline"
```

`apply()` tail:

```python
    msg = f"update-apply: installed {core} (Processed through: {processed_through or 'unchanged'})"
    a = _client()
    if a is None:
        return msg + f"; {store.LOCAL_ONLY_HINT}"
    try:
        sync.push_corpus(a)
        state = store.load_state()
        v = a.put_profile("core", text, state.versions.get("core", 0), "updater")
        state.versions["core"], state.hashes["core"] = v, sync._sha(text)
        store.save_state(state)
        if processed_through:
            a.set_processed_through(processed_through)
        return msg + f"; pushed core v{v}"
    except api.ConflictError as e:
        try:
            sync.pull(a)
        except (api.Offline, api.ApiError):
            pass
        return msg + f"; conflict: server core is v{e.current_version}; local core replaced by the server's - re-run update"
    except (api.Offline, api.ApiError) as e:
        return msg + f"; push failed: {e} (local apply stands; run 'voicectl sync' later)"
```

`cmd_update_apply` in `cli.py` returns 2 when the message contains `"; conflict:"`.

`gate.py` addition before the threshold check:

```python
    creds = store.load_credentials()
    if creds:
        try:
            r = sync.push_corpus(api.Api(creds.url, creds.token, timeout=5))
            _log(f"gate: pushed {r['inserted']} corpus line(s)")
        except Exception as e:  # noqa: BLE001 - never block teardown
            _log(f"gate: corpus push skipped: {e!r}")
```

- [ ] **Step 3: Run, commit** — `uv run pytest -q`; `git commit -m "feat(client): update flow syncs core and marker through the service; gate pushes corpus"`.

---

### Task 12: Skill docs + installer

**Files:**
- Modify: `skills/voice/SKILL.md`, `skills/voice/scripts/install_voice_pipeline.sh`, `skills/voice/scripts/install_voice_pipeline.test.sh`, `skills/voice/evals/evals.json`, `skills/voice/hooks/voice-sync-gate.sh` (comment only)

- [ ] **Step 1: SKILL.md** — replace the "Setting up a machine" section with:

```markdown
## Setting up a machine ("set up my voice")

`bash scripts/install_voice_pipeline.sh` once (installs `voicectl`, hooks, templates; local-only).
Then connect to a voice-store account. Walk the user through this:

1. `voicectl status --json`. If `mode` is `synced`, report `url`/`username` and stop.
2. Ask one question: **Do you have a voice-store account?**
   - **Yes** - ask for the service URL (e.g. `https://voice.example.com/api`) and username.
   - **No** - the server owner creates one (`create_user` script); stay local-only until then.
   - **Local only** - say plainly that other machines will not see this voice.
3. `voicectl login <url> --username <name>` (prompts for the password; never put it on the command line).
   A fresh dir is seeded from templates and then pulled from the server, so a second machine
   arrives with the user's real profiles and corpus.
4. `voicectl backfill`, then `voicectl push`, then report `voicectl status`.

Second machine: install the plugin → `voicectl login` → `voicectl backfill` → `voicectl push`.
```

Update "Updating the voice": step 1 says `update-prep` pulls (`pull: ok|offline|local-only`); step 4: "`update-apply` pushes the new core and the marker; `conflict:` in its output (exit 2) means another machine updated first - the server's core is now local, re-run the update." Edge cases: replace the git bullets with: "Offline: `update-prep` says `pull: offline`, works locally; `update-apply` says `push failed`; run `voicectl sync` later." and "`push` exit 2 = an overlay you edited locally was also changed on the server; `voicectl pull` takes the server copy (yours is in `.bak` nowhere - copy it out first if you want to merge by hand)." Remove every mention of git, remotes, `--create`, `--allow-public`, `corpusSync`. Tunables paragraph: `voicectl config` keys `model`, `minCount`, `minInterval` in `~/.madskillz/voice/config.json`.

- [ ] **Step 2: Installer** — replace step 5+6 (init/backfill/push) with:

```bash
# --- 5. local voice dir -------------------------------------------------------------------------
PATH="$HOME/.local/bin:$PATH"
if ! command -v voicectl >/dev/null 2>&1; then
  say "  ! voicectl not on PATH - skipping init; re-run after installing uv"
elif out="$(voicectl init 2>&1)"; then
  echo "$out" | grep -q "seeded: nothing" && skip "voice dir already seeded" || did "seeded voice dir ($VOICE_DIR)"
  if [ -n "${VOICE_URL:-}" ] && [ -n "${VOICE_USERNAME:-}" ]; then
    if out="$(voicectl login "$VOICE_URL" --username "$VOICE_USERNAME" --password-stdin 2>&1)"; then
      did "logged in to $VOICE_URL as $VOICE_USERNAME"
      voicectl backfill >/dev/null 2>&1 && did "backfilled local Claude history"
      voicectl push >/dev/null 2>&1 && did "pushed corpus + profiles"
    else
      say "  ! login failed:"; echo "$out" | sed 's/^/    /'
    fi
  else
    say "  ! local-only: run 'voicectl login URL' (or ask Claude to 'set up my voice') to sync across machines"
  fi
else
  say "  ! voicectl init failed:"; echo "$out" | sed 's/^/    /'
fi
```

Header env docs: `VOICE_URL`, `VOICE_USERNAME` (password read from stdin), drop `VOICE_REMOTE/VOICE_CREATE/VOICE_ALLOW_PUBLIC/VOICE_INSTALL_NO_INIT`. The tool copy step copies `client/` (path: `skill_root/../../client`) — compute `client_root="$(cd "$skill_root/../.." && pwd)/client"`. Test script: keep the settings/hook assertions; add `VOICE_INSTALL_NO_TOOL=1` still skips init because `voicectl` is absent in the sandbox PATH — assert the `! voicectl not on PATH` line appears.

- [ ] **Step 3: evals + hook comment** — evals line: `"Reports the push result that \`voicectl update-apply\` prints (pushed core vN, conflict, or push failed)"`. Gate shim comment: tunables via `voicectl config`; the gate also pushes corpus to the voice store with a 5s timeout.

- [ ] **Step 4: Verify + commit** — `bash skills/voice/scripts/install_voice_pipeline.test.sh`; `grep -rn "git\b\|--remote\|corpusSync\|madskillz-sync" skills/voice/SKILL.md` → empty; `git commit -m "docs(skill): login-based setup flow; installer targets the voice-store client"`.

---

### Task 13: Docker, Kustomize, ArgoCD, CI

**Files:**
- Create: `Dockerfile`, `docker-entrypoint.sh`, `k8s/base/{kustomization,namespace,configmap,secret,mysql-secret,mysql-deployment,mysql-service,deployment,service,ingress}.yaml`, `k8s/overlays/prod/{kustomization,ingress-json-patch,configmap-patch}.yaml`, `argocd/apps/prod.yaml`, `.github/workflows/{test,release}.yml`, `.github/scripts/compute-version.sh`

- [ ] **Step 1: Dockerfile + entrypoint** (skill-matrix's, paths adjusted)

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY server/pyproject.toml server/uv.lock ./
RUN uv pip install --system .
COPY server/ .
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "voice_store.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`server/docker-entrypoint.sh`: skill-matrix's script minus the `alembic_preflight` call (`alembic upgrade head` only).

- [ ] **Step 2: k8s base**

`namespace.yaml` (`voice-store`), `configmap.yaml` (`voice-store-config`: `PYTHONPATH=/app/src`, `DB_HOST=mysql`, `DB_PORT=3306`, `DB_USER=voice`, `DB_NAME=voice_store`, `REGISTRATION_OPEN=false`), `mysql-secret.yaml` (`root-password`, `app-password` base64 `password` placeholders — prod overlay patches real values; **never commit real secrets**), `mysql-deployment.yaml` + `mysql-service.yaml` (skill-matrix's, `MYSQL_DATABASE`/`MYSQL_USER` from `voice-store-config`, PVC `mysql-data` 5Gi), `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-store
spec:
  replicas: 1
  strategy: {type: RollingUpdate, rollingUpdate: {maxUnavailable: 0, maxSurge: 1}}
  selector: {matchLabels: {app: voice-store}}
  template:
    metadata: {labels: {app: voice-store}}
    spec:
      containers:
      - name: voice-store
        image: voice-store:latest
        imagePullPolicy: Always
        ports: [{containerPort: 8000}]
        envFrom: [{configMapRef: {name: voice-store-config}}]
        env:
        - name: DB_PASSWORD
          valueFrom: {secretKeyRef: {name: mysql-secret, key: app-password}}
        readinessProbe: {httpGet: {path: /health, port: 8000}, initialDelaySeconds: 5, periodSeconds: 10}
        livenessProbe: {httpGet: {path: /health, port: 8000}, initialDelaySeconds: 15, periodSeconds: 20}
        resources: {requests: {cpu: 50m, memory: 128Mi}, limits: {memory: 512Mi}}
```

`service.yaml` (port 80 → 8000), `ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: voice-store
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
  - host: voice.localhost
    http:
      paths:
      - path: /api(/|$)(.*)
        pathType: ImplementationSpecific
        backend: {service: {name: voice-store, port: {number: 80}}}
```

Prod overlay: namespace `voice-store-prod`, `images: [{name: voice-store, newName: bubthegreat/voice-store, newTag: "0.1.0"}]`, ingress json patch → host `voice.bubtaylor.com`, cert-manager `letsencrypt-prod` annotation, TLS secret `voice-store-prod-tls`; `configmap-patch.yaml` unchanged values (placeholder for `REGISTRATION_OPEN` flips). `argocd/apps/prod.yaml`: skill-matrix's with `repoURL: https://github.com/bubthegreat/voice-store.git`, `targetRevision: '>=0.1.0'`, `path: k8s/overlays/prod`, `namespace: voice-store-prod`, `ignoreDifferences` for `mysql-secret` `/data`.

- [ ] **Step 3: CI** — `test.yml` (on push/PR): three jobs — server (`cd server && uv sync && uv run ruff check . && uv run pytest -q`), client (`cd client && uv sync && uv run pytest -q`), vendor (`bash scripts/check_vendor.sh`) + installer test. `release.yml` (on push to `main`, after `test.yml` via `workflow_call`): compute next patch version (`compute-version.sh` = skill-matrix's script copied verbatim), build + push `bubthegreat/voice-store:{latest,VERSION}` to Docker Hub (`DOCKER_USERNAME`/`DOCKER_PASSWORD` secrets), bump `server/pyproject.toml` + prod overlay `newTag`, commit `[skip ci]`, tag `vVERSION` (`RELEASE_TOKEN` secret).

- [ ] **Step 4: Verify** — `docker build -t voice-store:dev .` then `docker run --rm -e DATABASE_URL=sqlite+aiosqlite:////tmp/x.db -p 8000:8000 voice-store:dev` and `curl -s localhost:8000/health`; `kubectl kustomize k8s/overlays/prod >/dev/null`. Commit `"chore: docker, kustomize, argocd, ci"`.

---

### Task 14: madskillz — remove the skill, add the marketplace entry, close PR #30

**Files (madskillz repo, new branch `chore/voice-to-voice-store` off `main`):**
- Delete: `plugins/madskillz/skills/voice/**`
- Modify: `.claude-plugin/marketplace.json`, `CLAUDE.md` (drop the voice-sync exception), `plugins/madskillz/skills/blog/SKILL.md` (install pointer → "install the `voice` plugin from this marketplace"), `docs/superpowers/specs/2026-08-25-voice-user-repo-storage-design.md` (add a top line: "Superseded by 2026-08-26-voice-store-service-design.md; never shipped.")
- Memory: `voice-system-voicectl.md`

- [ ] **Step 1: Branch + edits**

`marketplace.json` `plugins` gains:

```json
{
  "name": "voice",
  "description": "Owner voice profiles: capture, render, update, sync via voice-store",
  "source": { "source": "github", "repo": "bubthegreat/voice-store" },
  "category": "productivity"
}
```

- [ ] **Step 2: Verify + PR** — `grep -rn "skills/voice" plugins docs CLAUDE.md` → only the superseded spec; open PR "chore: move voice skill to bubthegreat/voice-store"; `gh pr close 30 --comment "Superseded by the voice-store service (bubthegreat/voice-store); the client code carried over."` (**confirm with the owner before closing #30**).

- [ ] **Step 3: Memory** — rewrite `voice-system-voicectl.md`: voice skill + `voicectl` + server live in `bubthegreat/voice-store`; live dir `~/.madskillz/voice`; `voicectl login`; spec path.

---

### Task 15: Owner cutover (controller + owner; outward actions need the owner's go)

- [ ] **Step 1:** Create DB creds: generate `app-password`/`root-password`, apply the prod overlay secrets out-of-band (`kubectl -n voice-store-prod create secret generic mysql-secret ...`), DNS record via Crossplane for `voice.bubtaylor.com`, push tag `v0.1.0` (release workflow), confirm ArgoCD sync and `curl https://voice.bubtaylor.com/api/health`.
- [ ] **Step 2:** `kubectl -n voice-store-prod exec deploy/voice-store -- python -m voice_store.scripts.create_user --username bubthegreat` (password prompted).
- [ ] **Step 3:** On this machine: install the plugin from the marketplace, run `skills/voice/scripts/install_voice_pipeline.sh`, `voicectl login https://voice.bubtaylor.com/api --username bubthegreat`, `voicectl push` (expect `created core, blog, chat, research, storycraft`, `inserted 1798`), `voicectl status --json` (`versions.core == {local:1, remote:1}`, `unpushed_lines == 0`). Marker: `PUT /me/processed-through` happens on the next `update-apply`; set it now with `voicectl` — add a hidden `voicectl set-marker <ts>` if needed, else `curl -X PUT .../me/processed-through -d '{"ts":"2026-08-26T19:59:03Z"}'`.
- [ ] **Step 4:** `rm -rf ~/.madskillz/voice/madskillz-sync ~/.madskillz/voice/voice.md`; keep `posts/`. Uninstall the old `madskillz` voice skill path (it is gone once the madskillz PR merges and the marketplace refreshes).

---

## Self-review

**Spec coverage.** Repo layout → T1; stack/env → T2; tables → T2; auth → T3 + T4; routes: auth T3, `/me` T5, profiles T6, corpus T7, health T2; client files/config → T8; commands: login/logout/whoami T9, pull/push/sync/status T10, update-prep/apply/gate T11, init/capture/backfill/render unchanged; two-machine semantics → T11 test; hooks/installer/SKILL.md → T12; error handling → each route/command task; testing → conftest T2, live server T9; deploy → T13; owner cutover → T15; madskillz removal + marketplace → T14. **Gap:** spec's `GET /corpus?since=` + `after_id` combined semantics — T7 rules that `after_id` pages by id and `since` alone orders by ts (noted inline). **Gap:** spec lists `.state.json` without `hashes` for core — T8 records core's hash too (harmless). **Deviation:** MySQL runs in-namespace (skill-matrix pattern) instead of "the homelab's existing instance" — recorded here as a ruling; no spec text depends on it.

**Placeholders.** None. Task 13's YAML is abbreviated with flow-style maps but complete; `compute-version.sh` and `docker-entrypoint.sh` are named verbatim copies.

**Type consistency.** `Api.get_profile -> (str, int)` used by `sync.pull`/tests; `put_profile -> int`; `ConflictError.current_version` used by `update.apply` and `push_profiles`; `store.State` fields match `.state.json` keys; `sync._sha` used from `update.apply`; `profile_service.StaleVersion.current` → route's `409 {"current_version"}` → client `ConflictError`; `TS_PATTERN` shared by `types/me.py` and `types/corpus.py`; live-server fixture yields a bare URL and the client's `Api` accepts it because routes are unprefixed (ingress rewrite handles `/api` in prod).
