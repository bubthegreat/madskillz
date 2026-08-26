"""voicectl - owner-voice pipeline CLI.

capture/gate keep the hook contract: exit 0 unconditionally, nothing on stdout,
failures logged to sync.log. Everything else errors loudly.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import backfill, config, gate, paths, store, sync, update
from .corpus import append_capture
from .merge import RenderError, render


def _log(msg: str) -> None:
    try:
        paths.voice_dir().mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with paths.log_path().open("a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except OSError:
        pass


def cmd_capture(_args) -> int:
    try:
        append_capture(paths.corpus_path(), sys.stdin.read())
    except Exception as e:  # noqa: BLE001 - never block the prompt
        _log(f"capture error: {e!r}")
    return 0


def cmd_gate(_args) -> int:
    gate.run()
    return 0


def cmd_backfill(_args) -> int:
    print(backfill.run())
    return 0


def cmd_render(args) -> int:
    core = paths.core_path()
    overlay = paths.overlay_path(args.context)
    if not core.is_file():
        print(f"error: live core profile missing: {core} (run 'voicectl init')", file=sys.stderr)
        return 1
    if not overlay.is_file():
        known = ", ".join(paths.live_contexts()) or "none"
        print(f"error: unknown context '{args.context}' (available: {known})", file=sys.stderr)
        return 1
    try:
        out = render(
            core.read_text(encoding="utf-8"),
            overlay.read_text(encoding="utf-8"),
            args.context,
        )
    except RenderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"rendered {args.context} -> {args.output}")
    else:
        sys.stdout.write(out)
    return 0


def cmd_status(args) -> int:
    info = sync.status_info()
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        for k, v in info.items():
            print(f"{k}: {v}")
    return 0


def cmd_sync(args) -> int:
    try:
        print(sync.run(dry_run=args.dry_run))
        return 0
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_update_prep(_args) -> int:
    try:
        print(update.prep_json())
        return 0
    except update.UpdateError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_update_apply(args) -> int:
    try:
        print(update.apply(Path(args.file), args.processed_through))
        return 0
    except (update.UpdateError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _run_init(args, wire=store.init) -> int:
    try:
        r = wire(args.remote, create=args.create, allow_public=args.allow_public)
    except store.InitRefused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 3
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"mode: {r['mode']}")
    print(f"action: {r['action']}")
    print(f"seeded: {', '.join(r['seeded']) or 'nothing'}")
    if r["backup"]:
        print(f"backup: {r['backup']}")
    if r["mode"] == "synced":
        print(f"visibility: {r['visibility']}")
    else:
        print(f"hint: {store.LOCAL_ONLY_HINT}")
    return 0


def cmd_init(args) -> int:
    return _run_init(args)


def cmd_migrate(args) -> int:
    return _run_init(args, store.migrate_to_repo)


def cmd_pull(_args) -> int:
    try:
        code = store.pull()
        print("pull: ok" if code == 0 else "pull: conflict resolved to remote")
        return code
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_push(_args) -> int:
    try:
        print(store.push())
        return 0
    except store.StoreError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_config(args) -> int:
    try:
        if args.key and args.value is not None:
            config.set(args.key, args.value)
            print(f"{args.key} = {args.value}")
        elif args.key:
            print(config.get(args.key))
        else:
            for k, v in config.all_values().items():
                print(f"{k} = {v}")
        return 0
    except KeyError as e:
        print(f"error: unknown key {e}; known: {', '.join(config.DEFAULTS)}", file=sys.stderr)
        return 1
    except config.ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="voicectl", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("capture", help="hook: append prompt JSON on stdin to the corpus").set_defaults(fn=cmd_capture)
    sub.add_parser("gate", help="hook: SessionEnd cheap-tier gate; may detach an updater").set_defaults(fn=cmd_gate)
    sub.add_parser("backfill", help="mine local Claude history into the corpus").set_defaults(fn=cmd_backfill)

    r = sub.add_parser("render", help="deterministically merge core + <context> overlay")
    r.add_argument("context")
    r.add_argument("-o", "--output")
    r.set_defaults(fn=cmd_render)

    s = sub.add_parser("status", help="mode, remote, ahead/behind, dirty files, markers, pending count, config")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    y = sub.add_parser("sync", help="pull then push the voice store")
    y.add_argument("--dry-run", action="store_true")
    y.set_defaults(fn=cmd_sync)

    sub.add_parser("update-prep", help="emit the LLM's exact input as JSON").set_defaults(fn=cmd_update_prep)

    a = sub.add_parser("update-apply", help="validate + atomically install a revised core profile")
    a.add_argument("file")
    a.add_argument("--processed-through")
    a.set_defaults(fn=cmd_update_apply)

    def _init_flags(parser, remote_required: bool):
        parser.add_argument("--remote", required=remote_required, help="git URL of your private voice repo")
        parser.add_argument("--create", action="store_true", help="create the repo (github.com + gh) if missing")
        parser.add_argument("--allow-public", action="store_true")

    i = sub.add_parser("init", help="wire this machine to your voice repo (or local-only without --remote)")
    _init_flags(i, remote_required=False)
    i.set_defaults(fn=cmd_init)

    m = sub.add_parser("migrate-to-repo", help="move an existing local voice dir into a voice repo")
    _init_flags(m, remote_required=True)
    m.set_defaults(fn=cmd_migrate)

    sub.add_parser("pull", help="rebase onto the voice repo (remote wins profile conflicts)").set_defaults(fn=cmd_pull)
    sub.add_parser("push", help="commit live changes and push to the voice repo").set_defaults(fn=cmd_push)

    c = sub.add_parser("config", help="get/set per-machine tunables (model, minCount, minInterval, corpusSync)")
    c.add_argument("key", nargs="?")
    c.add_argument("value", nargs="?")
    c.set_defaults(fn=cmd_config)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
