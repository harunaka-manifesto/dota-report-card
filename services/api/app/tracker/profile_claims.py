"""Versioned, coverage-honest Profile claim lifecycle primitives."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from sqlalchemy import Connection, text

ClaimState = Literal["CANDIDATE", "CONFIRMED", "FADING", "RETIRED"]
Mode = Literal["STANDARD", "TURBO"]
MAX_EVIDENCE_MATCHES = 200


@dataclass(frozen=True)
class ClaimPolicy:
    version: str
    persistence_gap: int


@dataclass(frozen=True)
class ClaimEvaluation:
    claim_id: str
    claim_version: str
    mode: Mode
    scope: str
    checkpoint_seq: int
    match_id: int
    eligible: bool
    coverage_complete: bool
    enter_met: bool
    exit_met: bool
    evidence: Mapping[str, Any]


@dataclass(frozen=True)
class ClaimStateResult:
    state: ClaimState | None
    state_since_match_id: int | None
    checkpoint_seq: int
    lifecycle: Mapping[str, Any]
    evidence: Mapping[str, Any]
    inputs_digest: str
    evaluation_digest: str


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _validated_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Require actual sampled evidence; incomplete coverage is refused upstream."""
    required = {"window", "n", "aggregate_values", "thresholds_crossed", "sample_match_ids", "representative_match_ids", "coverage"}
    if not required <= evidence.keys():
        raise ValueError("claim evidence is incomplete")
    window, coverage = evidence["window"], evidence["coverage"]
    if not isinstance(window, dict) or not {"definition", "start_at", "end_at"} <= window.keys():
        raise ValueError("claim window must describe the actual period")
    if not isinstance(coverage, dict) or coverage.get("complete") is not True or not isinstance(coverage.get("from_at"), str):
        raise ValueError("claim window coverage is incomplete")
    match_ids = evidence["sample_match_ids"]
    representatives = evidence["representative_match_ids"]
    if not isinstance(match_ids, list) or len(match_ids) > MAX_EVIDENCE_MATCHES:
        raise ValueError("claim evidence exceeds the bounded match window")
    if any(not isinstance(match_id, int) or match_id <= 0 for match_id in match_ids) or len(set(match_ids)) != len(match_ids):
        raise ValueError("claim evidence match references must be unique positive IDs")
    if not isinstance(evidence["n"], int) or evidence["n"] < 0 or evidence["n"] != len(match_ids):
        raise ValueError("claim sample count must match its evidence references")
    if not isinstance(representatives, list) or any(item not in match_ids for item in representatives):
        raise ValueError("representative matches must come from the measured sample")
    if not isinstance(evidence["aggregate_values"], dict) or not isinstance(evidence["thresholds_crossed"], list):
        raise ValueError("claim aggregate evidence is malformed")
    _canonical(evidence)
    result = dict(evidence)
    result["state_since"] = {"match_id": None, "at": None}
    return result


def evaluate(
    current: ClaimEvaluation,
    previous: Mapping[str, Any] | None,
    policy: ClaimPolicy,
) -> ClaimStateResult | None:
    """Advance one claim; None means withheld or a discarded candidate."""
    if not policy.version or policy.persistence_gap < 1:
        raise ValueError("a versioned positive persistence gap is required")
    if (current.mode not in ("STANDARD", "TURBO") or not current.claim_id or len(current.claim_id) > 80
            or not current.claim_version or len(current.claim_version) > 64 or not current.scope
            or len(current.scope) > 80 or current.checkpoint_seq < 1 or current.match_id < 1):
        raise ValueError("claim identity or checkpoint is invalid")
    if not current.eligible or not current.coverage_complete:
        return None
    evidence = _validated_evidence(current.evidence)
    digest_payload = {
        "policy": {"version": policy.version, "persistence_gap": policy.persistence_gap},
        "current": current.__dict__,
    }
    evaluation_digest = hashlib.sha256(_canonical(digest_payload)).hexdigest()
    inputs_digest = hashlib.sha256(_canonical({"evaluation": digest_payload,
                                               "previous": previous})).hexdigest()
    if previous is not None:
        if current.checkpoint_seq <= int(previous["checkpoint_seq"]):
            if current.checkpoint_seq == int(previous["checkpoint_seq"]) and evaluation_digest == previous.get("evaluation_digest"):
                return ClaimStateResult(previous["state"], previous.get("state_since_match_id"),
                                        previous["checkpoint_seq"], previous["lifecycle"], evidence,
                                        previous["inputs_digest"], evaluation_digest)
            raise ValueError("claim checkpoints must advance monotonically")

    old_state = cast(ClaimState | None, previous.get("state") if previous else None)
    state: ClaimState
    lifecycle = dict(previous.get("lifecycle", {})) if previous else {}
    since = previous.get("state_since_match_id") if previous else None
    pending = lifecycle.get("pending_state")
    pending_seq = lifecycle.get("pending_checkpoint_seq")

    if old_state in (None, "RETIRED"):
        if not current.enter_met:
            return None
        state = "CANDIDATE"
        since = current.match_id
        lifecycle = {"pending_state": "CONFIRMED", "pending_checkpoint_seq": current.checkpoint_seq, "policy_version": policy.version}
    else:
        assert old_state is not None
        desired: ClaimState | None = None
        if old_state == "CANDIDATE":
            desired = "CONFIRMED" if current.enter_met else None
        elif old_state == "CONFIRMED" and current.exit_met:
            desired = "FADING"
        elif old_state == "FADING":
            if current.exit_met:
                desired = "RETIRED"
            elif current.enter_met:
                desired = "CONFIRMED"
        if old_state == "CANDIDATE" and desired is None:
            return None
        state = old_state
        if desired is None:
            lifecycle.pop("pending_state", None)
            lifecycle.pop("pending_checkpoint_seq", None)
        elif pending != desired:
            lifecycle.update(pending_state=desired, pending_checkpoint_seq=current.checkpoint_seq, policy_version=policy.version)
        elif pending_seq is not None and current.checkpoint_seq - int(pending_seq) >= policy.persistence_gap:
            state = desired
            since = current.match_id
            lifecycle.pop("pending_state", None)
            lifecycle.pop("pending_checkpoint_seq", None)
    evidence["state_since"] = {"match_id": since, "at": evidence["window"]["end_at"]}
    return ClaimStateResult(state, since, current.checkpoint_seq, lifecycle, evidence,
                            inputs_digest, evaluation_digest)


def record_checkpoint(
    connection: Connection,
    *,
    profile_id: str,
    profile_generation: int,
    current: ClaimEvaluation,
    result: ClaimStateResult,
) -> bool:
    """Persist a claim checkpoint inside the caller's publication transaction."""
    if (result.state is None or result.checkpoint_seq != current.checkpoint_seq
            or not current.eligible or not current.coverage_complete):
        raise ValueError("only a matching eligible, covered claim result can be persisted")
    profile = connection.execute(
        text("SELECT generation, active FROM tracker_profiles WHERE id = :id FOR UPDATE"),
        {"id": profile_id},
    ).mappings().first()
    if profile is None or not profile["active"] or profile["generation"] != profile_generation:
        raise ValueError("claim publication has a stale or inactive profile generation")
    key = {"profile_id": profile_id, "mode": current.mode, "scope": current.scope,
           "claim_id": current.claim_id, "claim_version": current.claim_version}
    old = connection.execute(text("""SELECT checkpoint_seq, inputs_digest, evaluation_digest, evidence
        FROM tracker_profile_claim_checkpoints WHERE profile_id=:profile_id AND mode=:mode
        AND scope=:scope AND claim_id=:claim_id AND claim_version=:claim_version FOR UPDATE"""), key).mappings().first()
    if old is not None and old["checkpoint_seq"] >= current.checkpoint_seq:
        if old["checkpoint_seq"] == current.checkpoint_seq and old["evaluation_digest"] == result.evaluation_digest:
            return False
        raise ValueError("claim checkpoint is stale or conflicts with an existing evaluation")
    connection.execute(text("""INSERT INTO tracker_profile_claim_checkpoints
        (profile_id, profile_generation, mode, scope, claim_id, claim_version, state, evidence,
         previous_evidence, lifecycle, inputs_digest, evaluation_digest, checkpoint_seq, updated_at)
        VALUES (:profile_id, :generation, :mode, :scope, :claim_id, :claim_version, :state,
         CAST(:evidence AS jsonb), CAST(:previous_evidence AS jsonb), CAST(:lifecycle AS jsonb),
         :digest, :evaluation_digest, :checkpoint_seq, clock_timestamp())
        ON CONFLICT (profile_id, mode, scope, claim_id, claim_version) DO UPDATE SET
         profile_generation=EXCLUDED.profile_generation, state=EXCLUDED.state,
         previous_evidence=tracker_profile_claim_checkpoints.evidence, evidence=EXCLUDED.evidence,
         lifecycle=EXCLUDED.lifecycle, inputs_digest=EXCLUDED.inputs_digest,
         evaluation_digest=EXCLUDED.evaluation_digest,
         checkpoint_seq=EXCLUDED.checkpoint_seq, updated_at=EXCLUDED.updated_at"""), {
            **key, "generation": profile_generation, "state": result.state,
            "evidence": json.dumps(result.evidence, sort_keys=True, separators=(",", ":")),
            "previous_evidence": json.dumps(old["evidence"]) if old is not None else None,
            "lifecycle": json.dumps(result.lifecycle, sort_keys=True, separators=(",", ":")),
            "digest": result.inputs_digest, "evaluation_digest": result.evaluation_digest,
            "checkpoint_seq": current.checkpoint_seq,
        })
    return True


def load_checkpoint(connection: Connection, *, profile_id: str, mode: Mode,
                    scope: str, claim_id: str, claim_version: str) -> dict[str, Any] | None:
    row = connection.execute(text("""SELECT state, evidence, lifecycle, inputs_digest, evaluation_digest, checkpoint_seq
        FROM tracker_profile_claim_checkpoints WHERE profile_id=:profile_id AND mode=:mode
        AND scope=:scope AND claim_id=:claim_id AND claim_version=:claim_version"""), {
            "profile_id": profile_id, "mode": mode, "scope": scope,
            "claim_id": claim_id, "claim_version": claim_version,
        }).mappings().first()
    if row is None:
        return None
    evidence = row["evidence"]
    return {"state": row["state"], "state_since_match_id": evidence["state_since"]["match_id"],
            "checkpoint_seq": row["checkpoint_seq"], "lifecycle": row["lifecycle"],
            "inputs_digest": row["inputs_digest"], "evaluation_digest": row["evaluation_digest"]}
