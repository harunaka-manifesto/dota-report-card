#!/usr/bin/env python3
"""Run the resumable STRATZ V7 corpus collector until completion or a hard stop."""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.stratz_v7_corpus_runner import (  # noqa: E402
    DEFAULT_FREEZE_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_FRAME,
)

# Relative to the worktree it runs in. This used to be an absolute path into a
# sibling worktree, which tied one collection to another checkout's credential
# file and broke the moment that worktree was cleaned up.
DEFAULT_DOTENV = Path(".env")


def seconds_until(value: str, *, now: datetime | None = None) -> float:
    target = datetime.fromisoformat(value)
    if target.tzinfo is None:
        raise ValueError("resume_at must include a timezone")
    return max(0.0, (target - (now or datetime.now(UTC))).total_seconds())


def _state(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "manifests/state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read runner state: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("runner state must be a JSON object")
    return value


def _command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "scripts/stratz_v7_corpus_runner.py"),
        "--freeze-dir",
        str(args.freeze_dir),
        "--source-frame",
        str(args.source_frame),
        "--output-dir",
        str(args.output_dir),
        "--dotenv-path",
        str(args.dotenv_path),
        "--acknowledge-network-collection",
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-dir", type=Path, default=DEFAULT_FREEZE_DIR)
    parser.add_argument("--source-frame", type=Path, default=DEFAULT_SOURCE_FRAME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dotenv-path", type=Path, default=DEFAULT_DOTENV)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (args.output_dir / ".supervisor.lock").open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another STRATZ corpus supervisor is already running", file=sys.stderr)
        return 2

    authentication_retry_used = False
    while True:
        result = subprocess.run(_command(args), cwd=ROOT, check=False)
        state = _state(args.output_dir)
        status = state.get("status")
        if status == "COMPLETE":
            return 0
        if status == "PARTIAL_PAUSED":
            authentication_retry_used = False
            resume_at = state.get("resume_at")
            if not isinstance(resume_at, str):
                print("paused runner did not provide resume_at", file=sys.stderr)
                return 2
            delay = seconds_until(resume_at) + 2
            print(f"quota pause; sleeping {delay:.0f}s until {resume_at}", flush=True)
            time.sleep(delay)
            continue
        if (
            status == "STOP"
            and state.get("stop_kind") == "authentication_failure"
            and not authentication_retry_used
        ):
            authentication_retry_used = True
            print("isolated authentication failure; retrying once in 60s", flush=True)
            time.sleep(60)
            continue
        print(
            f"collector stopped: status={status!r}, reason={state.get('stop_reason')!r}",
            file=sys.stderr,
        )
        return result.returncode or 2


if __name__ == "__main__":
    raise SystemExit(main())
