"""Profile-scoped evidence coverage checkpoints for known match timestamps."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from .schema import account_matches, coverage, matches


def record_match_coverage(connection: Connection, *, profile_id: str, match_id: int) -> None:
    """Call only inside a profile-fenced publication transaction."""
    row = connection.execute(select(
        account_matches.c.mode, matches.c.started_at, matches.c.evidence_state,
        matches.c.terminal_reason,
    ).join(matches, matches.c.match_id == account_matches.c.match_id).where(
        account_matches.c.profile_id == profile_id,
        account_matches.c.match_id == match_id,
    )).one()
    if row.mode not in {"STANDARD", "TURBO"} or row.started_at is None or row.evidence_state == "DISCOVERED":
        return
    for evidence_class, state, reason in (
        ("SUMMARY", "KNOWN", None),
        ("REPLAY", "KNOWN" if row.evidence_state == "REPLAY_READY" else
         "GAP" if row.evidence_state == "REPLAY_UNAVAILABLE" else "PENDING",
         row.terminal_reason if row.evidence_state == "REPLAY_UNAVAILABLE" else None),
    ):
        identity = dict(profile_id=profile_id, mode=row.mode, evidence_class=evidence_class,
                        start_at=row.started_at, end_at=row.started_at)
        connection.execute(insert(coverage).values(
            id=str(uuid4()), **identity, state=state, reason=reason,
        ).on_conflict_do_update(
            index_elements=list(identity), set_={"state": state, "reason": reason},
            where=(coverage.c.state != "KNOWN") | (state == "KNOWN"),
        ))
