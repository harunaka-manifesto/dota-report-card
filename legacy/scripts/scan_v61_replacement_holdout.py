#!/usr/bin/env python3
"""Run the private, resumable V6.1 replacement-history scan."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.ingestion.summary_history_contract import (  # noqa: E402
    SUMMARY_HISTORY_PROJECTION_VERSION,
    SUMMARY_HISTORY_PROVIDER_LIMIT,
    SUMMARY_HISTORY_RETRY_LIMIT,
    SUMMARY_HISTORY_WINDOW_DAYS,
    request_manifest,
)
from app.ingestion.summary_normalize import previous_year_window  # noqa: E402

from scripts.prepare_v61_replacement_holdout import (  # noqa: E402
    EXPECTED_SALT_BYTES,
    EXPECTED_UNTOUCHED_RESERVE,
    ORDER_DIGEST_FORMAT,
    _order_digest,
    _pseudonym,
    load_candidate_ids,
    sha256_file,
)
from scripts.prepare_v61_replacement_holdout import (  # noqa: E402
    SCHEMA_VERSION as PRECOMMIT_SCHEMA_VERSION,
)

SCAN_SCHEMA_VERSION = "v61-replacement-holdout-scan-1.0.0"
RAW_ARCHIVE_SCHEMA_VERSION = "v61-raw-summary-archive-1.0.0"
MAX_NETWORK_REQUESTS_PER_MINUTE = 240
MIN_NETWORK_REQUEST_INTERVAL_SECONDS = 60 / MAX_NETWORK_REQUESTS_PER_MINUTE
EXPECTED_CANDIDATE_COUNT = EXPECTED_UNTOUCHED_RESERVE
EXPECTED_CANDIDATE_ORDER_SHA256 = (
    "7957c80bdd059013eac188e8244441289c2fe5165f161ceba0fd4b8e889d79fe"
)
PROFILE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RELEASE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
TERMINAL_STATUSES = frozenset({"success", "failed", "indeterminate"})
STATE_STATUSES = TERMINAL_STATUSES | {"attempt_started"}
PRIVATE_IDENTIFIER_KEYS = frozenset(
    {"account_id", "account_ids", "player_id", "player_ids", "steam_id"}
)
FORBIDDEN_ANALYTICAL_KEYS = frozenset(
    {"average_rank", "mmr", "rank", "rank_tier", "skill", "skill_bracket"}
)


class NetworkRequestPacer:
    """Space sequential network-request start times with a monotonic clock."""

    def __init__(
        self,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    ) -> None:
        self._monotonic = monotonic
        self._sleep = sleep
        self._next_allowed_start: float | None = None

    async def before_network_attempt(self) -> None:
        if self._next_allowed_start is not None:
            now = self._monotonic()
            if now < self._next_allowed_start:
                await self._sleep(self._next_allowed_start - now)
        actual_start = self._monotonic()
        self._next_allowed_start = (
            actual_start + MIN_NETWORK_REQUEST_INTERVAL_SECONDS
        )


@dataclass(frozen=True, slots=True)
class Candidate:
    index: int
    account_id: int
    profile_id: str


@dataclass(frozen=True, slots=True)
class ScanContext:
    precommit_path: Path
    salt: bytes
    raw_archive_dir: Path
    state_dir: Path
    output_path: Path
    candidates: tuple[Candidate, ...]
    manifest: dict[str, Any]

    @property
    def candidate_state_dir(self) -> Path:
        return self.state_dir / "candidates"

    @property
    def result_dir(self) -> Path:
        return self.state_dir / "results"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_private_directory(path: Path) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise ValueError("private directory is invalid")
        if stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ValueError("private directory has the wrong mode")
        return
    path.mkdir(parents=True, mode=0o700)
    path.chmod(0o700)


def _assert_private_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private state file is invalid")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError("private state file has the wrong mode")


def _read_json_object(path: Path, *, private: bool) -> dict[str, Any]:
    if private:
        _assert_private_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JSON state is unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON state must be an object")
    return payload


def _write_all(descriptor: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        offset += os.write(descriptor, value[offset:])


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> None:
    expected = _json_bytes(payload)
    _ensure_private_directory(path.parent)
    if path.exists():
        _assert_private_file(path)
        if path.read_bytes() != expected:
            raise ValueError("immutable scan manifest differs")
        return
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _write_all(descriptor, expected)
        os.fsync(descriptor)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)
    path.chmod(0o600)
    _fsync_directory(path.parent)


def _write_atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    _ensure_private_directory(path.parent)
    if path.exists():
        _assert_private_file(path)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise ValueError("partial private state file exists")
    expected = _json_bytes(payload)
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _write_all(descriptor, expected)
        os.fsync(descriptor)
        os.replace(temporary, path)
        path.chmod(0o600)
        _fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)


def _profile_digest(profile_ids: Sequence[str]) -> str:
    return _sha256_bytes(("\n".join(profile_ids) + "\n").encode("ascii"))


def _expected_collection_contract() -> dict[str, Any]:
    return {
        "summary_requests_per_candidate": 1,
        "planned_summary_requests": EXPECTED_CANDIDATE_COUNT,
        "planned_detail_requests": 0,
        "planned_parse_requests": 0,
        "retry_limit": SUMMARY_HISTORY_RETRY_LIMIT,
        "window_days": SUMMARY_HISTORY_WINDOW_DAYS,
        "provider_limit": SUMMARY_HISTORY_PROVIDER_LIMIT,
        "projection_version": SUMMARY_HISTORY_PROJECTION_VERSION,
        "raw_archive_required": True,
    }


def _validate_release_sha(release_sha: str) -> None:
    if not RELEASE_SHA_PATTERN.fullmatch(release_sha):
        raise ValueError("release SHA is invalid")


def _validate_precommit(
    path: Path,
    *,
    release_sha: str,
    expected_candidate_count: int,
) -> tuple[dict[str, Any], tuple[int, ...], str]:
    payload, account_ids = load_candidate_ids(path, label="precommit manifest")
    if payload.get("schema_version") != PRECOMMIT_SCHEMA_VERSION:
        raise ValueError("precommit manifest schema is invalid")
    if payload.get("release_sha") != release_sha:
        raise ValueError("precommit manifest release SHA differs")
    if payload.get("candidate_count") != len(account_ids):
        raise ValueError("precommit candidate count metadata is invalid")
    if len(account_ids) != expected_candidate_count:
        raise ValueError("precommit candidate count is invalid")
    if payload.get("candidate_order_digest_format") != ORDER_DIGEST_FORMAT:
        raise ValueError("precommit candidate order format is invalid")
    order_sha256 = _order_digest(account_ids)
    if payload.get("candidate_order_sha256") != order_sha256:
        raise ValueError("precommit candidate order digest is invalid")
    if (
        expected_candidate_count == EXPECTED_CANDIDATE_COUNT
        and order_sha256 != EXPECTED_CANDIDATE_ORDER_SHA256
    ):
        raise ValueError("precommit candidate order is not the sealed reserve order")
    exclusions = payload.get("exclusions")
    if not isinstance(exclusions, Mapping):
        raise ValueError("precommit exclusions are invalid")
    if exclusions.get("current_population_overlap_count") != 0:
        raise ValueError("precommit current-population overlap is nonzero")
    if payload.get("collection_contract") != _expected_collection_contract().copy() | {
        "planned_summary_requests": expected_candidate_count
    }:
        raise ValueError("precommit collection contract is invalid")
    return payload, account_ids, sha256_file(path)


def _build_scan_manifest(
    *,
    precommit_path: Path,
    precommit_sha256: str,
    release_sha: str,
    candidates: Sequence[Candidate],
    raw_archive_dir: Path,
    state_dir: Path,
    output_path: Path,
    window_start: int,
    window_end: int,
) -> dict[str, Any]:
    profile_ids = [candidate.profile_id for candidate in candidates]
    collection_contract = _expected_collection_contract().copy()
    collection_contract["planned_summary_requests"] = len(candidates)
    return {
        "schema_version": SCAN_SCHEMA_VERSION,
        "release_sha": release_sha,
        "precommit_manifest_sha256": precommit_sha256,
        "candidate_order_sha256": _order_digest(
            [candidate.account_id for candidate in candidates]
        ),
        "candidate_count": len(candidates),
        "requested_candidate_count": len(candidates),
        "candidate_profile_ids": profile_ids,
        "candidate_profile_ids_sha256": _profile_digest(profile_ids),
        "window_start": window_start,
        "window_end": window_end,
        "window_days": SUMMARY_HISTORY_WINDOW_DAYS,
        "window": {
            "days": SUMMARY_HISTORY_WINDOW_DAYS,
            "start_time": window_start,
            "end_time": window_end,
        },
        "provider_limit": SUMMARY_HISTORY_PROVIDER_LIMIT,
        "retry_limit": SUMMARY_HISTORY_RETRY_LIMIT,
        "summary_requests_per_candidate": 1,
        "detail_requests": 0,
        "parse_requests": 0,
        "raw_archive_required": True,
        "rank_or_mmr_used": False,
        "collection_contract": collection_contract,
        "request_contract": request_manifest(),
        "precommit_manifest_path": str(precommit_path),
        "raw_archive_dir": str(raw_archive_dir),
        "state_dir": str(state_dir),
        "output_path": str(output_path),
    }


def _validate_scan_manifest(
    payload: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
) -> None:
    if dict(payload) != dict(expected):
        raise ValueError("immutable scan manifest does not match resume inputs")


def _assert_private_root(paths: Sequence[Path]) -> None:
    root = (ROOT / ".local" / "calibration" / "v61").resolve()
    for path in paths:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("scan state must remain under .local/calibration/v61") from exc


def _assert_clean_worktree(release_sha: str) -> None:
    try:
        status = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        )
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("git release state cannot be verified") from exc
    if status.stdout.strip():
        raise RuntimeError("scan requires a clean worktree")
    if head != release_sha:
        raise RuntimeError("scan release SHA does not match HEAD")


def _validate_layout(directory: Path, expected_names: set[str]) -> None:
    _ensure_private_directory(directory)
    for child in directory.iterdir():
        if child.is_symlink() or child.is_dir():
            raise ValueError("private state layout is invalid")
        if child.name.endswith(".tmp") or child.name not in expected_names:
            raise ValueError("private state layout contains an unexpected file")
        _assert_private_file(child)


def _validate_archive_layout(directory: Path) -> None:
    _ensure_private_directory(directory)
    for child in directory.iterdir():
        if child.is_symlink() or child.is_dir():
            raise ValueError("raw archive layout is invalid")
        if child.name.endswith(".tmp"):
            raise ValueError("partial raw archive exists")
        if not child.name.endswith(".json") or not PROFILE_ID_PATTERN.fullmatch(
            child.stem
        ):
            raise ValueError("raw archive layout contains an unexpected file")
        _assert_private_file(child)


def _prepare_context(
    *,
    precommit_path: Path,
    salt_path: Path,
    raw_archive_dir: Path,
    state_dir: Path,
    output_path: Path,
    release_sha: str,
    expected_candidate_count: int,
    require_clean_worktree: bool,
    require_private_root: bool,
    now: int | None,
) -> ScanContext:
    _validate_release_sha(release_sha)
    precommit_path = precommit_path.resolve()
    salt_path = salt_path.resolve()
    raw_archive_dir = raw_archive_dir.resolve()
    state_dir = state_dir.resolve()
    output_path = output_path.resolve()
    if require_private_root:
        _assert_private_root((raw_archive_dir, state_dir, output_path))
    _, account_ids, precommit_sha256 = _validate_precommit(
        precommit_path,
        release_sha=release_sha,
        expected_candidate_count=expected_candidate_count,
    )
    try:
        salt = salt_path.read_bytes()
    except OSError as exc:
        raise ValueError("calibration salt is unreadable") from exc
    if len(salt) < EXPECTED_SALT_BYTES:
        raise ValueError("calibration salt is too short")
    candidates = tuple(
        Candidate(index, account_id, _pseudonym(account_id, salt))
        for index, account_id in enumerate(account_ids)
    )
    manifest_path = state_dir / "scan-manifest.json"
    state_dir_exists = state_dir.exists()
    if state_dir_exists and (state_dir.is_symlink() or not state_dir.is_dir()):
        raise ValueError("private state directory is invalid")
    if require_clean_worktree:
        _assert_clean_worktree(release_sha)

    if manifest_path.exists():
        _assert_private_file(manifest_path)
        existing = _read_json_object(manifest_path, private=True)
        window_start = existing.get("window_start")
        window_end = existing.get("window_end")
        if (
            isinstance(window_start, bool)
            or not isinstance(window_start, int)
            or isinstance(window_end, bool)
            or not isinstance(window_end, int)
        ):
            raise ValueError("scan window is invalid")
        if previous_year_window(
            window_end=window_end,
            days=SUMMARY_HISTORY_WINDOW_DAYS,
        ) != (window_start, window_end):
            raise ValueError("scan window is not the fixed 365-day boundary")
        expected = _build_scan_manifest(
            precommit_path=precommit_path,
            precommit_sha256=precommit_sha256,
            release_sha=release_sha,
            candidates=candidates,
            raw_archive_dir=raw_archive_dir,
            state_dir=state_dir,
            output_path=output_path,
            window_start=window_start,
            window_end=window_end,
        )
        _validate_scan_manifest(existing, expected=expected)
        manifest = dict(existing)
        candidate_state_dir = state_dir / "candidates"
        result_dir = state_dir / "results"
        _validate_layout(
            candidate_state_dir,
            {f"{candidate.profile_id}.json" for candidate in candidates},
        )
        _validate_layout(
            result_dir,
            {f"{candidate.profile_id}.json" for candidate in candidates},
        )
        if not raw_archive_dir.exists():
            raise ValueError("raw archive directory is missing on resume")
        _validate_archive_layout(raw_archive_dir)
    else:
        if state_dir_exists and any(state_dir.iterdir()):
            raise ValueError("private state is partial without its immutable manifest")
        window_end = int(
            datetime.now(UTC).timestamp() if now is None else now
        )
        window_start, window_end = previous_year_window(
            window_end=window_end,
            days=SUMMARY_HISTORY_WINDOW_DAYS,
        )
        manifest = _build_scan_manifest(
            precommit_path=precommit_path,
            precommit_sha256=precommit_sha256,
            release_sha=release_sha,
            candidates=candidates,
            raw_archive_dir=raw_archive_dir,
            state_dir=state_dir,
            output_path=output_path,
            window_start=window_start,
            window_end=window_end,
        )
        _write_once_json(manifest_path, manifest)
        _ensure_private_directory(state_dir / "candidates")
        _ensure_private_directory(state_dir / "results")
        _ensure_private_directory(raw_archive_dir)

    _ensure_private_directory(output_path.parent)
    return ScanContext(
        precommit_path,
        salt,
        raw_archive_dir,
        state_dir,
        output_path,
        candidates,
        manifest,
    )


def _state_path(context: ScanContext, candidate: Candidate) -> Path:
    return context.candidate_state_dir / f"{candidate.profile_id}.json"


def _result_path(context: ScanContext, candidate: Candidate) -> Path:
    return context.result_dir / f"{candidate.profile_id}.json"


def _archive_path(context: ScanContext, candidate: Candidate) -> Path:
    return context.raw_archive_dir / f"{candidate.profile_id}.json"


def _validate_private_payload(value: Any, *, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            folded = str(key).casefold()
            if folded in PRIVATE_IDENTIFIER_KEYS:
                raise ValueError(f"private identifier in {path}")
            if folded in FORBIDDEN_ANALYTICAL_KEYS or (
                "mmr" in folded or folded.startswith("rank")
            ):
                if not (folded == "rank_or_mmr_used" and nested is False):
                    raise ValueError(f"rank/MMR field in {path}")
            _validate_private_payload(nested, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _validate_private_payload(nested, path=f"{path}[{index}]")


def _validate_profile(profile: Mapping[str, Any], candidate: Candidate) -> dict[str, Any]:
    _validate_private_payload(profile)
    if profile.get("profile_id") != candidate.profile_id:
        raise ValueError("normalized profile ownership is invalid")
    if profile.get("status") not in {"eligible", "ineligible"}:
        raise ValueError("normalized profile status is invalid")
    matches = profile.get("matches")
    if not isinstance(matches, list):
        raise ValueError("normalized profile matches are invalid")
    eligible_match_count = profile.get("eligible_match_count")
    if (
        isinstance(eligible_match_count, bool)
        or not isinstance(eligible_match_count, int)
        or eligible_match_count < 0
    ):
        raise ValueError("normalized profile match count is invalid")
    return dict(profile)


def _read_state(path: Path, candidate: Candidate) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = _read_json_object(path, private=True)
    if payload.get("schema_version") != SCAN_SCHEMA_VERSION:
        raise ValueError("candidate state schema is invalid")
    if payload.get("candidate_index") != candidate.index:
        raise ValueError("candidate state order is invalid")
    if payload.get("profile_id") != candidate.profile_id:
        raise ValueError("candidate state profile is invalid")
    status = payload.get("status")
    if status not in STATE_STATUSES:
        raise ValueError("candidate state status is invalid")
    attempt_count = payload.get("attempt_count")
    if isinstance(attempt_count, bool) or not isinstance(attempt_count, int):
        raise ValueError("candidate state attempt count is invalid")
    if attempt_count not in {0, 1}:
        raise ValueError("candidate state retry count is invalid")
    if status == "attempt_started" and attempt_count != 1:
        raise ValueError("attempt marker is not durable")
    if status in {"failed", "indeterminate"} and attempt_count != 1:
        raise ValueError("terminal request state is invalid")
    if status == "attempt_started" and payload.get("request_accounting") != "network_attempt":
        raise ValueError("attempt marker accounting is invalid")
    if status == "failed":
        if payload.get("request_accounting") != "network_attempt":
            raise ValueError("failed request accounting is invalid")
        if not isinstance(payload.get("exception_type"), str) or not isinstance(
            payload.get("error_category"), str
        ):
            raise ValueError("failed request metadata is invalid")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", payload["exception_type"]):
            raise ValueError("failed request exception type is invalid")
        if payload["error_category"] not in {"collection", "network"}:
            raise ValueError("failed request category is invalid")
    if status == "indeterminate" and payload.get("request_accounting") != "indeterminate":
        raise ValueError("indeterminate request accounting is invalid")
    if status == "success" and payload.get("request_accounting") not in {
        "network_attempt",
        "archive_recovered",
        "archive_reused",
    }:
        raise ValueError("successful request accounting is invalid")
    if "result_sha256" in payload and not re.fullmatch(
        r"[0-9a-f]{64}", str(payload["result_sha256"])
    ):
        raise ValueError("candidate result checksum is invalid")
    return payload


def _read_result(path: Path, candidate: Candidate) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = _read_json_object(path, private=True)
    return _validate_profile(payload, candidate)


def _state_payload(
    candidate: Candidate,
    *,
    status: str,
    attempt_count: int,
    request_accounting: str,
    profile: Mapping[str, Any] | None = None,
    exception: BaseException | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCAN_SCHEMA_VERSION,
        "candidate_index": candidate.index,
        "profile_id": candidate.profile_id,
        "status": status,
        "attempt_count": attempt_count,
        "request_accounting": request_accounting,
    }
    if profile is not None:
        payload["result_sha256"] = _sha256_bytes(_json_bytes(profile))
    if exception is not None:
        exception_type = re.sub(r"[^A-Za-z0-9_.-]", "", type(exception).__name__)[:80]
        payload["exception_type"] = exception_type or "Exception"
        lowered = type(exception).__name__.casefold()
        payload["error_category"] = (
            "network"
            if any(token in lowered for token in ("http", "network", "timeout", "opendota"))
            else "collection"
        )
    return payload


def _load_archive_rows(
    path: Path,
    *,
    candidate: Candidate,
    context: ScanContext,
) -> list[dict[str, Any]]:
    _assert_private_file(path)
    payload = _read_json_object(path, private=True)
    if payload.get("schema_version") != RAW_ARCHIVE_SCHEMA_VERSION:
        raise ValueError("raw archive schema is invalid")
    if payload.get("profile_id") != candidate.profile_id:
        raise ValueError("raw archive profile is invalid")
    if payload.get("raw_identifiers_present") is not False:
        raise ValueError("raw archive privacy marker is invalid")
    if payload.get("rank_or_mmr_used") is not False:
        raise ValueError("raw archive analytical marker is invalid")
    if payload.get("provider_limit") != SUMMARY_HISTORY_PROVIDER_LIMIT:
        raise ValueError("raw archive provider limit is invalid")
    if payload.get("raw_count") != len(payload.get("raw_response", [])):
        raise ValueError("raw archive count is invalid")
    expected_window = {
        "days": SUMMARY_HISTORY_WINDOW_DAYS,
        "start_time": context.manifest["window_start"],
        "end_time": context.manifest["window_end"],
    }
    if payload.get("window") != expected_window:
        raise ValueError("raw archive window differs")
    source = payload.get("source")
    if not isinstance(source, Mapping) or source.get("request_parameters") != request_manifest()[
        "request_parameters"
    ]:
        raise ValueError("raw archive request contract is invalid")
    raw_response = payload.get("raw_response")
    if not isinstance(raw_response, list) or any(
        not isinstance(row, Mapping) for row in raw_response
    ):
        raise ValueError("raw archive response is invalid")
    _validate_private_payload(payload)
    try:
        from scripts.collect_v61_calibration_histories import (
            normalize_archived_summary_history,
        )

        normalize_archived_summary_history(path, account_id=candidate.account_id)
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("raw archive checksum validation failed") from exc
    return [dict(row) for row in raw_response]


class _ArchivedSource:
    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self.rows = [dict(row) for row in rows]

    async def get_summary_history_once(
        self,
        _account_id: int,
        *,
        days: int,
        project: Sequence[str],
        provider_limit: int,
    ) -> list[dict[str, Any]]:
        if (
            days != SUMMARY_HISTORY_WINDOW_DAYS
            or tuple(project) != tuple(request_manifest()["projection"])
            or provider_limit != SUMMARY_HISTORY_PROVIDER_LIMIT
        ):
            raise ValueError("archived normalization contract is invalid")
        return [dict(row) for row in self.rows]


async def _normalize_archive(
    path: Path,
    *,
    candidate: Candidate,
    context: ScanContext,
) -> dict[str, Any]:
    rows = _load_archive_rows(path, candidate=candidate, context=context)
    from scripts.collect_v61_calibration_histories import collect_profile

    profile = await collect_profile(
        _ArchivedSource(rows),
        candidate.account_id,
        salt=context.salt,
        window_start=context.manifest["window_start"],
        window_end=context.manifest["window_end"],
    )
    return _validate_profile(profile, candidate)


async def _scan_candidate(
    context: ScanContext,
    candidate: Candidate,
    *,
    client: Any | None,
    pacer: NetworkRequestPacer,
) -> tuple[str, dict[str, Any] | None]:
    state_path = _state_path(context, candidate)
    result_path = _result_path(context, candidate)
    archive_path = _archive_path(context, candidate)
    state = _read_state(state_path, candidate)
    result = _read_result(result_path, candidate)
    if state is not None and result is not None and state.get("result_sha256") != _sha256_bytes(
        _json_bytes(result)
    ):
        raise ValueError("candidate result checksum differs")
    if result is not None and not archive_path.exists():
        raise ValueError("normalized result exists without its raw archive")

    if state is not None:
        status = state["status"]
        if status == "failed":
            return status, None
        if status == "indeterminate":
            return status, None
        if not archive_path.exists():
            if status == "attempt_started":
                _write_atomic_json(
                    state_path,
                    _state_payload(
                        candidate,
                        status="indeterminate",
                        attempt_count=1,
                        request_accounting="indeterminate",
                    ),
                )
                return "indeterminate", None
            raise ValueError("successful state is missing its raw archive")
        if status == "attempt_started":
            if result is None:
                result = await _normalize_archive(
                    archive_path, candidate=candidate, context=context
                )
                _write_atomic_json(result_path, result)
            _load_archive_rows(archive_path, candidate=candidate, context=context)
            _write_atomic_json(
                state_path,
                _state_payload(
                    candidate,
                    status="success",
                    attempt_count=1,
                    request_accounting="archive_recovered",
                    profile=result,
                ),
            )
            return "success", result
        _load_archive_rows(archive_path, candidate=candidate, context=context)
        if result is None:
            result = await _normalize_archive(
                archive_path, candidate=candidate, context=context
            )
            _write_atomic_json(result_path, result)
        return "success", result

    if archive_path.exists():
        if result is None:
            result = await _normalize_archive(
                archive_path, candidate=candidate, context=context
            )
            _write_atomic_json(result_path, result)
        else:
            _load_archive_rows(archive_path, candidate=candidate, context=context)
        _write_atomic_json(
            state_path,
            _state_payload(
                candidate,
                status="success",
                attempt_count=0,
                request_accounting="archive_reused",
                profile=result,
            ),
        )
        return "success", result

    if client is None:
        raise RuntimeError("network collection acknowledgement is required")
    _write_atomic_json(
        state_path,
        _state_payload(
            candidate,
            status="attempt_started",
            attempt_count=1,
            request_accounting="network_attempt",
        ),
    )
    await pacer.before_network_attempt()
    try:
        from scripts.collect_v61_calibration_histories import collect_profile

        profile = await collect_profile(
            client,
            candidate.account_id,
            salt=context.salt,
            window_start=context.manifest["window_start"],
            window_end=context.manifest["window_end"],
            raw_archive_dir=context.raw_archive_dir,
        )
        profile = _validate_profile(profile, candidate)
        _load_archive_rows(archive_path, candidate=candidate, context=context)
        _write_atomic_json(result_path, profile)
        _write_atomic_json(
            state_path,
            _state_payload(
                candidate,
                status="success",
                attempt_count=1,
                request_accounting="network_attempt",
                profile=profile,
            ),
        )
        return "success", profile
    except Exception as request_error:
        failure = request_error
        if archive_path.exists():
            try:
                profile = await _normalize_archive(
                    archive_path, candidate=candidate, context=context
                )
                _write_atomic_json(result_path, profile)
                _write_atomic_json(
                    state_path,
                    _state_payload(
                        candidate,
                        status="success",
                        attempt_count=1,
                        request_accounting="archive_recovered",
                        profile=profile,
                    ),
                )
                return "success", profile
            except Exception as recovery_error:
                failure = recovery_error
        _write_atomic_json(
            state_path,
            _state_payload(
                candidate,
                status="failed",
                attempt_count=1,
                request_accounting="network_attempt",
                exception=failure,
            ),
        )
        return "failed", None


def _progress_counts(
    records: Sequence[tuple[str, dict[str, Any] | None]],
) -> tuple[int, int, int, int]:
    success = sum(status == "success" for status, _ in records)
    failed = sum(status == "failed" for status, _ in records)
    indeterminate = sum(status == "indeterminate" for status, _ in records)
    return success + failed + indeterminate, success, failed, indeterminate


def _compile_output(
    context: ScanContext,
    records: Sequence[tuple[str, dict[str, Any] | None]],
) -> dict[str, Any]:
    if len(records) != len(context.candidates):
        raise ValueError("scan did not reach every candidate")
    statuses: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    success_count = failure_count = indeterminate_count = 0
    eligible_count = ineligible_count = 0
    attempted = known_terminal = reused_archives = 0
    for candidate, (status, profile) in zip(context.candidates, records, strict=True):
        state = _read_state(_state_path(context, candidate), candidate)
        if state is None or state["status"] not in TERMINAL_STATUSES:
            raise ValueError("scan contains a nonterminal candidate")
        accounting = state["request_accounting"]
        attempted += state["attempt_count"]
        reused_archives += accounting == "archive_reused"
        if status == "success":
            if profile is None:
                raise ValueError("successful candidate has no normalized result")
            profile = _validate_profile(profile, candidate)
            profiles.append(profile)
            success_count += 1
            if profile["status"] == "eligible":
                eligible_count += 1
            else:
                ineligible_count += 1
            known_terminal += accounting in {"network_attempt", "archive_recovered"}
        elif status == "failed":
            failure_count += 1
            known_terminal += 1
        elif status == "indeterminate":
            indeterminate_count += 1
        else:
            raise ValueError("scan contains an invalid terminal status")
        statuses.append(
            {
                "candidate_index": candidate.index,
                "profile_id": candidate.profile_id,
                "status": status,
                "eligibility": profile["status"] if profile is not None else None,
                "request_accounting": accounting,
            }
        )
    return {
        "schema_version": SCAN_SCHEMA_VERSION,
        "release_sha": context.manifest["release_sha"],
        "precommit_manifest_sha256": context.manifest["precommit_manifest_sha256"],
        "candidate_order_sha256": context.manifest["candidate_order_sha256"],
        "candidate_count": context.manifest["candidate_count"],
        "requested_candidate_count": context.manifest["requested_candidate_count"],
        "window": context.manifest["window"],
        "window_start": context.manifest["window_start"],
        "window_end": context.manifest["window_end"],
        "success_count": success_count,
        "failure_count": failure_count,
        "indeterminate_count": indeterminate_count,
        "eligible_count": eligible_count,
        "ineligible_count": ineligible_count,
        "request_accounting": {
            "summary_requests_per_candidate": 1,
            "planned_summary_requests": context.manifest["candidate_count"],
            "attempted_summary_requests": attempted,
            "known_terminal_summary_requests": known_terminal,
            "indeterminate_summary_requests": indeterminate_count,
            "reused_archive_count": reused_archives,
            "detail_requests": 0,
            "parse_requests": 0,
            "retry_limit": 0,
        },
        "detail_requests": 0,
        "parse_requests": 0,
        "rank_or_mmr_used": False,
        "raw_archive_required": True,
        "raw_identifiers_present": False,
        "candidate_statuses": statuses,
        "profiles": profiles,
    }


async def run_scan(
    *,
    precommit_manifest: Path,
    salt: Path,
    raw_archive_dir: Path,
    state_dir: Path,
    output: Path,
    release_sha: str,
    client: Any | None = None,
    acknowledge_network_collection: bool = False,
    require_clean_worktree: bool = False,
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
    now: int | None = None,
    progress: bool = False,
    require_private_root: bool = False,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> dict[str, Any]:
    if not acknowledge_network_collection:
        raise RuntimeError("network collection acknowledgement is required")
    context = _prepare_context(
        precommit_path=precommit_manifest,
        salt_path=salt,
        raw_archive_dir=raw_archive_dir,
        state_dir=state_dir,
        output_path=output,
        release_sha=release_sha,
        expected_candidate_count=expected_candidate_count,
        require_clean_worktree=require_clean_worktree,
        require_private_root=require_private_root,
        now=now,
    )
    pacer = NetworkRequestPacer(monotonic=monotonic, sleep=sleep)
    records: list[tuple[str, dict[str, Any] | None]] = []
    for index, candidate in enumerate(context.candidates):
        records.append(
            await _scan_candidate(context, candidate, client=client, pacer=pacer)
        )
        if progress and ((index + 1) % 200 == 0 or index + 1 == len(context.candidates)):
            processed, success, failed, indeterminate = _progress_counts(records)
            print(
                f"processed {processed}/{len(context.candidates)} "
                f"success {success} failed {failed} indeterminate {indeterminate}"
            )
    payload = _compile_output(context, records)
    _write_atomic_json(context.output_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precommit-manifest", type=Path, required=True)
    parser.add_argument("--salt", type=Path, required=True)
    parser.add_argument("--raw-archive-dir", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--acknowledge-network-collection", action="store_true")
    return parser


async def _run_live(args: argparse.Namespace) -> dict[str, Any]:
    if not args.acknowledge_network_collection:
        raise RuntimeError("network collection acknowledgement is required")
    from app.core.config import Settings
    from app.opendota.client import OpenDotaClient

    settings = Settings.from_env()
    if not settings.opendota_api_key:
        raise RuntimeError("OPENDOTA_API_KEY is not configured")
    async with OpenDotaClient(settings) as client:
        return await run_scan(
            precommit_manifest=args.precommit_manifest,
            salt=args.salt,
            raw_archive_dir=args.raw_archive_dir,
            state_dir=args.state_dir,
            output=args.output,
            release_sha=args.release_sha,
            client=client,
            acknowledge_network_collection=True,
            require_clean_worktree=True,
            require_private_root=True,
            progress=True,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = asyncio.run(_run_live(args))
    except (OSError, RuntimeError, ValueError):
        print(json.dumps({"status": "error", "error_category": "validation"}))
        return 2
    print(
        json.dumps(
            {
                "status": "complete",
                "candidate_count": payload["candidate_count"],
                "success_count": payload["success_count"],
                "failure_count": payload["failure_count"],
                "indeterminate_count": payload["indeterminate_count"],
                "eligible_count": payload["eligible_count"],
                "ineligible_count": payload["ineligible_count"],
                "detail_requests": payload["detail_requests"],
                "parse_requests": payload["parse_requests"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
