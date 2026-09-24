"""Provisional, versioned team-relative role assignment from retained facts.

Scores describe assignment ambiguity, not calibrated probabilities. Outcome,
KDA, native provider position and hero popularity are not classification inputs.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from itertools import permutations
from typing import Any

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.evidence import canonical_json
from app.tracker.normalization import InvalidEvidence
from app.tracker.schema import match_players, matches, parameter_sets, positions

ROLES = {1: "CARRY", 2: "MID", 3: "OFFLANE", 4: "SUPPORT", 5: "SUPPORT"}
FARM_FIELDS = ("net_worth", "gold_per_min", "last_hits", "gold_spent")


@dataclass(frozen=True)
class RolePolicy:
    version: str = "role-assignment-provisional-1"
    farm_weight: float = 1.0
    lane_weight: float = 6.0
    support_weight: float = 1.0
    confidence_threshold: float = 0.60

    def __post_init__(self) -> None:
        if not self.version or len(self.version) > 64 or any(not math.isfinite(v) or v <= 0 for v in (self.farm_weight, self.lane_weight, self.support_weight)) or not 0 < self.confidence_threshold <= 1:
            raise ValueError("Invalid role policy")


def assign_positions(players: list[dict[str, Any]], *, evidence_profile: str = "SUMMARY", policy: RolePolicy = RolePolicy()) -> dict[str, Any]:
    """Jointly assign positions 1–5 per team; never rank across opposing teams.

    Replay inputs are canonical lane SAFE/MID/OFF and optional wards_placed, not
    native position labels. Summary intentionally ignores any such supplied fields.
    Only farm fields observed for every teammate enter relative ranks. Missing
    required team evidence gives a classification failure, not an Unknown role.
    """
    if evidence_profile not in {"SUMMARY", "REPLAY"} or len(players) != 10 or any(not isinstance(p, dict) for p in players) or {p.get("player_slot") for p in players} != set(range(10)):
        raise InvalidEvidence("Role assignment requires ten canonical slots")
    inputs = []
    for player in sorted(players, key=lambda p: p["player_slot"]):
        slot = player["player_slot"]
        if type(slot) is not int or player.get("team") != ("RADIANT" if slot < 5 else "DIRE"):
            raise InvalidEvidence("Role assignment team mismatch")
        values = player.get("values")
        if not isinstance(values, dict):
            values = {}
        farm = {key: value if type(value := values.get(key)) is int and value >= 0 else None for key in FARM_FIELDS}
        lane = player.get("lane") if evidence_profile == "REPLAY" else None
        wards = player.get("wards_placed") if evidence_profile == "REPLAY" else None
        inputs.append(dict(player_slot=slot, team=player["team"], farm=farm,
                           lane=lane if lane in {"SAFE", "MID", "OFF"} else None,
                           wards=wards if type(wards) is int and wards >= 0 else None))
    digest = hashlib.sha256(canonical_json({"players": inputs, "policy": asdict(policy), "evidence_profile": evidence_profile})).hexdigest()
    result: list[dict[str, Any]] = []
    for team in (inputs[:5], inputs[5:]):
        fields = [key for key in FARM_FIELDS if all(p["farm"][key] is not None for p in team)]
        if not fields:
            result.extend(dict(player_slot=p["player_slot"], team=p["team"], position=None, role=None, confidence=None,
                               confidence_bucket=None, reason="MISSING_FARM_PRIORITY") for p in team)
            continue
        # Midranks preserve ties without manufacturing a farm difference.
        ranks = [sum(1 + sum(q["farm"][key] > p["farm"][key] for q in team)
                         + (sum(q["farm"][key] == p["farm"][key] for q in team) - 1) / 2 for key in fields) / len(fields) for p in team]
        scores = []
        for index, player in enumerate(team):
            per_position = []
            for position in range(1, 6):
                score = -policy.farm_weight * abs(ranks[index] - position)
                expected_lane = {1: "SAFE", 2: "MID", 3: "OFF", 4: "OFF", 5: "SAFE"}[position]
                if player["lane"] is not None:
                    score += policy.lane_weight * (1 if player["lane"] == expected_lane else -1)
                if player["wards"] is not None:
                    # Relative support behavior has less weight than lane evidence.
                    lower = sum(q["wards"] is not None and q["wards"] < player["wards"] for q in team) / 4
                    score += policy.support_weight * lower * (1 if position >= 4 else -1)
                per_position.append(score)
            scores.append(per_position)
        choices = [(sum(scores[i][position - 1] for i, position in enumerate(order)), order) for order in permutations(range(1, 6))]
        choices.sort(key=lambda choice: (-choice[0], choice[1]))
        best_score, best = choices[0]
        for index, player in enumerate(team):
            role = ROLES[best[index]]
            alternative = max(score for score, order in choices if ROLES[order[index]] != role)
            margin = max(0.0, best_score - alternative)
            confidence = margin / (margin + policy.farm_weight + policy.lane_weight + policy.support_weight)
            # Farm ordering alone cannot establish lane identity with high confidence.
            high = player["lane"] is not None and confidence >= policy.confidence_threshold
            result.append(dict(player_slot=player["player_slot"], team=player["team"], position=best[index], role=role,
                               confidence=confidence, confidence_bucket="high" if high else "low",
                               reason="PROVISIONAL_REPLAY" if evidence_profile == "REPLAY" else "SUMMARY_FARM_ONLY"))
    return dict(version=policy.version, inputs_digest=digest, evidence_profile=evidence_profile, provisional=True, policy=asdict(policy), players=result)


def persist_summary_positions(connection: Connection, match_id: int, *, policy: RolePolicy = RolePolicy()) -> dict[str, Any]:
    rows = connection.execute(select(match_players).where(match_players.c.match_id == match_id).order_by(match_players.c.player_slot)).mappings().all()
    players = [{**row["summary"], "player_slot": row["player_slot"], "team": row["team"]} for row in rows]
    conflicts = connection.scalar(select(matches.c.quarantined_fields).where(matches.c.match_id == match_id)) or []
    for player in players:
        values = dict(player.get("values") or {})
        for key in FARM_FIELDS:
            if f"players.{player['player_slot']}.values.{key}" in conflicts:
                values.pop(key, None)
        player["values"] = values
    parameters = asdict(policy)
    policy_digest = hashlib.sha256(canonical_json(parameters)).hexdigest()
    connection.execute(insert(parameter_sets).values(version=policy.version, kind="ROLE_CLASSIFIER", digest=policy_digest,
        status="PROVISIONAL", parameters=parameters, provenance={"calibration": "PENDING", "confidence": "assignment margin, not probability"},
        created_at=func.now()).on_conflict_do_nothing())
    existing = connection.execute(select(parameter_sets).where(parameter_sets.c.version == policy.version)).mappings().one()
    if existing["kind"] != "ROLE_CLASSIFIER" or existing["digest"] != policy_digest:
        raise ValueError("Role policy version reused with different parameters")
    assignment = assign_positions(players, policy=policy)
    for player in assignment["players"]:
        connection.execute(insert(positions).values(match_id=match_id, player_slot=player["player_slot"], team=player["team"],
            evidence_profile="SUMMARY", version=assignment["version"], inputs_digest=assignment["inputs_digest"], position=player["position"],
            confidence=player["confidence"], reason=player["reason"], created_at=func.now()).on_conflict_do_nothing())
    return assignment
