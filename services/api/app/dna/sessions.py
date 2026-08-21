"""Duration-aware session inference for summary-only match history."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.ingestion.summary_normalize import NormalizedSummaryMatch

SESSION_VERSION = "sessions-5.0.0"


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
    left_censored: bool = False
    right_censored: bool = False

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
            "left_censored": self.left_censored,
            "right_censored": self.right_censored,
        }


@dataclass(frozen=True, slots=True)
class SessionResult:
    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: tuple[Session, ...]
    policy: SessionPolicy
    sensitivity: dict[int, tuple[tuple[int, ...], ...]]
    window_start: int | None = None
    window_end: int | None = None

    @property
    def dated_matches(self) -> tuple[NormalizedSummaryMatch, ...]:
        return tuple(item for item in self.matches if item.started_at is not None)

    @property
    def completed_sessions(self) -> tuple[Session, ...]:
        return tuple(item for item in self.sessions if not item.right_censored and not item.corrupt)

    @property
    def left_censored_session_count(self) -> int:
        return sum(item.left_censored for item in self.sessions)

    @property
    def right_censored_session_count(self) -> int:
        return sum(item.right_censored for item in self.sessions)

    def as_dict(self) -> dict[str, Any]:
        return {
            "matches": [item.as_dict() for item in self.matches],
            "sessions": [item.as_dict() for item in self.sessions],
            "policy": {"gap_minutes": self.policy.gap_minutes, "version": self.policy.version},
            "sensitivity": {
                str(gap): [list(group) for group in groups]
                for gap, groups in self.sensitivity.items()
            },
            "window_start": self.window_start,
            "window_end": self.window_end,
            "left_censored_session_count": self.left_censored_session_count,
            "right_censored_session_count": self.right_censored_session_count,
        }


def infer_sessions(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    policy: SessionPolicy | None = None,
    *,
    sensitivity_gaps: tuple[int, ...] = (60, 90, 120),
    window_start: int | None = None,
    window_end: int | None = None,
    pre_window_anchor: bool = False,
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
        first_match = group[0]
        last_match = group[-1]
        start = first_match.started_at or 0
        end = last_match.ended_at if last_match.ended_at is not None else last_match.started_at or start
        sessions.append(Session(session_id, ids, start, max(start, end), corrupt, corrupt_match_ids))
        for position, item in enumerate(group, start=1):
            assignments[item.match_id] = (session_id, position, item.match_id in corrupt_ids)

    # A time window can cut through a real session.  Keep the flags on the
    # session rather than pretending the first returned game is Game 1 or the
    # current last game proves that the session ended.
    if sessions:
        first_session = sessions[0]
        last_session = sessions[-1]
        left_censored = not pre_window_anchor
        sessions[0] = replace(first_session, left_censored=left_censored)
        latest_end = last_session.end_time
        end_anchor_gap = (
            (window_end - latest_end) if window_end is not None else None
        )
        right_censored = end_anchor_gap is None or end_anchor_gap <= policy.gap_seconds
        sessions[-1] = replace(
            last_session,
            right_censored=right_censored,
            left_censored=left_censored if len(sessions) == 1 else last_session.left_censored,
        )

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
    return SessionResult(tuple(assigned), tuple(sessions), policy, sensitivity, window_start, window_end)


def _group_ids(
    dated: list[NormalizedSummaryMatch], policy: SessionPolicy
) -> tuple[list[list[NormalizedSummaryMatch]], set[int]]:
    if not dated:
        return [], set()
    groups: list[list[NormalizedSummaryMatch]] = [[dated[0]]]
    corrupt_ids: set[int] = set()
    for current in dated[1:]:
        previous = groups[-1][-1]
        previous_end = previous.ended_at
        if previous_end is None or current.started_at is None:
            corrupt_ids.update({previous.match_id, current.match_id})
            groups.append([current])
            continue
        queue_gap = current.started_at - previous_end
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
