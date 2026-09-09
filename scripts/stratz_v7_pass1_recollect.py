#!/usr/bin/env python3
"""
Recollect the V7 Pass-1 STRATZ match-history corpus as a NEW analytical lineage.

Purpose
-------
This is a narrow recovery collector for the V7 runtime-context blocker. It reuses
the repository's existing frozen STRATZ cohort, frozen history GraphQL operation,
normalization/canonicalization, rate limiting, response archiving, and resume
logic from scripts/stratz_v7_corpus_runner.py.

Important:
- Default scope is DISCOVERY only (600 predeclared players).
- It NEVER reads/collects CALIBRATION_RESERVED or SEALED_VALIDATION.
- It NEVER collects parsed-match detail.
- It preserves the ORIGINAL 365-day window from the surviving old state file,
  so the new corpus is as comparable as possible to the reviewed run.
- It writes to a NEW output directory and must be treated as NEW LINEAGE,
  not as restoration/reproduction of the lost Pass-1 source corpus.
- It refuses output paths that resolve under /tmp, /private/tmp, or /var/tmp.
- Network access requires an explicit acknowledgement flag.

Run this only if the exact-artifact recovery audit concludes that fresh
collection is required.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.stratz_v7_corpus_runner import (
        DEFAULT_ENDPOINT,
        DEFAULT_FREEZE_DIR,
        DEFAULT_SOURCE_FRAME,
        CorpusRunner,
        PauseRun,
        RunnerError,
        StopRun,
        _read_json,
        _write_json,
        load_frozen_cohort,
        load_stratz_token,
    )
except ImportError as exc:
    raise SystemExit(
        "Could not import scripts.stratz_v7_corpus_runner. "
        "Run this script from the V7 repo containing the original STRATZ corpus runner."
    ) from exc


DEFAULT_SOURCE_STATE = (
    ROOT / ".local/corpora/stratz/v7-corpus-2026-09-02/manifests/state.json"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / ".local/corpora/stratz/v7-pass1-history-new-lineage-2026-09-07"
)

FORBIDDEN_TEMP_ROOTS = tuple(Path(p).resolve() for p in ("/tmp", "/private/tmp", "/var/tmp"))
ALLOWED_TARGET_SPLITS = {"DISCOVERY", "CANDIDATE_TEST"}


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_durable_output(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    for root in FORBIDDEN_TEMP_ROOTS:
        if _is_under(resolved, root):
            raise RunnerError(
                f"refusing non-durable output path: {resolved} resolves under {root}"
            )
    return resolved


def load_original_window(source_state: Path) -> dict[str, int]:
    state = _read_json(source_state)
    window = state.get("window")
    if not isinstance(window, Mapping):
        raise RunnerError("source state has no history window")

    start = window.get("start_timestamp")
    end = window.get("end_timestamp")
    days = window.get("days")

    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start > end
        or days != 365
    ):
        raise RunnerError("source state does not contain a valid frozen 365-day window")

    return {
        "start_timestamp": start,
        "end_timestamp": end,
        "days": 365,
    }


def verify_source_state_binding(source_state: Path, cohort: Any) -> None:
    state = _read_json(source_state)
    freeze = state.get("freeze")
    if not isinstance(freeze, Mapping):
        raise RunnerError("source state has no freeze binding")

    expected = {
        "split_manifest_sha256": cohort.split_digest,
        "corpus_plan_sha256": cohort.plan_digest,
        "source_frame_sha256": cohort.frame_digest,
    }
    for key, value in expected.items():
        if freeze.get(key) != value:
            raise RunnerError(
                f"source state does not bind to the currently frozen cohort: {key}"
            )


def selected_targets(cohort: Any, *, include_candidate_test: bool) -> tuple[Any, ...]:
    allowed = {"DISCOVERY"}
    if include_candidate_test:
        allowed.add("CANDIDATE_TEST")

    targets = tuple(t for t in cohort.targets if t.split in allowed)

    observed = Counter(t.split for t in targets)
    if observed.get("DISCOVERY", 0) != 600:
        raise RunnerError(
            f"expected exactly 600 DISCOVERY targets; found {observed.get('DISCOVERY', 0)}"
        )
    if include_candidate_test and observed.get("CANDIDATE_TEST", 0) != 300:
        raise RunnerError(
            "expected exactly 300 CANDIDATE_TEST targets when explicitly included"
        )

    # The frozen cohort loader already excludes reserved/sealed rows, but assert again.
    bad = [t.split for t in targets if t.split not in ALLOWED_TARGET_SPLITS]
    if bad:
        raise RunnerError(f"reserved/sealed target leaked into recollection: {sorted(set(bad))}")

    return targets


def build_recollection_manifest(
    *,
    output_dir: Path,
    source_state: Path,
    cohort: Any,
    targets: Sequence[Any],
    runner: CorpusRunner,
    include_candidate_test: bool,
) -> dict[str, Any]:
    states = runner.state.get("history", {}).get("accounts", {})
    selected_states = [
        states.get(t.pseudonym, {"status": "pending"})
        for t in targets
    ]

    canonical_dir = output_dir / "canonical/history"
    canonical_files = list(canonical_dir.glob("*.json")) if canonical_dir.exists() else []

    manifest = {
        "schema_version": "stratz-v7-pass1-history-recollection-1.0.0",
        "lineage": {
            "kind": "NEW_LINEAGE",
            "restoration_of_lost_pass1": False,
            "purpose": "runtime_context_projection_recovery",
            "created_at": datetime.now(UTC).isoformat(),
        },
        "source": {
            "old_state_path": str(source_state),
            "old_window_reused": True,
            "window": runner.state.get("window"),
            "split_manifest_sha256": cohort.split_digest,
            "corpus_plan_sha256": cohort.plan_digest,
            "source_frame_sha256": cohort.frame_digest,
        },
        "scope": {
            "discovery_players_predeclared": 600,
            "candidate_test_included": include_candidate_test,
            "candidate_test_players_predeclared": 300 if include_candidate_test else 0,
            "calibration_reserved_touched": False,
            "sealed_validation_touched": False,
            "parsed_collection": False,
        },
        "status": {
            "runner_status": runner.state.get("status"),
            "phase": runner.state.get("phase"),
            "selected_targets": len(targets),
            "complete": sum(
                isinstance(s, Mapping) and s.get("status") == "complete"
                for s in selected_states
            ),
            "truncated": sum(
                isinstance(s, Mapping) and s.get("status") == "truncated"
                for s in selected_states
            ),
            "unavailable": sum(
                isinstance(s, Mapping) and s.get("status") in {"private", "unavailable"}
                for s in selected_states
            ),
            "failed": sum(
                isinstance(s, Mapping) and s.get("status") == "failed"
                for s in selected_states
            ),
            "pending": sum(
                not isinstance(s, Mapping) or s.get("status") == "pending"
                for s in selected_states
            ),
            "canonical_history_files": len(canonical_files),
            "physical_attempts": len(runner.ledger_rows),
        },
        "safety": {
            "output_dir_resolved": str(output_dir.resolve()),
            "output_under_temp": False,
            "opendota_calls": 0,
            "rank_or_mmr_used": False,
        },
    }
    _write_json(output_dir / "manifests/recollection-manifest.json", manifest)
    return manifest


async def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = assert_durable_output(args.output_dir)

    cohort = load_frozen_cohort(
        args.freeze_dir,
        source_frame_path=args.source_frame,
    )
    verify_source_state_binding(args.source_state, cohort)
    original_window = load_original_window(args.source_state)

    targets = selected_targets(
        cohort,
        include_candidate_test=args.include_candidate_test,
    )

    token = None
    if args.acknowledge_new_lineage_collection:
        if args.dotenv_path is None:
            raise RunnerError(
                "network collection requires --dotenv-path containing STRATZ_API_TOKEN"
            )
        token = load_stratz_token(args.dotenv_path)

    async with CorpusRunner(
        cohort,
        output_dir=output_dir,
        token=token,
        endpoint=args.endpoint,
        network=args.acknowledge_new_lineage_collection,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        max_history_pages=args.max_history_pages,
    ) as runner:
        # New output dirs get a "now"-based window from CorpusRunner.
        # Replace it BEFORE any request with the surviving original frozen window.
        existing_window = runner.state.get("window")
        has_activity = bool(runner.ledger_rows) or any(
            isinstance(v, Mapping) and v.get("status") not in {None, "pending"}
            for v in runner.state.get("history", {}).get("accounts", {}).values()
        )

        if has_activity and existing_window != original_window:
            raise RunnerError(
                "resume state already contains collection activity with a different window; "
                "refusing to mutate lineage"
            )

        runner.state["window"] = original_window
        runner.state["phase"] = "PASS1_HISTORY_NEW_LINEAGE"
        runner.state["lineage"] = {
            "kind": "NEW_LINEAGE",
            "restoration_of_lost_pass1": False,
            "source_state": str(args.source_state),
            "scope": "DISCOVERY+CANDIDATE_TEST"
            if args.include_candidate_test
            else "DISCOVERY_ONLY",
            "parsed_collection": False,
        }
        runner._save_state()

        # Offline preflight: validates bindings and writes no provider request.
        if not args.acknowledge_new_lineage_collection:
            manifest = build_recollection_manifest(
                output_dir=output_dir,
                source_state=args.source_state,
                cohort=cohort,
                targets=targets,
                runner=runner,
                include_candidate_test=args.include_candidate_test,
            )
            return {
                "status": "OFFLINE_VALIDATED",
                "network_calls": {"stratz": 0, "opendota": 0},
                "selected_targets": len(targets),
                "window": original_window,
                "output_dir": str(output_dir),
                "manifest": str(
                    output_dir / "manifests/recollection-manifest.json"
                ),
            }

        runner.state["status"] = "RUNNING"
        runner._save_state()

        try:
            for target in targets:
                await runner._acquire_history(target)

            runner.state["status"] = "COMPLETE"
            runner.state["phase"] = "PASS1_HISTORY_NEW_LINEAGE_COMPLETE"
            runner.state["stop_reason"] = None
            runner.state["resume_at"] = None

        except PauseRun as exc:
            runner.state["status"] = "PARTIAL_PAUSED"
            runner.state["stop_reason"] = exc.reason
            runner.state["resume_at"] = exc.resume_at

        except StopRun as exc:
            runner.state["status"] = "STOP"
            runner.state["stop_reason"] = exc.reason
            runner.state["stop_kind"] = exc.kind

        except RunnerError as exc:
            runner.state["status"] = "STOP"
            runner.state["stop_reason"] = str(exc)
            runner.state["stop_kind"] = "runner_error"

        runner._save_state()

        manifest = build_recollection_manifest(
            output_dir=output_dir,
            source_state=args.source_state,
            cohort=cohort,
            targets=targets,
            runner=runner,
            include_candidate_test=args.include_candidate_test,
        )

        return {
            "status": runner.state.get("status"),
            "phase": runner.state.get("phase"),
            "physical_attempts": len(runner.ledger_rows),
            "stop_reason": runner.state.get("stop_reason"),
            "resume_at": runner.state.get("resume_at"),
            "network_calls": {
                "stratz": len(runner.ledger_rows),
                "opendota": 0,
            },
            "selected_targets": len(targets),
            "window": original_window,
            "output_dir": str(output_dir),
            "manifest": str(
                output_dir / "manifests/recollection-manifest.json"
            ),
            "lineage": "NEW_LINEAGE",
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-dir", type=Path, default=DEFAULT_FREEZE_DIR)
    parser.add_argument("--source-frame", type=Path, default=DEFAULT_SOURCE_FRAME)
    parser.add_argument("--source-state", type=Path, default=DEFAULT_SOURCE_STATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dotenv-path", type=Path)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-history-pages", type=int, default=25)
    parser.add_argument(
        "--include-candidate-test",
        action="store_true",
        help=(
            "Also recollect the 300 CANDIDATE_TEST history accounts. "
            "Default is DISCOVERY only because the reviewed final Finding fit read DISCOVERY only."
        ),
    )
    parser.add_argument(
        "--acknowledge-new-lineage-collection",
        action="store_true",
        help=(
            "Actually enable STRATZ network collection. Without this flag the script "
            "only validates cohort/window/output safety and performs zero provider calls."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = asyncio.run(run(args))
    except (RunnerError, httpx.HTTPError, OSError, ValueError) as exc:
        print(f"V7 Pass-1 recollection stopped: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if result.get("status") in {
        "OFFLINE_VALIDATED",
        "COMPLETE",
        "PARTIAL_PAUSED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
