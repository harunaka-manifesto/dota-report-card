"""V7 pilot acquisition policy (owner decision D9, 2026-09-06).

The owner's principle, in their words: *give every user the strongest possible
analysis rather than optimizing prematurely for API scale.*

Three things follow, and this module is where each becomes checkable rather
than aspirational.

**Full depth for every pilot user.** No free/paid split in how much is
fetched. Section 8 of the report sells depth of *analysis*, not depth of
acquisition, so paid output must never be better merely because more matches
were pulled for it. ``PAID_MAY_ACQUIRE_MORE_THAN_FREE`` is ``False`` and the
tests hold it there.

**Fetch once, reuse forever.** A second report for the same account inside the
freshness window must not touch the provider. That makes the cache decision a
pure function of what is already stored, which is what ``plan`` is: given what
the store holds and what the report needs, it returns the matches to fetch,
and it returns none when the store already covers the request.

**Capacity is a consequence, not an input.** Full depth costs what it costs;
this module reports the resulting ceiling rather than trimming depth to hit a
number. Revisit only if real demand approaches it.

What this module does *not* do: it does not talk to the provider or to the
database. It decides. The wiring that carries a plan to the STRATZ client and
a result into ``app.storage`` lands with the V7 report pipeline, which does
not exist yet — the persistence *requirements* are stated in
``PERSISTENCE_REQUIREMENTS`` so that pipeline has something to satisfy and to
be tested against.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

ACQUISITION_POLICY_VERSION = "v7-acquisition-policy-1.0.0"

#: Matches acquired per pilot user. The research corpus used the same target,
#: so the per-report cost below is measured rather than modelled.
FULL_DEPTH_MATCHES = 500

#: Deep matches per provider request. The Pass-2 collector refuses any other
#: value, and the cost arithmetic here assumes it.
MATCHES_PER_REQUEST = 8

#: Requests spent per account in the Pass-2 production run: 13,264 requests
#: against 300 targeted accounts. Higher than 500/8 = 63 would suggest,
#: because an account's parsed matches are discovered as well as fetched, and
#: lower than a naive one-request-per-match model. Measured, not assumed.
MEASURED_REQUESTS_PER_ACCOUNT = 45

#: Provider ceilings, clock-aligned (not rolling). Mirrors the Pass-2 runner.
PROVIDER_LIMITS: dict[str, int] = {
    "second": 8,
    "minute": 150,
    "hour": 1_500,
    "day": 15_000,
}

#: Owner decision D9: paid output is a difference in analysis, never in how
#: much was acquired. Flipping this to True would make an upgrade retroactively
#: change what the free report could have said, which is the thing the decision
#: rules out.
PAID_MAY_ACQUIRE_MORE_THAN_FREE = False

#: How long stored match data satisfies a new report without refetching.
#: A match already played does not change, so the only reason to refetch is
#: to pick up matches played *since* — which ``plan`` handles by asking for
#: the gap, not by discarding what is stored.
STORED_MATCH_TTL_DAYS: int | None = None  # never stale

#: What the storage layer must guarantee for D9 to hold. Stated here because
#: the V7 report pipeline does not exist yet and these are the conditions it
#: has to meet; the tests assert the policy, not the storage.
PERSISTENCE_REQUIREMENTS: tuple[str, ...] = (
    "Raw provider payloads are stored per match and keyed by match id, so a "
    "match is fetched at most once per account regardless of how many reports "
    "are generated.",
    "Derived per-match features are stored alongside the raw payload and "
    "keyed by the feature version, so a feature-version bump recomputes from "
    "storage rather than refetching from the provider.",
    "Report generation for an account already in storage makes zero provider "
    "calls when no new matches have been played since the last acquisition.",
    "Account creation and payment reuse the existing analysis: neither "
    "triggers a refetch, and neither is a precondition for having one.",
    "Paid output is generated from the same stored matches as the free "
    "report. Depth of acquisition is identical; only the analysis differs.",
)


@dataclass(frozen=True)
class AcquisitionPlan:
    """What a report needs from the provider, given what is already stored."""

    account_id: str
    match_ids_to_fetch: tuple[int, ...]
    already_stored: int
    requests_required: int

    @property
    def hits_provider(self) -> bool:
        return bool(self.match_ids_to_fetch)


def requests_for(match_count: int) -> int:
    """Provider requests needed to fetch ``match_count`` deep matches."""

    if match_count < 0:
        raise ValueError("match_count must not be negative")
    return math.ceil(match_count / MATCHES_PER_REQUEST)


def plan(
    account_id: str,
    candidate_match_ids: Sequence[int],
    stored_match_ids: Iterable[int],
    *,
    depth: int = FULL_DEPTH_MATCHES,
) -> AcquisitionPlan:
    """Decide what to fetch for one account.

    ``candidate_match_ids`` is the account's recent matches, newest first.
    Only the newest ``depth`` are ever considered, and anything already in
    ``stored_match_ids`` is skipped — so a repeat report for an account whose
    matches are all stored plans zero requests, which is the whole of the
    owner's caching requirement expressed as a return value.

    Order is preserved: the fetch list stays newest-first, so a partially
    completed acquisition resumes on the matches that matter most.
    """

    if depth < 0:
        raise ValueError("depth must not be negative")
    stored = set(stored_match_ids)
    considered = list(candidate_match_ids)[:depth]
    to_fetch = tuple(match_id for match_id in considered if match_id not in stored)
    return AcquisitionPlan(
        account_id=account_id,
        match_ids_to_fetch=to_fetch,
        already_stored=len(considered) - len(to_fetch),
        requests_required=requests_for(len(to_fetch)),
    )


def reports_per_day(requests_per_account: int = MEASURED_REQUESTS_PER_ACCOUNT) -> int:
    """First-time reports the daily provider ceiling allows at full depth.

    Counts *first-time* reports only. A repeat report costs nothing, so real
    throughput exceeds this number by however much of the audience is
    returning — which is the point of D9's caching half.
    """

    if requests_per_account <= 0:
        raise ValueError("requests_per_account must be positive")
    return PROVIDER_LIMITS["day"] // requests_per_account


def reports_per_hour(requests_per_account: int = MEASURED_REQUESTS_PER_ACCOUNT) -> int:
    if requests_per_account <= 0:
        raise ValueError("requests_per_account must be positive")
    return PROVIDER_LIMITS["hour"] // requests_per_account


def depth_for_tier(tier: str) -> int:
    """Acquisition depth by product tier — the same for every tier.

    A function rather than a constant so that the one place a tier could ever
    change acquisition depth is a place with the decision written next to it.
    """

    if tier not in {"free", "paid"}:
        raise ValueError(f"unknown product tier {tier!r}")
    return FULL_DEPTH_MATCHES


__all__ = [
    "ACQUISITION_POLICY_VERSION",
    "FULL_DEPTH_MATCHES",
    "MATCHES_PER_REQUEST",
    "MEASURED_REQUESTS_PER_ACCOUNT",
    "PAID_MAY_ACQUIRE_MORE_THAN_FREE",
    "PERSISTENCE_REQUIREMENTS",
    "PROVIDER_LIMITS",
    "STORED_MATCH_TTL_DAYS",
    "AcquisitionPlan",
    "depth_for_tier",
    "plan",
    "reports_per_day",
    "reports_per_hour",
    "requests_for",
]
