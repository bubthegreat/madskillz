"""Per-machine tunables, stored as `voice.<key>` in the store clone's LOCAL git config
(never committed). Env aliases win so tests and hooks can override without touching git."""

import os
import subprocess

from . import paths

DEFAULTS: dict[str, str] = {
    "model": "opus",
    "minCount": "15",
    "minInterval": "720",
    "corpusSync": "true",
}

ENV_ALIASES: dict[str, str] = {
    "model": "VOICE_SYNC_MODEL",
    "minCount": "VOICE_SYNC_MIN_COUNT",
    "minInterval": "VOICE_SYNC_MIN_INTERVAL_SECONDS",
}


class ConfigError(Exception):
    pass


def _is_repo() -> bool:
    return (paths.voice_dir() / ".git").exists()


def _git_config(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(paths.voice_dir()), "config", "--local", *args],
        capture_output=True, text=True,
    )


def get(key: str) -> str:
    if key not in DEFAULTS:
        raise KeyError(key)
    alias = ENV_ALIASES.get(key)
    if alias and os.environ.get(alias):
        return os.environ[alias]
    if _is_repo():
        r = _git_config("--get", f"voice.{key}")
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return DEFAULTS[key]


def set(key: str, value: str) -> None:  # noqa: A001 - CLI verb
    if key not in DEFAULTS:
        raise KeyError(key)
    if not _is_repo():
        raise ConfigError(
            f"{paths.voice_dir()} is not a git repo; run 'voicectl init' first"
        )
    r = _git_config(f"voice.{key}", value)
    if r.returncode != 0:
        raise ConfigError(r.stderr.strip())


def get_bool(key: str) -> bool:
    return get(key).strip().lower() in ("1", "true", "yes", "on")


def get_int(key: str) -> int:
    return int(get(key))


def all_values() -> dict[str, str]:
    return {k: get(k) for k in DEFAULTS}
