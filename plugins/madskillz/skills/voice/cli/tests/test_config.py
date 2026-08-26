import subprocess

import pytest

from voicectl import config


def test_get_defaults_without_repo(voice_env):
    assert config.get("model") == "opus"
    assert config.get_int("minCount") == 15
    assert config.get_bool("corpusSync") is True


def test_set_requires_repo(voice_env):
    with pytest.raises(config.ConfigError):
        config.set("model", "sonnet")


def test_set_and_get_round_trip(voice_env, git_env):
    subprocess.run(["git", "init", "-q", "-b", "main", str(voice_env)], check=True)
    config.set("model", "sonnet")
    config.set("corpusSync", "false")
    assert config.get("model") == "sonnet"
    assert config.get_bool("corpusSync") is False


def test_env_alias_overrides(voice_env, git_env, monkeypatch):
    subprocess.run(["git", "init", "-q", "-b", "main", str(voice_env)], check=True)
    config.set("minCount", "3")
    monkeypatch.setenv("VOICE_SYNC_MIN_COUNT", "7")
    assert config.get_int("minCount") == 7


def test_unknown_key(voice_env):
    with pytest.raises(KeyError):
        config.get("nope")
