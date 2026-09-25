"""Private/unavailable match data, kept distinct from "still syncing".

Onboarding §8 and settings §4: keep the link, keep Pro, keep the last coherent
state, block new acquisition, and on restoration recover from the original
link date. Detection uses only positive evidence: a history page that no
longer returns a match already accepted inside the same window means access
was withdrawn. An empty history for an account with no prior evidence stays
ambiguous (it may simply have no matches) and is not labelled private; that
limitation is recorded in the implementation ledger.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Connection, func, select, update

from .schema import (
    account_discoveries,
    bootstrap,
    bootstrap_search_items,
    dota_accounts,
    profiles,
    sync_state,
)


def mark_blocked(connection: Connection, account_id: int) -> None:
    connection.execute(update(dota_accounts).where(dota_accounts.c.account_id == account_id)
                       .values(visibility="BLOCKED"))
    connection.execute(update(sync_state).where(sync_state.c.account_id == account_id)
                       .values(blocked_reason="DATA_ACCESS_BLOCKED"))


def history_withdrawn(connection: Connection, *, account_id: int, window_start: datetime,
                      offset: int, rows: list[Any]) -> bool:
    """An empty first page while a previously accepted in-window match exists."""
    if offset != 0 or rows:
        return False
    return connection.scalar(select(account_discoveries.c.source_item_id).where(
        account_discoveries.c.account_id == account_id, account_discoveries.c.outcome == "ACCEPTED",
        account_discoveries.c.source_started_at >= window_start,
    ).limit(1)) is not None


def observe_history_page(connection: Connection, *, account_id: int, window_start: datetime,
                         offset: int, rows: list[Any]) -> None:
    if history_withdrawn(connection, account_id=account_id, window_start=window_start, offset=offset, rows=rows):
        mark_blocked(connection, account_id)
    elif rows:
        visibility = connection.scalar(select(dota_accounts.c.visibility).where(
            dota_accounts.c.account_id == account_id).with_for_update())
        if visibility != "ACCESSIBLE":
            connection.execute(update(dota_accounts).where(dota_accounts.c.account_id == account_id)
                               .values(visibility="ACCESSIBLE"))
        if visibility == "BLOCKED":
            restore_access(connection, account_id=account_id)


def restore_access(connection: Connection, *, account_id: int) -> list[str]:
    """Re-anchor recovery to the original link date for every active owner.

    Idempotent per blocked episode: the episode key is the account's discovery
    count at restoration, so repeated confirmations enqueue nothing new.
    """
    from .backfill import request_access_recovery
    from .bootstrap import request_bootstrap_search

    connection.execute(update(dota_accounts).where(dota_accounts.c.account_id == account_id,
                                                   dota_accounts.c.visibility == "BLOCKED")
                       .values(visibility="UNKNOWN"))
    connection.execute(update(sync_state).where(sync_state.c.account_id == account_id,
                                                sync_state.c.blocked_reason == "DATA_ACCESS_BLOCKED")
                       .values(blocked_reason=None))
    jobs: list[str] = []
    owners = connection.execute(select(profiles).where(
        profiles.c.account_id == account_id, profiles.c.active.is_(True)).with_for_update()).mappings().all()
    for profile in owners:
        blocked_modes = connection.scalars(select(bootstrap.c.mode).where(
            bootstrap.c.profile_id == profile["id"], bootstrap.c.outcome == "DATA_ACCESS_BLOCKED",
        )).all()
        if blocked_modes:
            # The original search saw no rows; restart it on the original window.
            connection.execute(bootstrap_search_items.delete().where(
                bootstrap_search_items.c.profile_id == profile["id"]))
            connection.execute(update(bootstrap).where(bootstrap.c.profile_id == profile["id"]).values(
                search_finished=False, cursor=None, discovered_count=0, eligible_count=0,
                settled_count=0, outcome=None, completed_at=None))
            jobs.append(request_bootstrap_search(connection, profile["id"], attempt="recovery"))
        episode = connection.scalar(select(func.count()).select_from(account_discoveries).where(
            account_discoveries.c.account_id == account_id))
        jobs.append(request_access_recovery(connection, profile["id"], episode=str(episode)))
    return jobs


def data_access_state(connection: Connection, account_id: int | None) -> str:
    visibility = connection.scalar(select(dota_accounts.c.visibility).where(
        dota_accounts.c.account_id == account_id))
    return "BLOCKED" if visibility == "BLOCKED" else "ACCESSIBLE" if visibility == "ACCESSIBLE" else "UNKNOWN"



def defer_if_blocked(connection: Connection, job: dict[str, Any]) -> bool:
    """New historical acquisition waits while access is withdrawn (settings §4).

    Foreground sync keeps running: its pages are how restoration is observed.
    The wait costs no failure attempt; recovery resumes from stored cursors.
    """
    from .jobs import reschedule

    if data_access_state(connection, job["account_id"]) != "BLOCKED":
        return False
    reschedule(connection, job, delay_seconds=3600, error="DATA_ACCESS_BLOCKED", failure=False)
    return True
