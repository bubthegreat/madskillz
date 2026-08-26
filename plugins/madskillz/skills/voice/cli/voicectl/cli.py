"""voicectl - owner-voice pipeline CLI.

capture/gate keep the hook contract: exit 0 unconditionally, nothing on stdout,
failures logged to sync.log. Everything else errors loudly.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import backfill, gate, paths, store, sync, update
from .corpus import append_capture, count_since
from .merge import RenderError, render
from .profile import get_marker


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


def cmd_init(args) -> int:
    """Seed missing live voice files from a committed voices directory (default: the
    dedicated sync clone). Never overwrites an existing live file."""
    src = Path(args.source) if args.source else paths.sync_repo() / paths.VOICES_SUBPATH
    if not src.is_dir():
        print(f"error: committed voices dir not found: {src}", file=sys.stderr)
        return 1
    paths.voice_dir().mkdir(parents=True, exist_ok=True)
    seeded, kept = [], []
    for f in sorted(src.glob("*.md")):
        dst = paths.voice_dir() / f.name
        if dst.exists():
            kept.append(f.name)
        else:
            shutil.copyfile(f, dst)
            seeded.append(f.name)
    print(f"init: seeded {seeded or 'nothing'}; kept existing {kept or 'nothing'}")
    return 0


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

    s = sub.add_parser("status", help="markers, pending counts, materiality, lock state")
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

    i = sub.add_parser("init", help="seed missing live voice files from the committed library")
    i.add_argument("--source")
    i.set_defaults(fn=cmd_init)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
