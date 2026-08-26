import json

from voicectl.cli import main
from tests.test_store import _make_synced_store


def test_init_local_only_cli(voice_env, capsys):
    assert main(["init"]) == 0
    assert "local-only" in capsys.readouterr().out


def test_init_with_remote_and_config(voice_env, bare_remote, capsys):
    assert main(["init", "--remote", str(bare_remote)]) == 0
    out = capsys.readouterr().out
    assert "action: adopted-empty" in out
    assert main(["config", "model", "sonnet"]) == 0
    capsys.readouterr()  # drain "model = sonnet" from the set
    assert main(["config", "model"]) == 0
    assert capsys.readouterr().out.strip() == "sonnet"
    assert main(["config"]) == 0
    assert "minCount" in capsys.readouterr().out


def test_init_missing_remote_exit_3(voice_env, tmp_path, capsys):
    assert main(["init", "--remote", str(tmp_path / "nope.git")]) == 3
    assert "--create" in capsys.readouterr().err


def test_pull_push_status_json(voice_env, bare_remote, capsys):
    _make_synced_store(voice_env, bare_remote)
    assert main(["pull"]) == 0
    assert main(["push"]) == 0
    assert main(["status", "--json"]) == 0
    info = json.loads(capsys.readouterr().out.split("push:")[-1].split("\n", 1)[1])
    assert info["mode"] == "synced"


def test_migrate_requires_remote(voice_env):
    import pytest
    with pytest.raises(SystemExit):
        main(["migrate-to-repo"])
