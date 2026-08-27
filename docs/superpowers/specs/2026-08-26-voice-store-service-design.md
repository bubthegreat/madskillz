# Voice Store — service + client design spec (2026-08-26)

Replace the git-repo voice store (spec 2026-08-25) with a small authenticated FastAPI service.
The service stores each user's voice profiles and prompt corpus behind a per-user bearer token.
All LLM work (the "update my voice" judgment) stays on the user's machine, run by the `voice`
skill through a light Python client. The `voice` skill moves out of madskillz into the new repo.

Supersedes `2026-08-25-voice-user-repo-storage-design.md` entirely. The render/merge rules,
profile file contract, corpus line format, and gate decision logic from
`2026-08-19-voice-system-design.md` are unchanged.

## Decisions (from brainstorming)

- Multi-user from day one. API only; Swagger (`/api/docs`) is the whole UI.
- Hosted on the homelab k8s cluster via ArgoCD, public DNS + TLS.
- Auth modeled on skill-matrix's `skills-api`, then simplified: username + password, opaque
  bearer tokens stored in a table, no JWT, no refresh, no revocation list, no MFA, no orgs,
  no roles, no rate limiter, no password reset.
- No server-side scheduler and no LLM calls from the server. No Anthropic key on the server.
- The token identifies the user; every route is scoped by it. No user ids in paths.
- Corpus is append-only and is never deleted.
- Profile history is kept (every `PUT` is a new version).

## Goals

- One store per user, reachable from any machine with a token.
- N machines converge on one core, one overlay set, one corpus, one `processed_through` marker.
- The skill and its client live in one repo that is itself a Claude Code plugin.
- Local-only mode still works for users without a server.

## Non-goals

- No web UI. No email. No org/team sharing. No server-side updater. No LLM proxying.
- No migration tooling from the git store (it never shipped; PR #30 is closed unmerged).

## Repo layout — `bubthegreat/voice-store`

```
.claude-plugin/plugin.json        # plugin "voice"; madskillz marketplace points here
skills/voice/
  SKILL.md                        # moved from madskillz; setup section rewritten (below)
  references/voice-update.md
  references/voice-overlay-template.md
  references/voices/*.md          # templates only (as today)
  hooks/capture-voice.sh, hooks/voice-sync-gate.sh
  scripts/install_voice_pipeline.sh (+ .test.sh)
  evals/evals.json
client/                           # uv project `voicectl`
  pyproject.toml                  # deps: httpx; python >= 3.11
  voicectl/{cli,paths,config,profile,merge,corpus,backfill,gate,update,api,store}.py
  tests/
server/                           # uv project `voice_store`, skill-matrix layout
  pyproject.toml
  src/voice_store/{main,db,models/,routes/,services/,types/,utils/,scripts/,vendor/}
  alembic/ alembic.ini
  tests/
Dockerfile  Dockerfile.dev  docker-entrypoint.sh
k8s/base  k8s/overlays/{local,prod}
argocd/apps/prod.yaml
.github/workflows/{ci,image}.yml
```

`server/src/voice_store/vendor/{profile,merge}.py` are verbatim copies of the client modules
with a header naming the source; a CI check diffs them against `client/voicectl/`.

## Server

### Stack (skill-matrix conventions)

FastAPI, SQLAlchemy async, MySQL via `aiomysql` (tests: per-xdist-worker SQLite), Alembic
(`docker-entrypoint.sh` runs `alembic upgrade head`, `SKIP_MIGRATIONS=1` to skip), settings
via `os.getenv` that raise on missing secrets, ruff line-length 120, pytest-asyncio
`asyncio_mode=auto` + xdist, `FastAPI(root_path="/api")`, `GET /health` on the app.
Python 3.12 image, uv for installs.

Env: `DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME` (required), `REGISTRATION_OPEN`
(default `false`), `BCRYPT_ROUNDS` (default 12).

### Tables

| table | columns |
|---|---|
| `users` | `id`, `username` (unique, 3-64 chars), `hashed_password`, `is_active` (default true), `processed_through` (nullable str, ISO Z), `created_at` |
| `tokens` | `id`, `user_id` (fk), `name` (default `"default"`), `token_hash` (sha256 hex, unique), `created_at`, `last_used_at` |
| `profiles` | `id`, `user_id`, `context` (`core`, `blog`, …; 1-32 chars `[a-z0-9-]`), `version` (int ≥1), `body` (MEDIUMTEXT), `source` (`user`/`updater`/`seed`), `created_at`; unique `(user_id, context, version)` |
| `corpus` | `id`, `user_id`, `ts` (str ISO Z), `text` (MEDIUMTEXT), `machine` (str, nullable), `sha` (sha256 of `ts + "\n" + text`), `created_at`; unique `(user_id, sha)`; index `(user_id, ts)` |

Profiles are append-only; the current profile is the highest `version`. Corpus rows are never
updated or deleted; there is no route that can.

### Auth

- Password: passlib `CryptContext(schemes=["bcrypt"])`, `bcrypt==4.0.1` pinned.
  `services/password_service.py` is the only module that writes `hashed_password`.
  Policy: length ≥ 12, nothing else.
- Token: `secrets.token_urlsafe(32)` prefixed `vs_`. Stored as sha256 hex. Returned once.
- `get_current_user` (`utils/auth.py`): reads `Authorization: Bearer <token>`, hashes, looks up
  `tokens.token_hash` joined to an active user, bumps `last_used_at` (at most once per
  minute), returns the user. No token / unknown token → `401` with
  `WWW-Authenticate: Bearer`. Inactive user → `403`.
- Swagger: `HTTPBearer` security scheme so the "Authorize" box takes a pasted token.
- Bootstrap: `python -m voice_store.scripts.create_user --username U [--password P | prompt]
  [--reset-password]` — inserts or resets; prints nothing secret.

### Routes

All routes except `/health`, `/auth/register`, `/auth/login` require the bearer token.

| Method + path | Request | Response |
|---|---|---|
| `POST /auth/register` | `{username, password}` | `201 {id, username}`; `403` when `REGISTRATION_OPEN` is false; `409` on duplicate |
| `POST /auth/login` | `{username, password, token_name?}` | `200 {token, id, name}`; `401` on bad credentials |
| `GET /auth/tokens` | – | `[{id, name, created_at, last_used_at}]` |
| `DELETE /auth/tokens/{id}` | – | `204`; `404` if not yours / absent. Deleting the token in use is allowed. |
| `POST /auth/change-password` | `{current_password, new_password}` | `204`; deletes every token of the user (including the caller's) |
| `GET /me` | – | `{username, processed_through, profile_contexts: [...], corpus_count, latest_corpus_ts}` |
| `PUT /me/processed-through` | `{ts}` | `200 {processed_through}`; `422` if `ts` is not ISO-8601 Z or is older than the current value |
| `GET /profiles` | – | `[{context, version, created_at}]` (current versions) |
| `GET /profiles/{ctx}` | – | body as `text/markdown`, headers `ETag: "<version>"`, `X-Version`; `404` if none |
| `PUT /profiles/{ctx}` | `text/markdown` body, header `If-Match: "<version>"` (`"0"` to create), optional `X-Source: user\|updater` | `200 {context, version}`; `428` without `If-Match`; `409 {current_version}` if stale; `422` when `ctx == core` and `validate_core` returns problems |
| `GET /profiles/{ctx}/versions` | `?limit=50&before=<version>` | `[{version, source, created_at, size}]` |
| `GET /profiles/{ctx}/versions/{n}` | – | body of version `n`, `text/markdown` |
| `GET /profiles/{ctx}/render` | – | `text/markdown` from vendored `merge.render(core, overlay, ctx)`; `404` if core or overlay missing |
| `POST /corpus` | `[{ts, text, machine?}]` (≤ 1000 items) | `200 {inserted, skipped}`; `422` for any malformed item (nothing inserted) |
| `GET /corpus` | `?since=<ts>&after_id=<id>&limit=1000` | `{items: [{id, ts, text, machine}], next_after_id}` ascending by `(ts, id)` |
| `GET /health` | – | `{status: "healthy", service: "voice-store"}` |

Errors are FastAPI `HTTPException(detail=...)`; unhandled exceptions → `500 {"message"}`.

## Client — `voicectl`

Same package as today with `store.py`'s git transport replaced by `api.py`.

### Files and config

- `~/.madskillz/voice/` stays the live dir: `core.md`, `<ctx>.md`, `corpus.jsonl`, `sync.log`,
  `.sync.lock`, `.last-sync-attempt`, plus new `token` (mode `0600`, contents `<url>\n<token>`)
  and `.state.json` (`{"pushed_through_line": N, "pulled_through_id": M, "versions": {"core": 7, "blog": 2}, "hashes": {"core": "<sha256 as pulled>", ...}}`).
- Templates: `~/.madskillz/voice-templates/` (installer copies `skills/voice/references/voices/`).
- Tunables: `voicectl config` keys `model`, `minCount`, `minInterval` stored in
  `~/.madskillz/voice/config.json` (no git config any more). Env aliases unchanged.
- `mode()`: `synced` when `token` exists, else `local-only`.

### Commands

| Command | Behavior |
|---|---|
| `login <url>` | prompt username + password (or `--username/--password-stdin`), `POST /auth/login` with `token_name=<hostname>`, write `token`. If the live dir is empty, seed templates, then `pull`. |
| `logout` | `DELETE /auth/tokens/{id}` (ignore 404), delete `token`. |
| `whoami` | `GET /me`. |
| `pull` | `GET /profiles` → for each context `GET /profiles/{ctx}`, overwrite the local file, record version. `GET /corpus?after_id=<pulled_through_id>` paged → append lines not already present locally (dedupe on `(ts,text)`), update `pulled_through_id`. `GET /me` → set local core's `Processed through` to the server value. Exit 0. Local-only → prints hint, exit 0. |
| `push` | `POST /corpus` in batches of 1000 for local lines after `pushed_through_line`, `machine=<hostname>`; advance the line counter on each 200. For each overlay whose local sha256 differs from `hashes[ctx]`: `PUT /profiles/{ctx}` with `If-Match` of the recorded version; `409` → report, leave the file, exit 2. Any local profile the server does not have yet (including `core`, e.g. first login onto an empty account) is created with `If-Match: "0"`, `X-Source: user`. Otherwise never PUTs `core` (only `update-apply` does). |
| `sync` | `pull` then `push`. |
| `capture` | unchanged (local append, exit 0, no stdout). |
| `backfill` | unchanged; lines land locally and go up on the next `push`. |
| `render <ctx>` | unchanged (local files). Warns on an unfilled core as today. |
| `update-prep` | `pull` first (offline → `pull: offline`, continue locally), then as today. |
| `update-apply <file>` | validate + atomic local install as today; then `push` corpus; then `PUT /profiles/core` with `If-Match: "<recorded core version>"`, `X-Source: updater`; on `200` → `PUT /me/processed-through {newest_ts}` and stamp the local marker; on `409` → `pull`, keep the remote core, exit 2 "re-run update"; on connection error → local apply stands, exit 0 with "push failed; run `voicectl sync`". |
| `gate` | unchanged decision logic, thresholds on the local `Processed through` (which `pull` keeps equal to the server's). Runs the corpus half of `push` first with a 5-second HTTP timeout so corpus reaches the server even when no update launches; any failure is logged and ignored (the SessionEnd hook has a 10-second budget and must never block). |
| `status [--json]` | `mode`, `url`, `username`, local/remote `processed_through`, `pending_since_processed`, `unpushed_lines`, per-context local vs remote version. |
| `init` | local-only seeding from templates only (no remote flags). |

Removed: `migrate-to-repo`, git `store.py`, `.gitattributes`/`.gitignore`/`README.md` scaffolding.

### Two-machine semantics

- Corpus: server unique `(user_id, sha)` makes concurrent pushes from A and B a union.
- Core: only `update-apply` writes it, with `If-Match`. Two simultaneous updaters → one wins,
  the other gets `409`, pulls, and re-runs against the winner's core and marker. Nothing lost:
  the loser's corpus lines were pushed before its `PUT`.
- Marker: single server value; `pull` copies it into the local core; the gate reads the local
  copy, so a machine that pulled recently will not re-run an update another machine already did.

### Hooks and installer

- `capture-voice.sh` unchanged. `voice-sync-gate.sh` unchanged (calls `voicectl gate`).
- `install_voice_pipeline.sh`: tool install (copies `client/` + templates), hooks, settings.json
  wiring (same rewrite rules), then `voicectl init` (local-only). Prints the `voicectl login`
  hint. Env `VOICE_URL` + `VOICE_USERNAME` + `VOICE_PASSWORD_STDIN` allow a non-interactive
  login for scripted setups.

### SKILL.md setup flow ("set up my voice")

1. `voicectl status --json`; if `mode` is `synced`, report and stop.
2. Ask: **do you have a voice-store account?** Options: yes (URL + username), no (the server
   owner creates one; local-only until then), local only.
3. `voicectl login <url>`; report `whoami`.
4. `voicectl backfill`, `voicectl push`, `voicectl status`.

Second machine: install plugin → `voicectl login` (seeds + pulls) → `voicectl backfill` →
`voicectl push`.

## Error handling

- Client HTTP errors never modify local files; exit 1 with the server `detail`; `409` exits 2.
- `pull` writes profiles atomically (tmp + rename) after all GETs succeed.
- Hooks: exit 0, no stdout, errors to `sync.log`, unchanged.
- Server: validation via Pydantic → `422`; DB unique violations mapped to `409`/skipped as
  documented; everything else `500 {"message"}`.

## Testing

- Server (`server/tests`, skill-matrix conftest pattern): register gating, login, token list /
  delete 404, change-password drops tokens, `get_current_user` 401/403, profile create /
  version chain / 428 / 409 / 422 on bad core, versions listing, render, corpus batch
  idempotency + paging + 422 atomicity, marker set + monotonic check, `/me`.
- Client (`client/tests`): keep the non-git tests from PR #30 (profile/merge, corpus, config,
  update, gate, cli render warning, installer). New: `login` writes `token` 0600; `push`/`pull`
  /`update-apply`/`sync` against an **in-process server fixture** (the FastAPI app on SQLite
  served by uvicorn in a thread; real HTTP through httpx) — no mocks; two-machine convergence
  test rewritten over HTTP; `409` path; offline path (server stopped).
- CI: ruff + both test suites + vendor-diff check; image build on tag.

## Deploy

- `k8s/base`: Deployment (uvicorn, 1 replica, probes on `/health`), Service, Ingress
  (cert-manager TLS, Crossplane-DNS hostname `voice.<domain>`), ExternalSecret/Secret for
  `DB_*`. `k8s/overlays/prod` sets the hostname and image tag. MySQL is the homelab's existing
  instance; a `voice_store` database + user are created by hand once.
- `argocd/apps/prod.yaml` tracks the highest semver tag (skill-matrix pattern).
  GitHub Actions builds the image to GHCR on tag.
- First user: `kubectl exec deploy/voice-store -- python -m voice_store.scripts.create_user
  --username bubthegreat`.

## Owner cutover

1. Scaffold repo from PR #30's `client/` code; move `skills/voice`; close PR #30 unmerged.
2. madskillz PR: delete `plugins/madskillz/skills/voice`, add the `voice` plugin entry to
   `.claude-plugin/marketplace.json` pointing at `bubthegreat/voice-store`, re-point blog /
   scientific-study / storycraft docs if they name the old path.
3. Deploy; create user; `voicectl login`; `voicectl push` uploads the 1,798-line corpus and
   the current profiles as version 1; `PUT /me/processed-through 2026-08-26T19:59:03Z`.
4. Delete `~/.madskillz/voice/madskillz-sync`, `voice.md`; keep `posts/` (untouched by the client).
