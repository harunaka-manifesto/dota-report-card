"""Duration-aware session inference for summary-only match history."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.ingestion.summary_normalize import NormalizedSummaryMatch

SESSION_VERSION = "sessions-1.1.0"


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    gap_minutes: int = 90
    clock_tolerance_seconds: int = 300
    version: str = SESSION_VERSION

    @property
    def gap_seconds(self) -> int:
        return max(1, self.gap_minutes) * 60


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    match_ids: tuple[int, ...]
    start_time: int
    end_time: int
    corrupt: bool = False
    corrupt_match_ids: tuple[int, ...] = ()

    @property
    def match_count(self) -> int:
        return len(self.match_ids)

    @property
    def elapsed_seconds(self) -> int:
        return max(0, self.end_time - self.start_time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "match_ids": list(self.match_ids),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "elapsed_seconds": self.elapsed_seconds,
            "match_count": self.match_count,
            "corrupt": self.corrupt,
            "corrupt_match_ids": list(self.corrupt_match_ids),
        }


@dataclass(frozen=True, slots=True)
class SessionResult:
    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: tuple[Session, ...]
    policy: SessionPolicy
    sensitivity: dict[int, tuple[tuple[int, ...], ...]]

    @property
    def dated_matches(self) -> tuple[NormalizedSummaryMatch, ...]:
        return tuple(item for item in self.matches if item.started_at is not None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "matches": [item.as_dict() for item in self.matches],
            "sessions": [item.as_dict() for item in self.sessions],
            "policy": {"gap_minutes": self.policy.gap_minutes, "version": self.policy.version},
            "sensitivity": {
                str(gap): [list(group) for group in groups]
                for gap, groups in self.sensitivity.items()
            },
        }


def infer_sessions(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    policy: SessionPolicy | None = None,
    *,
    sensitivity_gaps: tuple[int, ...] = (60, 90, 120),
) -> SessionResult:
    policy = policy or SessionPolicy()
    ordered = sorted(
        matches,
        key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
    )
    dated = [item for item in ordered if item.started_at is not None]
    groups, corrupt_ids = _group_ids(dated, policy)
    sessions: list[Session] = []
    assignments: dict[int, tuple[str, int, bool]] = {}
    for index, group in enumerate(groups, start=1):
        session_id = f"session-{index}"
        ids = tuple(item.match_id for item in group)
        corrupt_match_ids = tuple(item.match_id for item in group if item.match_id in corrupt_ids)
        # A clock-overlap invalidates only the affected rows/transitions. The
        # rest of a long session remains usable evidence.
        corrupt = len(corrupt_match_ids) == len(group)
        first = group[0]
        last = group[-1]
        start = first.started_at or 0
        end = last.ended_at if last.ended_at is not None else last.started_at or start
        sessions.append(Session(session_id, ids, start, max(start, end), corrupt, corrupt_match_ids))
        for position, item in enumerate(group, start=1):
            assignments[item.match_id] = (session_id, position, item.match_id in corrupt_ids)

    assigned: list[NormalizedSummaryMatch] = []
    for item in ordered:
        assignment = assignments.get(item.match_id)
        if assignment is None:
            assigned.append(item.with_session(None, None))
        else:
            assigned.append(item.with_session(assignment[0], assignment[1], corrupt=assignment[2]))

    sensitivity = {
        gap: tuple(
            tuple(item.match_id for item in group)
            for group in _group_ids(dated, replace(policy, gap_minutes=gap))[0]
        )
        for gap in sorted(set(sensitivity_gaps) | {policy.gap_minutes})
    }
    return SessionResult(tuple(assigned), tuple(sessions), policy, sensitivity)


def _group_ids(
    dated: list[NormalizedSummaryMatch], policy: SessionPolicy
) -> tuple[list[list[NormalizedSummaryMatch]], set[int]]:
    if not dated:
        return [], set()
    groups: list[list[NormalizedSummaryMatch]] = [[dated[0]]]
    corrupt_ids: set[int] = set()
    for current in dated[1:]:
        previous = groups[-1][-1]
        previous_start = previous.started_at or 0
        previous_duration = max(previous.duration_seconds or 0, 0)
        queue_gap = (current.started_at or 0) - (previous_start + previous_duration)
        if queue_gap < -abs(policy.clock_tolerance_seconds):
            corrupt_ids.update({previous.match_id, current.match_id})
            groups.append([current])
        elif queue_gap > policy.gap_seconds:
            groups.append([current])
        else:
            groups[-1].append(current)
    return groups, corrupt_ids


def session_group_ids(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    gap_minutes: int,
) -> tuple[tuple[int, ...], ...]:
    dated = sorted(
        (item for item in matches if item.started_at is not None),
        key=lambda item: (item.started_at or 0, item.match_id),
    )
    groups, _ = _group_ids(dated, SessionPolicy(gap_minutes=gap_minutes))
    return tuple(tuple(item.match_id for item in group) for group in groups)
