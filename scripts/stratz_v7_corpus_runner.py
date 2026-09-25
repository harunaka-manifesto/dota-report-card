#!/usr/bin/env python3
"""Resumable, local-only STRATZ V7 history/parsed research acquisition.

The runner is deliberately separate from the production provider.  It reads
only ``STRATZ_API_TOKEN`` from an explicitly supplied dotenv file, uses the
frozen cohort without replacement, archives each physical response once, and
keeps all row-level material below ``.local/corpora/stratz/``.

Without ``--acknowledge-network-collection`` the command only validates the
freeze and existing local ledgers; it never opens a network transport.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.stratz.client import parse_rate_limit_headers  # noqa: E402
from app.stratz.models import STRATZ_ENUM_VOCABULARY  # noqa: E402
from app.stratz.queries import (  # noqa: E402
    GET_PARSED_ACQUISITION_BATCH,
    GET_PLAYER_HISTORY_PAGE,
    GraphQLOperation,
)
from report_card.player_analysis_v7.research.durability import (  # noqa: E402
    assert_durable_corpus_root,
)

from scripts.stratz_v7_acquisition_freeze import (  # noqa: E402
    EXPECTED_FRAME_COUNT,
    load_source_frame,
    pseudonymize_account,
)

DEFAULT_ENDPOINT = "https://api.stratz.com/graphql"
DEFAULT_FREEZE_DIR = ROOT / ".local/corpora/stratz/v7-acquisition-freeze-2026-09-01"
DEFAULT_OUTPUT_DIR = ROOT / ".local/corpora/stratz/v7-corpus-2026-09-02"
DEFAULT_SOURCE_FRAME = (
    ROOT / ".local/corpora/opendota/v61-session-drift-expansion/manifests/fixed-frame-manifest.json"
)

RUNNER_SCHEMA = "stratz-v7-corpus-runner-1.0.0"
NORMALIZED_HISTORY_SCHEMA = "stratz-v7-provider-native-history-1.0.0"
NORMALIZED_PARSED_SCHEMA = "stratz-v7-provider-native-parsed-1.0.0"
CANONICAL_HISTORY_SCHEMA = "stratz-v7-canonical-history-1.0.0"
CANONICAL_PARSED_SCHEMA = "stratz-v7-canonical-parsed-1.0.0"
ATLAS_SCHEMA = "stratz-v7-neutral-qa-atlas-1.0.0"

EXPECTED_SALT_SHA256 = "2d552949ff32480ab7089d979152423a5e8bffd57fe4f613b9c7db698bdee7e4"
EXPECTED_SPLIT_SHA256 = "ef24c63b1c2f56e4bb21b4947b0b43dedf0550bd3547ee818cc9346f4275d885"
EXPECTED_PLAN_SHA256 = "9a77fb59fc22e8ac9cad036e3c7854f2668f97a46ed155d6a0a2a86aebac8dd0"
EXPECTED_FRAME_SHA256 = "98a442c0f04f7db8b5d5c32a51acdc0ece47e9fbc490408a29dfb23219bffaa9"

ALLOWED_SPLITS = ("DISCOVERY", "CANDIDATE_TEST")
EXPECTED_SPLIT_COUNTS = {
    "DISCOVERY": 600,
    "CANDIDATE_TEST": 300,
    "CALIBRATION_RESERVED": 150,
    "SEALED_VALIDATION": 150,
}
EXPECTED_PARSED_COUNTS = {
    "DISCOVERY": 128,
    "CANDIDATE_TEST": 128,
    "CALIBRATION_RESERVED": 0,
    "SEALED_VALIDATION": 0,
}
LOCAL_RATE_LIMITS = {"second": 5, "minute": 100, "hour": 1_000, "day": 10_000}
PLANNED_DAILY_CAP = 9_000
HISTORY_PAGE_SIZE = 100
MAX_HISTORY_PAGES = 25
PARSED_BATCH_SIZE = 8
MAX_BACKOFF_SECONDS = 30.0
MAX_WAIT_SECONDS = 60.0
WINDOW_DAYS = 365
_SENSITIVE_HEADER_MARKERS = (
    "authorization",
    "cookie",
    "set-cookie",
    "api-key",
    "apikey",
    "secret",
    "token",
)
_SCHEMA_MARKERS = (
    "cannot query field",
    "unknown argument",
    "unknown type",
    "does not exist",
    "graphql validation",
    "validation failed",
)
_FORBIDDEN_TOKENS = (
    "rank",
    "mmr",
    "imp",
    "behavior",
    "chat",
    "playback",
    "rolebasic",
    "analysisoutcome",
    "predicted",
)
_FORBIDDEN_FIELD_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(token) for token in _FORBIDDEN_TOKENS) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
Sleep = Callable[[float], Awaitable[None]]


class RunnerError(RuntimeError):
    """A fail-closed setup or provider error."""


class AccountUnavailable(RunnerError):
    """A single account is private or unavailable; the fixed cohort continues."""


class PauseRun(RunnerError):
    """The run can resume after a bounded rate or daily reset."""

    def __init__(self, reason: str, *, resume_at: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.resume_at = resume_at


class StopRun(RunnerError):
    """A provider or schema condition requires a whole-run stop."""

    def __init__(self, reason: str, *, kind: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.kind = kind


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, payload.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    path.chmod(0o600)


def _write_once(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, body)
        os.fsync(descriptor)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        os.close(descriptor)
    path.chmod(0o600)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read local JSON artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise RunnerError(f"local JSON artifact must be an object: {path.name}")
    return value


def load_stratz_token(dotenv_path: Path) -> str:
    """Read only STRATZ_API_TOKEN; never mutate or print the environment."""

    try:
        values = dotenv_values(dotenv_path, interpolate=False)
    except OSError as exc:
        raise RunnerError("cannot read the supplied dotenv file") from exc
    token = values.get("STRATZ_API_TOKEN")
    if not isinstance(token, str) or not token.strip():
        raise RunnerError("STRATZ_API_TOKEN is missing from the supplied dotenv file")
    return token.strip()


def redact_bytes(value: bytes, secret: str | None) -> bytes:
    return value.replace(secret.encode("utf-8"), b"[REDACTED]") if secret else value


def redact_text(value: str, secret: str | None) -> str:
    return value.replace(secret, "[REDACTED]") if secret else value


def safe_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if not any(marker in name.casefold() for marker in _SENSITIVE_HEADER_MARKERS)
    }


def safe_rate_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.casefold() == "retry-after"
        or "rate-limit" in name.casefold()
        or "ratelimit" in name.casefold()
    }


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return max(0.0, parsed.timestamp() - time.time())


def _error_text(payload: Mapping[str, Any] | None, secret: str | None) -> str | None:
    if not isinstance(payload, Mapping) or not payload.get("errors"):
        return None
    errors = payload["errors"]
    if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes, bytearray)):
        errors = (errors,)
    messages: list[str] = []
    for error in errors:
        message = error.get("message", "unknown GraphQL error") if isinstance(error, Mapping) else error
        messages.append(redact_text(str(message), secret)[:500])
    return "; ".join(messages) or "unknown GraphQL error"


def _is_schema_error(reason: str | None) -> bool:
    lowered = (reason or "").casefold()
    return any(marker in lowered for marker in _SCHEMA_MARKERS)


def _rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RunnerError(f"{label} must be a positive integer")
    return value


def _optional_int(value: Any, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise StopRun(f"schema drift at {path}", kind="schema_drift")
    return value


def _optional_bool(value: Any, path: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise StopRun(f"schema drift at {path}", kind="schema_drift")
    return value


def _optional_str(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StopRun(f"schema drift at {path}", kind="schema_drift")
    return value


def _optional_sequence(value: Any, path: str) -> list[Any] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise StopRun(f"schema drift at {path}", kind="schema_drift")
    return list(value)


def _enum_failure(value: str | None, vocabulary: Sequence[str]) -> bool:
    return value is None or value not in vocabulary


def _assert_operation_safe(operation: GraphQLOperation) -> None:
    if _FORBIDDEN_FIELD_RE.search(operation.document):
        raise RunnerError(f"frozen operation contains a forbidden selection: {operation.name}")


def _contains_forbidden_field(value: Mapping[str, Any]) -> bool:
    return any(
        isinstance(key, str) and _FORBIDDEN_FIELD_RE.fullmatch(key) is not None
        for key in value
    )


def _assert_no_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        if _contains_forbidden_field(value):
            raise StopRun("forbidden provider field returned", kind="schema_drift")
        for child in value.values():
            _assert_no_forbidden_fields(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            _assert_no_forbidden_fields(child)


def _validate_frozen_operations(plan: Mapping[str, Any]) -> None:
    """Require the two acquisition documents to remain the frozen ones."""

    registry = plan.get("pack_registry_check")
    packs = registry.get("packs") if isinstance(registry, Mapping) else None
    if not isinstance(packs, Sequence) or isinstance(packs, (str, bytes, bytearray)):
        raise RunnerError("frozen corpus plan has no operation registry")
    expected = {
        GET_PLAYER_HISTORY_PAGE.name: GET_PLAYER_HISTORY_PAGE,
        GET_PARSED_ACQUISITION_BATCH.name: GET_PARSED_ACQUISITION_BATCH,
    }
    observed: dict[str, dict[str, Any]] = {}
    for pack in packs:
        if not isinstance(pack, Mapping):
            continue
        operation_name = pack.get("operation")
        if isinstance(operation_name, str) and operation_name in expected:
            observed[operation_name] = dict(pack)
    for name, operation in expected.items():
        entry = observed.get(name)
        if entry is None:
            raise RunnerError(f"frozen corpus plan omits {name}")
        if (
            entry.get("operation_sha256") != operation.document_sha256
            or entry.get("operation_version") != operation.version
        ):
            raise RunnerError(f"frozen operation changed: {name}")


def request_key(operation: GraphQLOperation, variables: Mapping[str, Any]) -> str:
    return digest(
        {
            "provider": "stratz",
            "operation": operation.name,
            "version": operation.version,
            "document_sha256": operation.document_sha256,
            "variables_sha256": digest(dict(variables)),
        }
    )


def _is_immutable_success_response(status: Any, error_kind: str | None) -> bool:
    return (
        isinstance(status, int)
        and not isinstance(status, bool)
        and 200 <= status < 400
        and error_kind is None
    )


def _is_immutable_success_row(row: Mapping[str, Any]) -> bool:
    return (
        row.get("immutable_success") is True
        and _is_immutable_success_response(row.get("http_status"), row.get("error_kind"))
        and not row.get("error")
        and isinstance(row.get("raw_metadata_path"), str)
        and isinstance(row.get("raw_body_path"), str)
        and isinstance(row.get("response_sha256"), str)
    )


class CohortTarget:
    __slots__ = ("pseudonym", "source_position", "split", "parsed_subset", "parsed_order", "account_id")

    def __init__(
        self,
        *,
        pseudonym: str,
        source_position: int,
        split: str,
        parsed_subset: bool,
        parsed_order: int | None,
        account_id: int,
    ) -> None:
        self.pseudonym = pseudonym
        self.source_position = source_position
        self.split = split
        self.parsed_subset = parsed_subset
        self.parsed_order = parsed_order
        self.account_id = account_id


class FrozenCohort:
    __slots__ = ("freeze_dir", "source_frame_path", "salt", "split_digest", "plan_digest", "frame_digest", "targets")

    def __init__(
        self,
        *,
        freeze_dir: Path,
        source_frame_path: Path,
        salt: bytes,
        split_digest: str,
        plan_digest: str,
        frame_digest: str,
        targets: tuple[CohortTarget, ...],
    ) -> None:
        self.freeze_dir = freeze_dir
        self.source_frame_path = source_frame_path
        self.salt = salt
        self.split_digest = split_digest
        self.plan_digest = plan_digest
        self.frame_digest = frame_digest
        self.targets = targets

    @property
    def parsed_targets(self) -> tuple[CohortTarget, ...]:
        return tuple(target for target in self.targets if target.parsed_subset)


def load_frozen_cohort(
    freeze_dir: Path = DEFAULT_FREEZE_DIR,
    *,
    source_frame_path: Path = DEFAULT_SOURCE_FRAME,
    strict: bool = True,
) -> FrozenCohort:
    salt_path = freeze_dir / "salt.bin"
    split_path = freeze_dir / "manifests/split-manifest.json"
    plan_path = freeze_dir / "manifests/corpus-plan.json"
    try:
        salt = salt_path.read_bytes()
    except OSError as exc:
        raise RunnerError("frozen salt is unavailable") from exc
    split_digest = sha256_file(split_path)
    plan_digest = sha256_file(plan_path)
    if strict and (split_digest != EXPECTED_SPLIT_SHA256 or plan_digest != EXPECTED_PLAN_SHA256):
        raise RunnerError("frozen manifest digest does not match the acquisition freeze")
    if len(salt) != 32:
        raise RunnerError("frozen salt must be exactly 32 bytes")
    salt_digest = hashlib.sha256(salt).hexdigest()
    if strict and salt_digest != EXPECTED_SALT_SHA256:
        raise RunnerError("frozen salt digest does not match the acquisition freeze")
    split = _read_json(split_path)
    plan = _read_json(plan_path)
    _validate_frozen_operations(plan)
    split_counts = split.get("split_counts")
    parsed_counts = split.get("parsed_subset_counts")
    if split_counts != EXPECTED_SPLIT_COUNTS or parsed_counts != EXPECTED_PARSED_COUNTS:
        raise RunnerError("frozen split counts changed")
    if plan.get("split_manifest_sha256") != split_digest:
        raise RunnerError("corpus plan is not bound to the split manifest")
    if plan.get("split_counts") != EXPECTED_SPLIT_COUNTS or plan.get("parsed_subset_counts") != EXPECTED_PARSED_COUNTS:
        raise RunnerError("corpus plan split counts changed")
    frame = load_source_frame(source_frame_path)
    if frame.frame_count != EXPECTED_FRAME_COUNT:
        raise RunnerError("source frame count changed")
    frame_digest = frame.digest
    if strict and frame_digest != EXPECTED_FRAME_SHA256:
        raise RunnerError("source frame digest does not match the acquisition freeze")
    positions = {record.source_position: record.account_id for record in frame.records}
    members = split.get("members")
    if not isinstance(members, list) or len(members) != sum(EXPECTED_SPLIT_COUNTS.values()):
        raise RunnerError("frozen split members are invalid")
    observed_counts: Counter[str] = Counter()
    observed_parsed: Counter[str] = Counter()
    targets: list[CohortTarget] = []
    seen_allowed: set[str] = set()
    for member in members:
        if not isinstance(member, Mapping):
            raise RunnerError("frozen split member is invalid")
        split_name = member.get("split")
        if not isinstance(split_name, str):
            raise RunnerError("frozen split member has no partition")
        observed_counts[split_name] += 1
        parsed_subset = member.get("parsed_subset") is True
        if parsed_subset:
            observed_parsed[split_name] += 1
        # Reserved/sealed rows are counted above but their row-level details are
        # intentionally not consumed by the runner.
        if split_name not in ALLOWED_SPLITS:
            continue
        pseudonym = member.get("pseudonym")
        source_position = member.get("source_position")
        parsed_order = member.get("parsed_subset_order")
        if not isinstance(pseudonym, str) or not isinstance(source_position, int):
            raise RunnerError("allowed frozen member is missing pseudonym/source position")
        if source_position not in positions:
            raise RunnerError("allowed frozen member is not in the source frame")
        if pseudonymize_account(positions[source_position], salt) != pseudonym:
            raise RunnerError("frozen pseudonym does not bind to source position")
        if pseudonym in seen_allowed:
            raise RunnerError("allowed split overlap detected")
        seen_allowed.add(pseudonym)
        if parsed_subset and (not isinstance(parsed_order, int) or parsed_order < 0):
            raise RunnerError("parsed subset order is invalid")
        targets.append(
            CohortTarget(
                pseudonym=pseudonym,
                source_position=source_position,
                split=split_name,
                parsed_subset=parsed_subset,
                parsed_order=parsed_order if isinstance(parsed_order, int) else None,
                account_id=positions[source_position],
            )
        )
    if dict(observed_counts) != EXPECTED_SPLIT_COUNTS or {
        split_name: observed_parsed.get(split_name, 0) for split_name in EXPECTED_PARSED_COUNTS
    } != EXPECTED_PARSED_COUNTS:
        raise RunnerError("frozen member counts do not match declarations")
    if len(targets) != 900 or len([target for target in targets if target.parsed_subset]) != 256:
        raise RunnerError("allowed acquisition cohort is not 900/256")
    return FrozenCohort(
        freeze_dir=freeze_dir,
        source_frame_path=source_frame_path,
        salt=salt,
        split_digest=split_digest,
        plan_digest=plan_digest,
        frame_digest=frame_digest,
        targets=tuple(targets),
    )


class RateController:
    """Conservative local windows plus lower live limits and reset signals."""

    def __init__(self, *, sleep: Sleep, attempt_times: Sequence[float] = ()) -> None:
        self._sleep = sleep
        self.times: deque[float] = deque(sorted(float(value) for value in attempt_times))
        self.limits = dict(LOCAL_RATE_LIMITS)
        self.observed: dict[str, int] = {}
        self.remaining: dict[str, int] = {}
        self.reset_at: dict[str, float] = {}

    def _purge(self, now: float) -> None:
        while self.times and now - self.times[0] >= 86_400:
            self.times.popleft()

    def _effective_limits(self) -> dict[str, int]:
        limits = dict(self.limits)
        default = self.observed.get("default")
        if default is not None:
            limits["second"] = min(limits["second"], default)
        for bucket in LOCAL_RATE_LIMITS:
            if bucket in self.observed:
                limits[bucket] = min(limits[bucket], self.observed[bucket])
        return limits

    def observe(self, headers: Mapping[str, str]) -> None:
        snapshot = parse_rate_limit_headers(headers)
        for bucket, limit in snapshot.limits.items():
            if limit <= 0:
                raise StopRun("provider reported an invalid rate limit", kind="rate_behavior_changed")
            previous = self.observed.get(bucket)
            if previous is not None and previous != limit:
                raise StopRun("provider rate behavior changed during acquisition", kind="rate_behavior_changed")
            self.observed[bucket] = limit
        self.remaining.update(snapshot.remaining)
        self.reset_at.update(snapshot.reset_at)

    def _reset_delay(self, now: float) -> float | None:
        delays = [value - now for value in self.reset_at.values() if value > now]
        return min(delays) if delays else None

    async def before_attempt(self, planned_attempts: int) -> None:
        now = time.time()
        if planned_attempts >= PLANNED_DAILY_CAP:
            tomorrow = datetime.now(UTC).date() + timedelta(days=1)
            raise PauseRun(
                "planned daily cap reached (retries included)",
                resume_at=datetime.combine(tomorrow, datetime.min.time(), tzinfo=UTC).isoformat(),
            )
        self._purge(now)
        delay = self._reset_delay(now) if any(value <= 0 for value in self.remaining.values()) else 0.0
        windows = {"second": 1.0, "minute": 60.0, "hour": 3_600.0, "day": 86_400.0}
        for bucket, limit in self._effective_limits().items():
            active = [stamp for stamp in self.times if now - stamp < windows[bucket]]
            if len(active) >= limit:
                candidate = active[0] + windows[bucket] - now
                delay = max(delay or 0.0, candidate)
        if delay and delay > MAX_WAIT_SECONDS:
            raise PauseRun(
                "rate-window reset exceeds bounded wait; resume from checkpoint",
                resume_at=datetime.fromtimestamp(now + delay, UTC).isoformat(),
            )
        if delay and delay > 0:
            await self._sleep(delay)
        self.times.append(time.time())


def _profile_summary(player: Mapping[str, Any]) -> dict[str, Any]:
    if "steamAccount" not in player:
        raise StopRun("schema drift at data.player.steamAccount", kind="schema_drift")
    account = player.get("steamAccount")
    if account is None:
        return {
            "available": False,
            "is_anonymous": None,
            "is_public": False,
        }
    if not isinstance(account, Mapping):
        raise StopRun("schema drift at data.player.steamAccount", kind="schema_drift")
    if "isAnonymous" not in account or "isStratzPublic" not in account:
        raise StopRun("schema drift in STRATZ profile privacy fields", kind="schema_drift")
    anonymous = _optional_bool(account.get("isAnonymous"), "steamAccount.isAnonymous")
    public = _optional_bool(account.get("isStratzPublic"), "steamAccount.isStratzPublic")
    return {
        "available": True,
        "is_anonymous": anonymous,
        "is_public": public,
    }


def _native_match(
    match: Mapping[str, Any],
    *,
    account_id: int,
    path: str,
    required_match_fields: set[str] | None = None,
    required_player_fields: set[str] | None = None,
) -> dict[str, Any]:
    required_match_fields = required_match_fields or {
        "id",
        "didRadiantWin",
        "durationSeconds",
        "startDateTime",
        "endDateTime",
        "lobbyType",
        "gameMode",
        "gameVersionId",
        "parsedDateTime",
    }
    missing_match = required_match_fields.difference(match)
    if missing_match:
        raise StopRun(f"schema drift at {path}: missing {sorted(missing_match)}", kind="schema_drift")
    match_id = _positive_int(match.get("id"), f"{path}.id")
    players = _rows(match.get("players"))
    if not players:
        raise StopRun(f"schema drift at {path}.players", kind="schema_drift")
    selected = [row for row in players if row.get("steamAccountId") == account_id]
    if len(selected) != 1:
        raise StopRun(f"requested player row missing at {path}.players", kind="schema_drift")
    player = selected[0]
    allowed_player = {
        "steamAccountId",
        "playerSlot",
        "isRadiant",
        "isVictory",
        "heroId",
        "variant",
        "kills",
        "deaths",
        "assists",
        "leaverStatus",
        "partyId",
        "lane",
        "position",
        "role",
    }
    missing_player = (required_player_fields or allowed_player).difference(player)
    if missing_player:
        raise StopRun(f"schema drift at {path}.players: missing {sorted(missing_player)}", kind="schema_drift")
    if _contains_forbidden_field(match):
        raise StopRun("forbidden provider field returned", kind="schema_drift")
    if _contains_forbidden_field(player):
        raise StopRun("forbidden provider field returned", kind="schema_drift")
    native = {
        "match_id": match_id,
        "did_radiant_win": _optional_bool(match.get("didRadiantWin"), f"{path}.didRadiantWin"),
        "duration_seconds": _optional_int(match.get("durationSeconds"), f"{path}.durationSeconds"),
        "started_at": _optional_int(match.get("startDateTime"), f"{path}.startDateTime"),
        "ended_at": _optional_int(match.get("endDateTime"), f"{path}.endDateTime"),
        "lobby_type_native": _optional_str(match.get("lobbyType"), f"{path}.lobbyType"),
        "game_mode_native": _optional_str(match.get("gameMode"), f"{path}.gameMode"),
        "game_version_id": _optional_int(match.get("gameVersionId"), f"{path}.gameVersionId"),
        "parsed_at": _optional_int(match.get("parsedDateTime"), f"{path}.parsedDateTime"),
        "radiant_kills": _optional_sequence(match.get("radiantKills"), f"{path}.radiantKills"),
        "dire_kills": _optional_sequence(match.get("direKills"), f"{path}.direKills"),
        "radiant_networth_leads": _optional_sequence(
            match.get("radiantNetworthLeads"), f"{path}.radiantNetworthLeads"
        ),
        "bottom_lane_outcome_native": _optional_str(match.get("bottomLaneOutcome"), f"{path}.bottomLaneOutcome"),
        "mid_lane_outcome_native": _optional_str(match.get("midLaneOutcome"), f"{path}.midLaneOutcome"),
        "top_lane_outcome_native": _optional_str(match.get("topLaneOutcome"), f"{path}.topLaneOutcome"),
        "player": {
            "player_slot": _optional_int(player.get("playerSlot"), f"{path}.players.playerSlot"),
            "is_radiant": _optional_bool(player.get("isRadiant"), f"{path}.players.isRadiant"),
            "is_victory": _optional_bool(player.get("isVictory"), f"{path}.players.isVictory"),
            "hero_id": _optional_int(player.get("heroId"), f"{path}.players.heroId"),
            "variant": _optional_int(player.get("variant"), f"{path}.players.variant"),
            "kills": _optional_int(player.get("kills"), f"{path}.players.kills"),
            "deaths": _optional_int(player.get("deaths"), f"{path}.players.deaths"),
            "assists": _optional_int(player.get("assists"), f"{path}.players.assists"),
            "leaver_status_native": _optional_str(player.get("leaverStatus"), f"{path}.players.leaverStatus"),
            "party_id": _optional_int(player.get("partyId"), f"{path}.players.partyId"),
            "lane_native": _optional_str(player.get("lane"), f"{path}.players.lane"),
            "position_native": _optional_str(player.get("position"), f"{path}.players.position"),
            "role_native": _optional_str(player.get("role"), f"{path}.players.role"),
        },
    }
    return native


def normalize_history_page(
    payload: Mapping[str, Any],
    *,
    account_id: int,
    pseudonym: str,
    split: str,
    source_position: int,
    window_start: int,
    window_end: int,
    operation: GraphQLOperation = GET_PLAYER_HISTORY_PAGE,
) -> dict[str, Any]:
    _assert_no_forbidden_fields(payload)
    data = payload.get("data")
    player = data.get("player") if isinstance(data, Mapping) else None
    if not isinstance(player, Mapping):
        raise AccountUnavailable("history profile is private or unavailable")
    profile = _profile_summary(player)
    matches_value = player.get("matches")
    if not isinstance(matches_value, Sequence) or isinstance(matches_value, (str, bytes, bytearray)):
        raise StopRun("schema drift at data.player.matches", kind="schema_drift")
    rows = [
        _native_match(match, account_id=account_id, path=f"data.player.matches[{index}]")
        for index, match in enumerate(matches_value)
        if isinstance(match, Mapping)
    ]
    if len(rows) != len(matches_value):
        raise StopRun("schema drift in history match rows", kind="schema_drift")
    return {
        "schema_version": NORMALIZED_HISTORY_SCHEMA,
        "provider": "stratz",
        "account_pseudonym": pseudonym,
        "source_position": source_position,
        "split": split,
        "operation": operation.name,
        "operation_version": operation.version,
        "operation_document_sha256": operation.document_sha256,
        "profile": profile,
        "window": {"start_timestamp": window_start, "end_timestamp": window_end, "days": WINDOW_DAYS},
        "rows": rows,
    }


def _parsed_stats(stats: Any, path: str) -> dict[str, Any]:
    if not isinstance(stats, Mapping):
        raise StopRun(f"parsed stats missing at {path}", kind="response_shape")
    if _contains_forbidden_field(stats):
        raise StopRun("forbidden parsed provider field returned", kind="schema_drift")
    result: dict[str, Any] = {}
    for source, target in (("killEvents", "kill_events"), ("assistEvents", "assist_events"), ("itemPurchases", "item_purchases")):
        if source not in stats:
            raise StopRun(f"schema drift at {path}.{source}", kind="schema_drift")
        value = stats.get(source)
        if value is not None and not isinstance(value, Sequence):
            raise StopRun(f"schema drift at {path}.{source}", kind="schema_drift")
        events: list[dict[str, Any]] | None = None
        if value is not None:
            events = []
            for index, event in enumerate(value):
                if not isinstance(event, Mapping):
                    raise StopRun(f"schema drift at {path}.{source}[{index}]", kind="schema_drift")
                item: dict[str, Any] = {"time": _optional_int(event.get("time"), f"{path}.{source}[{index}].time")}
                if source == "itemPurchases":
                    item["item_id"] = _optional_int(event.get("itemId"), f"{path}.{source}[{index}].itemId")
                events.append(item)
        result[target] = events
    return result


def normalize_parsed_batch(
    payload: Mapping[str, Any],
    *,
    account_id: int,
    requested_ids: Sequence[int],
    pseudonym: str,
    split: str,
    source_position: int,
    operation: GraphQLOperation = GET_PARSED_ACQUISITION_BATCH,
) -> dict[str, Any]:
    _assert_no_forbidden_fields(payload)
    data = payload.get("data")
    player = data.get("player") if isinstance(data, Mapping) else None
    matches_value = player.get("matches") if isinstance(player, Mapping) else None
    matches = _rows(matches_value)
    requested = tuple(dict.fromkeys(int(value) for value in requested_ids))
    returned = [match.get("id") for match in matches]
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in returned):
        raise RunnerError("parsed response returned an invalid match ID")
    if len(matches) != len(requested) or set(returned) != set(requested) or len(set(returned)) != len(returned):
        raise RunnerError("parsed response did not return exactly the requested match IDs")
    rows: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        if match.get("id") not in requested:
            raise RunnerError("parsed response returned an unexpected match ID")
        native = _native_match(
            match,
            account_id=account_id,
            path=f"data.player.matches[{index}]",
            required_match_fields={
                "id",
                "durationSeconds",
                "startDateTime",
                "endDateTime",
                "didRadiantWin",
                "gameVersionId",
                "parsedDateTime",
                "radiantKills",
                "direKills",
                "radiantNetworthLeads",
                "bottomLaneOutcome",
                "midLaneOutcome",
                "topLaneOutcome",
            },
            required_player_fields={
                "steamAccountId",
                "isRadiant",
                "isVictory",
                "heroId",
                "position",
                "role",
                "lane",
                "stats",
            },
        )
        raw_players = _rows(match.get("players"))
        if len(raw_players) != 1 or raw_players[0].get("stats") is None:
            raise RunnerError("parsed response has a missing selected player or stats")
        native["player"]["stats"] = _parsed_stats(raw_players[0]["stats"], f"data.player.matches[{index}].players.stats")
        rows.append(native)
    return {
        "schema_version": NORMALIZED_PARSED_SCHEMA,
        "provider": "stratz",
        "account_pseudonym": pseudonym,
        "source_position": source_position,
        "split": split,
        "operation": operation.name,
        "operation_version": operation.version,
        "operation_document_sha256": operation.document_sha256,
        "requested_batch_size": len(requested),
        "rows": rows,
    }


def _row_completeness(row: Mapping[str, Any]) -> tuple[int, str]:
    values: list[Any] = []
    for key, value in row.items():
        if key == "player" and isinstance(value, Mapping):
            values.extend(value.values())
        elif key != "match_id":
            values.append(value)
    return sum(value is not None for value in values), digest(row)


def dedupe_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    chosen: dict[int, Mapping[str, Any]] = {}
    duplicates = 0
    for row in rows:
        match_id = row.get("match_id")
        if not isinstance(match_id, int):
            raise RunnerError("canonical row has no positive match ID")
        previous = chosen.get(match_id)
        if previous is None:
            chosen[match_id] = row
            continue
        duplicates += 1
        if _row_completeness(row) > _row_completeness(previous):
            chosen[match_id] = row
    ordered = sorted(
        (dict(row) for row in chosen.values()),
        key=lambda row: (row.get("started_at") is None, -(row.get("started_at") or 0), row["match_id"]),
    )
    return ordered, duplicates


def _canonical_history_row(row: Mapping[str, Any], *, window_start: int, window_end: int) -> dict[str, Any]:
    player = row["player"]
    role = player.get("role_native")
    position = player.get("position_native")
    lane = player.get("lane_native")
    leaver = player.get("leaver_status_native")
    enum_failure = (
        _enum_failure(role, STRATZ_ENUM_VOCABULARY["role"])
        or _enum_failure(position, STRATZ_ENUM_VOCABULARY["position"])
        or _enum_failure(lane, STRATZ_ENUM_VOCABULARY["lane"])
        or _enum_failure(leaver, STRATZ_ENUM_VOCABULARY["leaver_status"])
    )
    started = row.get("started_at")
    in_window = isinstance(started, int) and window_start <= started <= window_end
    return {
        "match_id": row["match_id"],
        "started_at": started,
        "ended_at": row.get("ended_at"),
        "duration_seconds": row.get("duration_seconds"),
        "hero_id": player.get("hero_id"),
        "did_radiant_win": row.get("did_radiant_win"),
        "is_radiant": player.get("is_radiant"),
        "is_victory": player.get("is_victory"),
        "kills": player.get("kills"),
        "deaths": player.get("deaths"),
        "assists": player.get("assists"),
        "game_version_id": row.get("game_version_id"),
        "position_native": position,
        "role_native": role,
        "lane_native": lane,
        "game_mode_native": row.get("game_mode_native"),
        "lobby_type_native": row.get("lobby_type_native"),
        "leaver_status_native": leaver,
        "parsed_at": row.get("parsed_at"),
        "is_parsed": row.get("parsed_at") is not None,
        "in_window": in_window,
        "enum_failure": enum_failure,
        "structural_eligible": False if enum_failure else None,
    }


def canonicalize_history(
    pages: Sequence[Mapping[str, Any]],
    *,
    pseudonym: str,
    source_position: int,
    split: str,
    window_start: int,
    window_end: int,
    completeness: str,
) -> dict[str, Any]:
    profile = pages[0].get("profile", {"available": False, "is_anonymous": None, "is_public": False}) if pages else {"available": False, "is_anonymous": None, "is_public": False}
    native_rows = [row for page in pages for row in page.get("rows", ()) if isinstance(row, Mapping)]
    unique, duplicates = dedupe_rows(native_rows)
    rows = [
        _canonical_history_row(row, window_start=window_start, window_end=window_end)
        for row in unique
        if row.get("started_at") is None or window_start <= row["started_at"] <= window_end
    ]
    return {
        "schema_version": CANONICAL_HISTORY_SCHEMA,
        "provider": "stratz",
        "account_pseudonym": pseudonym,
        "source_position": source_position,
        "split": split,
        "window": {"start_timestamp": window_start, "end_timestamp": window_end, "days": WINDOW_DAYS},
        "profile": profile,
        "completeness": completeness,
        "raw_row_count": len(native_rows),
        "unique_match_count": len(rows),
        "duplicate_match_count": duplicates,
        "rows": rows,
    }


def canonicalize_parsed(
    batches: Sequence[Mapping[str, Any]],
    *,
    pseudonym: str,
    source_position: int,
    split: str,
) -> dict[str, Any]:
    native_rows = [row for batch in batches for row in batch.get("rows", ()) if isinstance(row, Mapping)]
    unique, duplicates = dedupe_rows(native_rows)
    rows: list[dict[str, Any]] = []
    for row in unique:
        player = row["player"]
        rows.append(
            {
                "match_id": row["match_id"],
                "started_at": row.get("started_at"),
                "ended_at": row.get("ended_at"),
                "duration_seconds": row.get("duration_seconds"),
                "did_radiant_win": row.get("did_radiant_win"),
                "game_version_id": row.get("game_version_id"),
                "parsed_at": row.get("parsed_at"),
                "radiant_kills": row.get("radiant_kills"),
                "dire_kills": row.get("dire_kills"),
                "radiant_networth_leads": row.get("radiant_networth_leads"),
                "bottom_lane_outcome_native": row.get("bottom_lane_outcome_native"),
                "mid_lane_outcome_native": row.get("mid_lane_outcome_native"),
                "top_lane_outcome_native": row.get("top_lane_outcome_native"),
                "is_radiant": player.get("is_radiant"),
                "is_victory": player.get("is_victory"),
                "hero_id": player.get("hero_id"),
                "position_native": player.get("position_native"),
                "role_native": player.get("role_native"),
                "lane_native": player.get("lane_native"),
                "stats": player.get("stats"),
            }
        )
    return {
        "schema_version": CANONICAL_PARSED_SCHEMA,
        "provider": "stratz",
        "account_pseudonym": pseudonym,
        "source_position": source_position,
        "split": split,
        "raw_row_count": len(native_rows),
        "unique_match_count": len(rows),
        "duplicate_match_count": duplicates,
        "rows": rows,
    }


def _coverage(fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for field in fields:
        present = sum(row.get(field) is not None for row in rows)
        result[field] = {"present": present, "missing": len(rows) - present, "total": len(rows)}
    return result


def _sequence_coverage(fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for field in fields:
        values = [row.get(field) for row in rows]
        present = sum(value is not None for value in values)
        nonempty = sum(isinstance(value, list) and bool(value) for value in values)
        elements = sum(len(value) for value in values if isinstance(value, list))
        result[field] = {
            "present": present,
            "missing": len(rows) - present,
            "nonempty": nonempty,
            "elements": elements,
            "total": len(rows),
        }
    return result


def _distribution(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = row.get(field)
        counts["__MISSING__" if value is None else str(value)] += 1
    return dict(sorted(counts.items()))


def _duration(rows: Sequence[Mapping[str, Any]]) -> dict[str, int | float | None]:
    values = [value for value in (row.get("duration_seconds") for row in rows) if isinstance(value, int)]
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": round(sum(values) / len(values), 3) if values else None,
    }


def build_qa_atlas(cohort: FrozenCohort, output_dir: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    history_dir = output_dir / "canonical/history"
    parsed_dir = output_dir / "canonical/parsed"
    history_docs = [_read_json(path) for path in sorted(history_dir.glob("*.json"))]
    parsed_docs = [_read_json(path) for path in sorted(parsed_dir.glob("*.json"))]
    history_rows = [row for doc in history_docs for row in doc.get("rows", ()) if isinstance(row, Mapping)]
    parsed_rows = [row for doc in parsed_docs for row in doc.get("rows", ()) if isinstance(row, Mapping)]
    account_states = state.get("history", {}).get("accounts", {}) if isinstance(state.get("history"), Mapping) else {}
    parsed_states = state.get("parsed", {}).get("accounts", {}) if isinstance(state.get("parsed"), Mapping) else {}
    split_summary: dict[str, Any] = {}
    for split in ALLOWED_SPLITS:
        targets = [target for target in cohort.targets if target.split == split]
        ptargets = [target for target in targets if target.parsed_subset]
        states = [account_states.get(target.pseudonym, {"status": "pending"}) for target in targets]
        p_states = [parsed_states.get(target.pseudonym, {"status": "pending"}) for target in ptargets]
        profiles: list[Mapping[str, Any]] = []
        for account_state in states:
            if not isinstance(account_state, Mapping):
                continue
            profile = account_state.get("profile")
            if isinstance(profile, Mapping):
                profiles.append(profile)
        split_rows = [
            row
            for doc in history_docs
            if doc.get("split") == split
            for row in doc.get("rows", ())
            if isinstance(row, Mapping)
        ]
        public_profiles = [profile for profile in profiles if profile.get("is_public") is True]
        product_profiles = [profile for profile in profiles if profile.get("is_anonymous") is False]
        split_summary[split] = {
            "predeclared_history_players": len(targets),
            "history_attempted_players": sum(state.get("status") != "pending" for state in states),
            "history_complete_players": sum(state.get("status") == "complete" for state in states),
            "history_truncated_players": sum(state.get("status") == "truncated" for state in states),
            "history_private_or_unavailable_players": sum(state.get("status") in {"private", "unavailable"} for state in states),
            "history_failed_players": sum(state.get("status") == "failed" for state in states),
            "history_public_profile_players": len(public_profiles),
            "history_product_eligible_players": len(product_profiles),
            "history_anonymous_profile_players": sum(profile.get("is_anonymous") is True for profile in profiles),
            "history_privacy_unknown_players": sum(profile.get("is_anonymous") is None for profile in profiles) + sum(
                1 for account_state in states
                if not isinstance(account_state, Mapping) or not isinstance(account_state.get("profile"), Mapping)
            ),
            "history_rows": len(split_rows),
            "history_parsed_opportunity_rows": sum(row.get("parsed_at") is not None for row in split_rows),
            "history_enum_failure_rows": sum(row.get("enum_failure") is True for row in split_rows),
            "history_structural_observable_rows": sum(row.get("enum_failure") is False for row in split_rows),
            "predeclared_parsed_players": len(ptargets),
            "parsed_attempted_players": sum(bool(state.get("batches")) for state in p_states if isinstance(state, Mapping)),
            "parsed_complete_players": sum(state.get("status") == "complete" for state in p_states),
            "parsed_skipped_anonymous": sum(state.get("status") == "skipped_anonymous" for state in p_states),
            "parsed_no_valid_opportunities": sum(state.get("status") == "no_valid_opportunities" for state in p_states),
        }
    parsed_available = sum(row.get("parsed_at") is not None for row in history_rows)
    parsed_missing = len(history_rows) - parsed_available
    contexts: dict[str, dict[str, int]] = {}
    for row in history_rows:
        context = "|".join(
            str(row.get(field) if row.get(field) is not None else "__MISSING__")
            for field in ("game_mode_native", "lobby_type_native", "game_version_id", "role_native", "position_native", "lane_native")
        )
        cell = contexts.setdefault(context, {"rows": 0, "parsed_available": 0, "parsed_missing": 0})
        cell["rows"] += 1
        if row.get("parsed_at") is None:
            cell["parsed_missing"] += 1
        else:
            cell["parsed_available"] += 1
    event_coverage: dict[str, dict[str, int]] = {}
    for source, field in (("kill_events", "kill_events"), ("assist_events", "assist_events"), ("item_purchases", "item_purchases")):
        values = [row.get("stats", {}).get(field) if isinstance(row.get("stats"), Mapping) else None for row in parsed_rows]
        present = sum(value is not None for value in values)
        event_coverage[source] = {
            "rows": len(values),
            "present": present,
            "missing": len(values) - present,
            "empty": sum(value == [] for value in values),
            "events": sum(len(value) for value in values if isinstance(value, list)),
        }
    atlas = {
        "schema_version": ATLAS_SCHEMA,
        "provider": "stratz",
        "freeze": {
            "split_manifest_sha256": cohort.split_digest,
            "corpus_plan_sha256": cohort.plan_digest,
            "source_frame_sha256": cohort.frame_digest,
        },
        "status": state.get("status", "UNKNOWN"),
        "network_calls": {"stratz": int(state.get("physical_attempts", 0)), "opendota": 0},
        "players": split_summary,
        "denominators": {
            "source_frame_accounts": EXPECTED_FRAME_COUNT,
            "preselection_accounts": sum(EXPECTED_SPLIT_COUNTS.values()),
            "allowed_history_accounts": len(cohort.targets),
            "allowed_parsed_subset_accounts": len(cohort.parsed_targets),
            "product_public_eligible_accounts": sum(
                summary["history_product_eligible_players"] for summary in split_summary.values()
            ),
            "history_rows": len(history_rows),
            "information_opportunity_rows": parsed_available,
            "structural_observable_rows": sum(row.get("enum_failure") is False for row in history_rows),
            "structural_eligibility": "UNKNOWN_UNTIL_NATIVE_MODE_LOBBY_LEAVER_SEMANTICS_VERIFIED",
        },
        "history": {
            "players_with_canonical_rows": len(history_docs),
            "rows": len(history_rows),
            "rows_with_known_window": sum(row.get("in_window") is True for row in history_rows),
            "rows_with_unknown_window": sum(row.get("started_at") is None for row in history_rows),
            "parsed_available_rows": parsed_available,
            "parsed_missing_rows": parsed_missing,
            "duration_seconds": _duration(history_rows),
            "game_version_id": _distribution(history_rows, "game_version_id"),
            "role_native": _distribution(history_rows, "role_native"),
            "position_native": _distribution(history_rows, "position_native"),
            "lane_native": _distribution(history_rows, "lane_native"),
            "game_mode_native": _distribution(history_rows, "game_mode_native"),
            "lobby_type_native": _distribution(history_rows, "lobby_type_native"),
            "leaver_status_native": _distribution(history_rows, "leaver_status_native"),
            "structural_observation": {
                "rows_with_all_observed_enums": sum(
                    row.get("enum_failure") is False for row in history_rows
                ),
                "rows_with_enum_failure": sum(row.get("enum_failure") is True for row in history_rows),
                "eligibility_status": "UNKNOWN_UNTIL_NATIVE_MODE_LOBBY_LEAVER_SEMANTICS_VERIFIED",
            },
            "field_coverage": _coverage(
                ("match_id", "started_at", "ended_at", "duration_seconds", "hero_id", "game_version_id", "role_native", "position_native", "lane_native", "game_mode_native", "lobby_type_native", "leaver_status_native", "parsed_at"),
                history_rows,
            ),
        },
        "parsed": {
            "players_with_canonical_rows": len(parsed_docs),
            "rows": len(parsed_rows),
            "duration_seconds": _duration(parsed_rows),
            "field_coverage": _coverage(
                ("match_id", "started_at", "ended_at", "duration_seconds", "game_version_id", "parsed_at", "hero_id", "role_native", "position_native", "lane_native", "stats"),
                parsed_rows,
            ),
            "trajectory_coverage": _sequence_coverage(
                ("radiant_kills", "dire_kills", "radiant_networth_leads"),
                parsed_rows,
            ),
            "event_coverage": event_coverage,
        },
        "parsed_missingness_by_observable_context": contexts,
        "unknown_semantics_excluded": True,
        "identities_included": False,
    }
    _assert_aggregate_only(atlas)
    return atlas


def _assert_aggregate_only(value: Any, *, path: str = "atlas") -> None:
    forbidden_keys = {"account_id", "steam_account_id", "pseudonym", "source_position", "match_ids", "raw_response"}
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in forbidden_keys:
                raise RunnerError(f"aggregate atlas contains an identity field at {path}.{key}")
            _assert_aggregate_only(child, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_aggregate_only(child, path=f"{path}[{index}]")


class CorpusRunner:
    """Sequential resumable runner for the fixed two-wave acquisition."""

    def __init__(
        self,
        cohort: FrozenCohort,
        *,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        token: str | None = None,
        endpoint: str = DEFAULT_ENDPOINT,
        network: bool = False,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        max_history_pages: int = MAX_HISTORY_PAGES,
        http_client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        _assert_operation_safe(GET_PLAYER_HISTORY_PAGE)
        _assert_operation_safe(GET_PARSED_ACQUISITION_BATCH)
        if network and not token:
            raise RunnerError("network collection requires STRATZ_API_TOKEN")
        if max_history_pages < 1:
            raise RunnerError("history page ceiling must be positive")
        self.cohort = cohort
        # The state, ledger and raw directories all hang off this one
        # path, so guarding it here covers the collector output root and
        # the resume/checkpoint root together. It follows symlinks: the
        # 2026-09-07 loss came through a durable-looking link.
        self.output_dir = assert_durable_corpus_root(
            output_dir, purpose="collector output and resume/checkpoint root"
        )
        self.token = token
        self.endpoint = endpoint
        self.network = network
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, int(max_retries))
        self.max_history_pages = int(max_history_pages)
        self._http = http_client
        self._owns_http = http_client is None
        self._sleep = sleep
        self.state_path = output_dir / "manifests/state.json"
        self.ledger_path = output_dir / "ledgers/request-ledger.jsonl"
        self.raw_dir = output_dir / "raw"
        self.normalized_history_dir = output_dir / "normalized/history"
        self.normalized_parsed_dir = output_dir / "normalized/parsed"
        self.canonical_history_dir = output_dir / "canonical/history"
        self.canonical_parsed_dir = output_dir / "canonical/parsed"
        for directory in (
            self.raw_dir,
            self.normalized_history_dir,
            self.normalized_parsed_dir,
            self.canonical_history_dir,
            self.canonical_parsed_dir,
            self.ledger_path.parent,
            self.state_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        self.ledger_rows = self._load_ledger()
        self.state = self._load_state()
        attempt_times = [float(row.get("timestamp_epoch", 0)) for row in self.ledger_rows if row.get("timestamp_epoch")]
        self.rate = RateController(sleep=sleep, attempt_times=attempt_times)
        for row in self.ledger_rows:
            safe_headers = row.get("safe_rate_headers")
            if not isinstance(safe_headers, Mapping):
                continue
            for bucket, limit in parse_rate_limit_headers(safe_headers).limits.items():
                previous = self.rate.observed.get(bucket)
                if previous is not None and previous != limit:
                    raise StopRun("provider rate behavior changed in resume ledger", kind="rate_behavior_changed")
                self.rate.observed[bucket] = limit
        saved_rates = self.state.get("rate_observed")
        if isinstance(saved_rates, Mapping):
            for bucket, limit in saved_rates.items():
                if not isinstance(bucket, str) or isinstance(limit, bool) or not isinstance(limit, int):
                    continue
                previous = self.rate.observed.get(bucket)
                if previous is not None and previous != limit:
                    raise StopRun("provider rate behavior changed in resume state", kind="rate_behavior_changed")
                self.rate.observed[bucket] = limit

    async def __aenter__(self) -> CorpusRunner:
        if self._http is None and self.network:
            self._http = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http is not None and self._owns_http:
            await self._http.aclose()
            self._http = None

    def _load_ledger(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise RunnerError("cannot read request ledger") from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RunnerError("request ledger contains invalid JSON") from exc
            if not isinstance(row, dict):
                raise RunnerError("request ledger row must be an object")
            rows.append(row)
        return rows

    def _load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            state = _read_json(self.state_path)
            if state.get("schema_version") != RUNNER_SCHEMA:
                raise RunnerError("unsupported corpus runner state schema")
            freeze = state.get("freeze")
            if (
                not isinstance(freeze, Mapping)
                or freeze.get("split_manifest_sha256") != self.cohort.split_digest
                or freeze.get("corpus_plan_sha256") != self.cohort.plan_digest
                or freeze.get("source_frame_sha256") != self.cohort.frame_digest
            ):
                raise RunnerError("resume state is bound to a different frozen cohort")
            window = state.get("window")
            if not isinstance(window, Mapping):
                raise RunnerError("resume state has no fixed history window")
            if (
                window.get("days") != WINDOW_DAYS
                or isinstance(window.get("start_timestamp"), bool)
                or not isinstance(window.get("start_timestamp"), int)
                or isinstance(window.get("end_timestamp"), bool)
                or not isinstance(window.get("end_timestamp"), int)
                or window["start_timestamp"] > window["end_timestamp"]
            ):
                raise RunnerError("resume state has an invalid 365-day history window")
            return state
        end = int(datetime.now(UTC).timestamp())
        state = {
            "schema_version": RUNNER_SCHEMA,
            "status": "PENDING",
            "phase": "HISTORY",
            "freeze": {
                "split_manifest_sha256": self.cohort.split_digest,
                "corpus_plan_sha256": self.cohort.plan_digest,
                "source_frame_sha256": self.cohort.frame_digest,
            },
            "window": {
                "start_timestamp": end - WINDOW_DAYS * 86_400,
                "end_timestamp": end,
                "days": WINDOW_DAYS,
            },
            "history": {"accounts": {}},
            "parsed": {"accounts": {}},
            "physical_attempts": len(self.ledger_rows),
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_observed": {},
            "stop_reason": None,
            "resume_at": None,
        }
        _write_json(self.state_path, state)
        return state

    def _save_state(self) -> None:
        self.state["physical_attempts"] = len(self.ledger_rows)
        _write_json(self.state_path, self.state)

    def _append_ledger(self, row: Mapping[str, Any]) -> None:
        payload = json.dumps(dict(row), sort_keys=True) + "\n"
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        self.ledger_rows.append(dict(row))
        self.ledger_path.chmod(0o600)

    def _success_index(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for row in self.ledger_rows:
            if _is_immutable_success_row(row):
                key = row.get("request_key")
                if isinstance(key, str):
                    result[key] = row
        return result

    def _archive_response(
        self,
        *,
        physical_ordinal: int,
        operation: GraphQLOperation,
        variables_hash: str,
        content: bytes,
        response: httpx.Response,
        latency: float,
        attempt: int,
        retrying: bool,
        retry_after: float | None,
        error_kind: str | None,
    ) -> tuple[Path, Path, str, str]:
        body = redact_bytes(content, self.token)
        response_sha = hashlib.sha256(content).hexdigest()
        archived_sha = hashlib.sha256(body).hexdigest()
        stem = f"{physical_ordinal:06d}-{operation.name}"
        body_path = self.raw_dir / f"{stem}.body"
        meta_path = self.raw_dir / f"{stem}.json"
        _write_once(body_path, body)
        metadata = {
            "schema_version": "stratz-v7-raw-response-1.0.0",
            "provider": "stratz",
            "physical_ordinal": physical_ordinal,
            "operation": operation.name,
            "operation_version": operation.version,
            "operation_document_sha256": operation.document_sha256,
            "variables_sha256": variables_hash,
            "captured_at": datetime.now(UTC).isoformat(),
            "http_status": response.status_code,
            "response_sha256": response_sha,
            "archived_body_sha256": archived_sha,
            "response_bytes": len(content),
            "latency_seconds": round(latency, 6),
            "attempt": attempt,
            "retrying": retrying,
            "retry_after_seconds": retry_after,
            "cache_hit": False,
            "cache_miss": True,
            "error_kind": error_kind,
            "safe_headers": safe_response_headers(response.headers),
            "safe_rate_headers": safe_rate_headers(response.headers),
            "body_path": body_path.relative_to(self.output_dir).as_posix(),
        }
        _write_once(meta_path, canonical_bytes(metadata) + b"\n")
        return body_path, meta_path, response_sha, archived_sha

    def _load_archived_payload(self, row: Mapping[str, Any]) -> Mapping[str, Any]:
        meta_path = self.output_dir / str(row.get("raw_metadata_path", ""))
        metadata = _read_json(meta_path)
        body_path = self.output_dir / str(metadata.get("body_path", ""))
        try:
            body = body_path.read_bytes()
        except OSError as exc:
            raise RunnerError("immutable raw response body is missing") from exc
        if hashlib.sha256(body).hexdigest() != metadata.get("archived_body_sha256"):
            raise RunnerError("immutable raw response body hash mismatch")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunnerError("immutable raw response is not JSON") from exc
        if not isinstance(payload, Mapping):
            raise RunnerError("immutable raw response is not an object")
        return payload

    async def request(
        self,
        operation: GraphQLOperation,
        variables: Mapping[str, Any],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[Mapping[str, Any], dict[str, Any]]:
        key = request_key(operation, variables)
        variables_hash = digest(dict(variables))
        existing = self._success_index().get(key)
        if existing is not None:
            payload = self._load_archived_payload(existing)
            self.state["cache_hits"] = int(self.state.get("cache_hits", 0)) + 1
            return payload, {
                "request_key": key,
                "variables_sha256": variables_hash,
                "cache_hit": True,
                "cache_miss": False,
                "physical_attempts": 0,
                "raw_response_sha256": existing.get("response_sha256"),
            }
        if not self.network:
            raise RunnerError("network disabled; offline validation made zero provider calls")
        self.state["cache_misses"] = int(self.state.get("cache_misses", 0)) + 1
        attempts: list[dict[str, Any]] = []
        last_payload: Mapping[str, Any] | None = None
        last_reason: str | None = None
        for attempt in range(self.max_retries + 1):
            today = datetime.now(UTC).date()
            planned_today = sum(
                datetime.fromtimestamp(float(row["timestamp_epoch"]), UTC).date() == today
                for row in self.ledger_rows
                if row.get("timestamp_epoch")
            )
            await self.rate.before_attempt(planned_today)
            if self._http is None:
                self._http = httpx.AsyncClient(timeout=self.timeout_seconds)
            started = time.monotonic()
            ordinal = len(self.ledger_rows) + 1
            timestamp_epoch = time.time()
            status: int | None = None
            response_sha: str | None = None
            raw_metadata_path: str | None = None
            raw_body_path: str | None = None
            response_bytes = 0
            headers: Mapping[str, str] = {}
            retryable = False
            retry_after: float | None = None
            error_kind: str | None = None
            error: str | None = None
            rate_error: StopRun | None = None
            try:
                response = await self._http.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                        "User-Agent": "STRATZ_API",
                    },
                    json={
                        "operationName": operation.name,
                        "variables": dict(variables),
                        "query": operation.document,
                    },
                )
                latency = time.monotonic() - started
                status = response.status_code
                response_bytes = len(response.content)
                headers = safe_response_headers(response.headers)
                try:
                    parsed = response.json()
                except (TypeError, ValueError):
                    parsed = None
                last_payload = parsed if isinstance(parsed, Mapping) else None
                error = _error_text(last_payload, self.token)
                if status < 400 and isinstance(parsed, Mapping):
                    if error:
                        error_kind = "schema_drift" if _is_schema_error(error) else "graphql_error"
                    elif not isinstance(parsed.get("data"), Mapping):
                        error_kind = "missing_data"
                        error = "STRATZ response has no data"
                elif status >= 400:
                    error = error or f"HTTP {status}"
                    error_kind = "authentication_failure" if status in {401, 403} else "http_error"
                    retryable = status == 429 or status >= 500
                    retry_after = parse_retry_after(response.headers.get("Retry-After"))
                else:
                    error_kind = "invalid_json"
                    error = "STRATZ returned invalid JSON"
                if status in {401, 403}:
                    retryable = False
                body_path, metadata_path, response_sha, archived_sha = self._archive_response(
                    physical_ordinal=ordinal,
                    operation=operation,
                    variables_hash=variables_hash,
                    content=response.content,
                    response=response,
                    latency=latency,
                    attempt=attempt,
                    retrying=retryable and attempt < self.max_retries,
                    retry_after=retry_after,
                    error_kind=error_kind,
                )
                raw_body_path = body_path.relative_to(self.output_dir).as_posix()
                raw_metadata_path = metadata_path.relative_to(self.output_dir).as_posix()
                try:
                    self.rate.observe(response.headers)
                except StopRun as exc:
                    rate_error = exc
                self.state["rate_observed"] = dict(self.rate.observed)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                latency = time.monotonic() - started
                error_kind = "transport_error"
                error = type(exc).__name__
                retryable = True
            row = {
                "schema_version": "stratz-v7-request-ledger-1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "timestamp_epoch": timestamp_epoch,
                "physical_ordinal": ordinal,
                "attempt": attempt,
                "operation": operation.name,
                "operation_version": operation.version,
                "operation_document_sha256": operation.document_sha256,
                "request_key": key,
                "variables_sha256": variables_hash,
                "variable_keys": sorted(str(name) for name in variables),
                "context_keys": sorted(str(name) for name in (context or {})),
                "batch_size": len(variables.get("matchIds", ())) if "matchIds" in variables else None,
                "http_status": status,
                "response_sha256": response_sha,
                "response_bytes": response_bytes,
                "latency_seconds": round(latency, 6),
                "safe_headers": dict(headers),
                "safe_rate_headers": safe_rate_headers(headers),
                "retrying": retryable and attempt < self.max_retries,
                "retry_after_seconds": retry_after,
                "cache_hit": False,
                "cache_miss": True,
                "immutable_success": _is_immutable_success_response(status, error_kind),
                "error_kind": error_kind,
                "error": redact_text(error, self.token) if error else None,
                "raw_body_path": raw_body_path,
                "raw_metadata_path": raw_metadata_path,
                "archived_body_sha256": archived_sha if raw_metadata_path else None,
            }
            self._append_ledger(row)
            attempts.append(row)
            last_reason = error
            if rate_error is not None:
                raise rate_error
            if status in {401, 403}:
                raise StopRun("persistent STRATZ authentication failure", kind="authentication_failure")
            if error_kind == "schema_drift" or (error and _is_schema_error(error)):
                raise StopRun("STRATZ schema drift observed", kind="schema_drift")
            if error_kind == "graphql_error":
                raise StopRun("STRATZ returned a GraphQL error", kind="graphql_error")
            if error_kind == "missing_data":
                raise StopRun("STRATZ response has no data", kind="response_shape")
            if status == 429 and attempt >= self.max_retries:
                raise StopRun("persistent STRATZ rate limit response", kind="rate_limited")
            if not retryable or attempt >= self.max_retries:
                break
            delay = max(
                retry_after or 0.0,
                min(MAX_BACKOFF_SECONDS, 0.25 * (2**attempt)),
            )
            if delay > MAX_WAIT_SECONDS:
                raise PauseRun("retry reset exceeds bounded wait", resume_at=datetime.fromtimestamp(time.time() + delay, UTC).isoformat())
            await self._sleep(delay)
        final = attempts[-1]
        if final.get("http_status", 0) is None or int(final.get("http_status") or 0) >= 400:
            raise StopRun(redact_text(last_reason or "STRATZ request failed", self.token), kind=str(final.get("error_kind") or "provider_error"))
        if not isinstance(last_payload, Mapping):
            raise StopRun("STRATZ returned invalid JSON", kind="invalid_response")
        return last_payload, {
            "request_key": key,
            "variables_sha256": variables_hash,
            "cache_hit": False,
            "cache_miss": True,
            "physical_attempts": len(attempts),
            "raw_response_sha256": final.get("response_sha256"),
        }

    def _history_account_state(self, target: CohortTarget) -> dict[str, Any]:
        accounts = self.state.setdefault("history", {}).setdefault("accounts", {})
        return accounts.setdefault(target.pseudonym, {"status": "pending", "next_page": 0, "pages": []})

    def _parsed_account_state(self, target: CohortTarget) -> dict[str, Any]:
        accounts = self.state.setdefault("parsed", {}).setdefault("accounts", {})
        return accounts.setdefault(target.pseudonym, {"status": "pending", "next_batch": 0, "batches": []})

    def _history_pages(self, target: CohortTarget, account_state: Mapping[str, Any]) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        for page in account_state.get("pages", ()):
            if not isinstance(page, Mapping):
                continue
            path = self.output_dir / str(page.get("normalized_path", ""))
            if path.is_file():
                pages.append(_read_json(path))
        return pages

    def _history_match_ids(self, target: CohortTarget) -> list[int]:
        path = self.canonical_history_dir / f"{target.pseudonym}.json"
        if not path.is_file():
            return []
        canonical = _read_json(path)
        return list(
            dict.fromkeys(
                int(row["match_id"])
                for row in canonical.get("rows", ())
                if isinstance(row, Mapping) and row.get("is_parsed") is True and isinstance(row.get("match_id"), int)
            )
        )

    async def _acquire_history(self, target: CohortTarget) -> None:
        account_state = self._history_account_state(target)
        if account_state.get("status") in {"complete", "truncated", "private", "unavailable"}:
            return
        window = self.state["window"]
        page_index = int(account_state.get("next_page", 0))
        while page_index < self.max_history_pages:
            variables = {
                "steamAccountId": target.account_id,
                "startDateTime": int(window["start_timestamp"]),
                "endDateTime": int(window["end_timestamp"]),
                "take": HISTORY_PAGE_SIZE,
                "skip": page_index * HISTORY_PAGE_SIZE,
            }
            try:
                payload, request_meta = await self.request(
                    GET_PLAYER_HISTORY_PAGE,
                    variables,
                    context={"phase": "HISTORY", "split": target.split},
                )
            except (PauseRun, StopRun):
                raise
            except RunnerError:
                account_state["status"] = "failed"
                self._save_state()
                raise
            try:
                normalized = normalize_history_page(
                    payload,
                    account_id=target.account_id,
                    pseudonym=target.pseudonym,
                    split=target.split,
                    source_position=target.source_position,
                    window_start=int(window["start_timestamp"]),
                    window_end=int(window["end_timestamp"]),
                )
            except AccountUnavailable:
                account_state["status"] = "unavailable"
                self._save_state()
                break
            except RunnerError:
                account_state["status"] = "failed"
                self._save_state()
                raise
            page_path = self.normalized_history_dir / target.pseudonym / f"page-{page_index:04d}.json"
            page_payload = dict(normalized)
            page_payload["raw_response_sha256"] = request_meta.get("raw_response_sha256")
            page_payload["request_key"] = request_meta["request_key"]
            if page_path.exists():
                if digest(_read_json(page_path)) != digest(page_payload):
                    raise RunnerError("normalized history page changed on resume")
            else:
                _write_json(page_path, page_payload)
            pages = account_state.setdefault("pages", [])
            page_entry = {
                "page": page_index,
                "normalized_path": page_path.relative_to(self.output_dir).as_posix(),
                "request_key": request_meta["request_key"],
                "raw_response_sha256": request_meta.get("raw_response_sha256"),
                "row_count": len(normalized["rows"]),
            }
            if not any(item.get("page") == page_index for item in pages if isinstance(item, Mapping)):
                pages.append(page_entry)
            profile = normalized["profile"]
            if not profile.get("available"):
                account_state["status"] = "unavailable"
                account_state["next_page"] = page_index + 1
                self._save_state()
                break
            account_state["profile"] = profile
            account_state["next_page"] = page_index + 1
            starts = [row.get("started_at") for row in normalized["rows"] if isinstance(row.get("started_at"), int)]
            page_index += 1
            complete = len(normalized["rows"]) < HISTORY_PAGE_SIZE or any(
                value < int(window["start_timestamp"]) for value in starts
            )
            if complete:
                account_state["status"] = "complete"
                self._save_state()
                break
            self._save_state()
        else:
            account_state["status"] = "truncated"
            account_state["truncation_reason"] = "history_page_ceiling"
            self._save_state()
        if account_state.get("status") in {"complete", "truncated", "unavailable"}:
            pages = self._history_pages(target, account_state)
            completeness = "truncated" if account_state.get("status") == "truncated" else account_state.get("status", "complete")
            canonical = canonicalize_history(
                pages,
                pseudonym=target.pseudonym,
                source_position=target.source_position,
                split=target.split,
                window_start=int(window["start_timestamp"]),
                window_end=int(window["end_timestamp"]),
                completeness=str(completeness),
            )
            canonical_path = self.canonical_history_dir / f"{target.pseudonym}.json"
            if canonical_path.exists() and digest(_read_json(canonical_path)) != digest(canonical):
                raise RunnerError("canonical history changed on resume")
            if not canonical_path.exists():
                _write_json(canonical_path, canonical)
            account_state["canonical_path"] = canonical_path.relative_to(self.output_dir).as_posix()
            account_state["history_row_count"] = canonical["unique_match_count"]
            account_state["parsed_opportunity_count"] = sum(row.get("is_parsed") is True for row in canonical["rows"])
            if account_state.get("status") == "complete" and not canonical["profile"].get("available"):
                account_state["status"] = "unavailable"
            self._save_state()

    async def _acquire_parsed(self, target: CohortTarget) -> None:
        history_state = self._history_account_state(target)
        parsed_state = self._parsed_account_state(target)
        if parsed_state.get("status") in {"complete", "skipped_anonymous", "no_valid_opportunities"}:
            return
        profile = history_state.get("profile", {})
        if profile.get("is_anonymous") is not False:
            parsed_state["status"] = "skipped_anonymous"
            self._save_state()
            return
        match_ids = parsed_state.get("match_ids")
        if not isinstance(match_ids, list):
            match_ids = self._history_match_ids(target)
            parsed_state["match_ids"] = match_ids
            parsed_state["batch_count"] = (len(match_ids) + PARSED_BATCH_SIZE - 1) // PARSED_BATCH_SIZE
            if not match_ids:
                parsed_state["status"] = "no_valid_opportunities"
                self._save_state()
                return
            self._save_state()
        match_offset = int(parsed_state.get("next_batch", 0))
        batches = parsed_state.setdefault("batches", [])
        if batches:
            last_batch = max(
                (item for item in batches if isinstance(item, Mapping) and isinstance(item.get("batch"), int)),
                key=lambda item: int(item["batch"]),
            )
            last_doc = _read_json(self.output_dir / str(last_batch["normalized_path"]))
            match_offset = max(match_offset, int(last_batch["batch"]) + int(last_doc["requested_batch_size"]))
        while match_offset < len(match_ids):
            batch_ids = match_ids[match_offset : match_offset + PARSED_BATCH_SIZE]
            payload, request_meta = await self.request(
                GET_PARSED_ACQUISITION_BATCH,
                {"steamAccountId": target.account_id, "matchIds": batch_ids},
                context={"phase": "PARSED", "split": target.split},
            )
            normalized = normalize_parsed_batch(
                payload,
                account_id=target.account_id,
                requested_ids=batch_ids,
                pseudonym=target.pseudonym,
                split=target.split,
                source_position=target.source_position,
            )
            path = self.normalized_parsed_dir / target.pseudonym / f"batch-{match_offset:04d}.json"
            normalized["raw_response_sha256"] = request_meta.get("raw_response_sha256")
            normalized["request_key"] = request_meta["request_key"]
            if path.exists() and digest(_read_json(path)) != digest(normalized):
                raise RunnerError("normalized parsed batch changed on resume")
            if not path.exists():
                _write_json(path, normalized)
            if not any(item.get("batch") == match_offset for item in batches if isinstance(item, Mapping)):
                batches.append(
                    {
                        "batch": match_offset,
                        "normalized_path": path.relative_to(self.output_dir).as_posix(),
                        "request_key": request_meta["request_key"],
                        "raw_response_sha256": request_meta.get("raw_response_sha256"),
                        "row_count": len(normalized["rows"]),
                    }
                )
            match_offset += len(batch_ids)
            parsed_state["next_batch"] = match_offset
            self._save_state()
        batch_docs = [
            _read_json(self.output_dir / str(item["normalized_path"]))
            for item in parsed_state.get("batches", ())
            if isinstance(item, Mapping)
        ]
        canonical = canonicalize_parsed(batch_docs, pseudonym=target.pseudonym, source_position=target.source_position, split=target.split)
        path = self.canonical_parsed_dir / f"{target.pseudonym}.json"
        if path.exists() and digest(_read_json(path)) != digest(canonical):
            raise RunnerError("canonical parsed data changed on resume")
        if not path.exists():
            _write_json(path, canonical)
        parsed_state["status"] = "complete"
        parsed_state["canonical_path"] = path.relative_to(self.output_dir).as_posix()
        parsed_state["parsed_row_count"] = canonical["unique_match_count"]
        self._save_state()

    def reconcile(self) -> dict[str, Any]:
        ordinals = [row.get("physical_ordinal") for row in self.ledger_rows]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise RunnerError("request ledger physical attempts are not contiguous")
        response_rows = [row for row in self.ledger_rows if row.get("raw_metadata_path")]
        metadata_paths = sorted(self.raw_dir.glob("*.json"))
        if len(response_rows) != len(metadata_paths):
            raise RunnerError("raw archive count does not reconcile to response attempts")
        metadata_by_path: dict[str, dict[str, Any]] = {}
        body_paths: set[str] = set()
        seen_success: set[str] = set()
        for row in self.ledger_rows:
            key = row.get("request_key")
            if row.get("immutable_success") is True and not _is_immutable_success_row(row):
                raise RunnerError("ledger marks an errored response as immutable success")
            if _is_immutable_success_row(row):
                if not isinstance(key, str) or key in seen_success:
                    raise RunnerError("successful immutable request repeated")
                seen_success.add(key)
            if row.get("raw_metadata_path"):
                metadata_relative = str(row["raw_metadata_path"])
                metadata_path = self.output_dir / metadata_relative
                if not metadata_path.is_file():
                    raise RunnerError("ledger references a missing raw metadata object")
                metadata = _read_json(metadata_path)
                metadata_by_path[metadata_relative] = metadata
                if metadata.get("physical_ordinal") != row.get("physical_ordinal"):
                    raise RunnerError("ledger/raw physical ordinal mismatch")
                if metadata.get("operation_document_sha256") != row.get("operation_document_sha256"):
                    raise RunnerError("ledger/raw operation digest mismatch")
                if metadata.get("variables_sha256") != row.get("variables_sha256"):
                    raise RunnerError("ledger/raw variables hash mismatch")
                if metadata.get("response_sha256") != row.get("response_sha256"):
                    raise RunnerError("ledger/raw response hash mismatch")
                body_path = self.output_dir / str(metadata.get("body_path", ""))
                body_paths.add(str(metadata.get("body_path", "")))
                if row.get("raw_body_path") != metadata.get("body_path"):
                    raise RunnerError("ledger/raw body path mismatch")
                if not body_path.is_file() or sha256_file(body_path) != metadata.get("archived_body_sha256"):
                    raise RunnerError("ledger/raw body hash mismatch")
        actual_metadata = {path.relative_to(self.output_dir).as_posix() for path in metadata_paths}
        if set(metadata_by_path) != actual_metadata:
            raise RunnerError("raw metadata objects are not exactly represented in the ledger")
        actual_bodies = {path.relative_to(self.output_dir).as_posix() for path in self.raw_dir.glob("*.body")}
        if body_paths != actual_bodies:
            raise RunnerError("raw body objects are not exactly represented in the ledger")
        return {
            "physical_attempts": len(self.ledger_rows),
            "response_attempts": len(response_rows),
            "raw_objects": len(metadata_paths),
            "successful_immutable_requests": len(seen_success),
            "reconciled": True,
        }

    def write_manifest(self, atlas: Mapping[str, Any]) -> dict[str, Any]:
        ledger = self.reconcile()
        raw_hashes = []
        for path in sorted(self.raw_dir.glob("*.json")):
            metadata = _read_json(path)
            raw_hashes.append(
                {
                    "ordinal": metadata.get("physical_ordinal"),
                    "response_sha256": metadata.get("response_sha256"),
                }
            )
        manifest = {
            "schema_version": RUNNER_SCHEMA,
            "status": self.state.get("status"),
            "phase": self.state.get("phase"),
            "freeze": self.state.get("freeze"),
            "window": self.state.get("window"),
            "operation_registry": {
                GET_PLAYER_HISTORY_PAGE.name: GET_PLAYER_HISTORY_PAGE.document_sha256,
                GET_PARSED_ACQUISITION_BATCH.name: GET_PARSED_ACQUISITION_BATCH.document_sha256,
            },
            "cohort": {"history_players": 900, "parsed_players": 256, "reserved_or_sealed_touched": False},
            "ledger": ledger,
            "raw": {"objects": len(raw_hashes), "response_hash_manifest_sha256": digest(raw_hashes)},
            "atlas": {
                "schema_version": atlas.get("schema_version"),
                "identities_included": False,
                "unknown_semantics_excluded": True,
            },
            "policy": {
                "adaptive_top_up": False,
                "finding_output_selection": False,
                "opendota_calls": 0,
                "rank_or_mmr_used": False,
                "raw_committed": False,
            },
        }
        _write_json(self.output_dir / "manifests/run-manifest.json", manifest)
        return manifest

    async def run(self) -> dict[str, Any]:
        if not self.network:
            self.state["status"] = "OFFLINE_VALIDATED"
            self.state["phase"] = "VALIDATION"
            self._save_state()
            atlas = build_qa_atlas(self.cohort, self.output_dir, self.state)
            _write_json(self.output_dir / "derived/qa-atlas.json", atlas)
            self.write_manifest(atlas)
            return {"status": self.state["status"], "physical_attempts": 0, "network_calls": {"stratz": 0, "opendota": 0}}
        self.state["status"] = "RUNNING"
        self.state["stop_reason"] = None
        self._save_state()
        try:
            self.state["phase"] = "HISTORY"
            for target in self.cohort.targets:
                await self._acquire_history(target)
            self.state["phase"] = "PARSED"
            self._save_state()
            for target in self.cohort.parsed_targets:
                await self._acquire_parsed(target)
            self.state["phase"] = "COMPLETE"
            self.state["status"] = "COMPLETE"
        except PauseRun as exc:
            self.state["status"] = "PARTIAL_PAUSED"
            self.state["stop_reason"] = exc.reason
            self.state["resume_at"] = exc.resume_at
        except StopRun as exc:
            self.state["status"] = "STOP"
            self.state["stop_reason"] = exc.reason
            self.state["stop_kind"] = exc.kind
        except RunnerError as exc:
            self.state["status"] = "STOP"
            self.state["stop_reason"] = str(exc)
            self.state["stop_kind"] = "runner_error"
        self._save_state()
        atlas = build_qa_atlas(self.cohort, self.output_dir, self.state)
        _write_json(self.output_dir / "derived/qa-atlas.json", atlas)
        self.write_manifest(atlas)
        return {
            "status": self.state.get("status"),
            "phase": self.state.get("phase"),
            "physical_attempts": len(self.ledger_rows),
            "stop_reason": self.state.get("stop_reason"),
            "resume_at": self.state.get("resume_at"),
            "network_calls": {"stratz": len(self.ledger_rows), "opendota": 0},
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-dir", type=Path, default=DEFAULT_FREEZE_DIR)
    parser.add_argument("--source-frame", type=Path, default=DEFAULT_SOURCE_FRAME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dotenv-path", type=Path)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-history-pages", type=int, default=MAX_HISTORY_PAGES)
    parser.add_argument("--acknowledge-network-collection", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    cohort = load_frozen_cohort(args.freeze_dir, source_frame_path=args.source_frame)
    token = None
    if args.acknowledge_network_collection:
        if args.dotenv_path is None:
            raise RunnerError("network collection requires --dotenv-path")
        token = load_stratz_token(args.dotenv_path)
    async with CorpusRunner(
        cohort,
        output_dir=args.output_dir,
        token=token,
        endpoint=args.endpoint,
        network=args.acknowledge_network_collection,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        max_history_pages=args.max_history_pages,
    ) as runner:
        return await runner.run()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = asyncio.run(_run(args))
    except (RunnerError, httpx.HTTPError) as exc:
        print(f"stratz corpus runner stopped: {str(exc)}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") in {"OFFLINE_VALIDATED", "COMPLETE", "PARTIAL_PAUSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
