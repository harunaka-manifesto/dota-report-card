#!/usr/bin/env python3
"""Drive the Pass-2 collector until it completes or hits a hard stop.

Pass 2 is roughly thirteen thousand requests against an hourly-limited
endpoint, so it will pause for quota several times before it finishes. The
supervisor exists so that a multi-hour collection survives those pauses without
someone watching it, exactly as the pass-1 supervisor does.

It holds an exclusive lock on the output directory, so two supervisors cannot
interleave writes into one corpus.
"""

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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from legacy.scripts.stratz_v7_corpus_runner import (  # noqa: E402
    DEFAULT_FREEZE_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_FRAME,
)
from legacy.scripts.stratz_v7_pass2_runner import DEFAULT_PASS2_OUTPUT_DIR  # noqa: E402

#: A pause whose resume time has already passed still gets a short floor, so a
#: misreported reset cannot turn into a hot retry loop.
MIN_PAUSE_SECONDS = 5.0

#: How many consecutive collector runs may fail to make any progress before the
#: supervisor gives up. Without this it will happily respawn a child that cannot
#: start at all: observed in the wild as a 13-hour spin after the launching
#: terminal closed and the inherited stdin became a bad file descriptor.
MAX_STALLED_ATTEMPTS = 3


def seconds_until(value: str, *, now: datetime | None = None) -> float:
    target = datetime.fromisoformat(value)
    if target.tzinfo is None:
        raise ValueError("resume_at must include a timezone")
    return max(0.0, (target - (now or datetime.now(UTC))).total_seconds())


def read_state(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "manifests/state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read pass-2 state: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("pass-2 state must be a JSON object")
    return value


def collect_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "legacy/scripts/stratz_v7_pass2_runner.py"),
        "collect",
        "--freeze-dir",
        str(args.freeze_dir),
        "--source-frame",
        str(args.source_frame),
        "--pass1-dir",
        str(args.pass1_dir),
        "--output-dir",
        str(args.output_dir),
        "--dotenv",
        str(args.dotenv),
        "--max-accounts",
        str(args.max_accounts),
        "--acknowledge-network-collection",
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-dir", type=Path, default=DEFAULT_FREEZE_DIR)
    parser.add_argument("--source-frame", type=Path, default=DEFAULT_SOURCE_FRAME)
    parser.add_argument("--pass1-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PASS2_OUTPUT_DIR)
    parser.add_argument("--dotenv", type=Path, default=Path(".env"))
    parser.add_argument("--max-accounts", type=int, default=300)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (args.output_dir / ".supervisor.lock").open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another pass-2 supervisor is already running", file=sys.stderr)
        return 2

    authentication_retry_used = False
    stalled = 0
    last_attempts = -1
    while True:
        # stdin is DEVNULL on purpose. A detached supervisor outlives the shell
        # that launched it, and an inherited-but-closed stdin makes CPython die
        # during interpreter start-up with "can't initialize sys standard
        # streams" - before it can run, report, or record anything.
        result = subprocess.run(
            collect_command(args), cwd=ROOT, check=False, stdin=subprocess.DEVNULL
        )
        state = read_state(args.output_dir)
        status = state.get("status")

        attempts = state.get("physical_attempts")
        if attempts == last_attempts:
            stalled += 1
            if stalled >= MAX_STALLED_ATTEMPTS:
                print(
                    f"collector made no progress across {stalled} consecutive runs "
                    f"(exit code {result.returncode}); stopping rather than spinning. "
                    "Check the log above for a start-up failure.",
                    file=sys.stderr,
                )
                return result.returncode or 3
        else:
            stalled = 0
        last_attempts = attempts
        if status == "COMPLETE":
            print("pass 2 complete")
            return 0
        if status == "PARTIAL_PAUSED":
            authentication_retry_used = False
            resume_at = state.get("resume_at")
            if not isinstance(resume_at, str):
                print("paused runner did not provide resume_at", file=sys.stderr)
                return 2
            delay = max(MIN_PAUSE_SECONDS, seconds_until(resume_at) + 2)
            print(f"quota pause; sleeping {delay:.0f}s until {resume_at}", flush=True)
            time.sleep(delay)
            continue
        if (
            status == "STOP"
            and state.get("stop_kind") == "authentication_failure"
            and not authentication_retry_used
        ):
            # STRATZ and Cloudflare produce isolated auth-shaped rejections
            # during otherwise healthy collections. One retry, then stop.
            authentication_retry_used = True
            print("isolated authentication failure; retrying once in 60s", flush=True)
            time.sleep(60)
            continue
        print(
            f"pass 2 stopped: status={status!r} kind={state.get('stop_kind')!r} "
            f"reason={state.get('stop_reason')!r}",
            file=sys.stderr,
        )
        return result.returncode or 2


if __name__ == "__main__":
    raise SystemExit(main())
