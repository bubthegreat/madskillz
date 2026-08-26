import json

from voicectl.cli import main
from tests.conftest import CORE
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


UNFILLED_CORE = (
    CORE.replace("- **trait one** - keep.\n- **trait two** - tone-down.\n", "")
    .replace("Processed through: 2026-01-01T00:00:00Z", "Processed through: none")
)


def test_render_warns_when_the_core_is_still_a_template(voice_env, capsys):
    """A seeded template renders fine but is nobody's voice yet, so the caller has to hear
    about it. The rendered doc still goes to stdout untouched."""
    (voice_env / "core.md").write_text(UNFILLED_CORE, encoding="utf-8")
    assert main(["render", "blog"]) == 0
    out, err = capsys.readouterr()
    assert "no observed traits yet" in err
    assert "update my voice" in err
    assert "Blog preamble" in out


def test_render_is_quiet_for_a_real_core(voice_env, capsys):
    assert main(["render", "blog"]) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert "trait one" in out
