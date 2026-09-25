"""The owner's nine V7 selections, recorded so code can be checked against them.

`legacy/docs/evidence/v7-owner-selection-packet-2026-09-06.md` put nine decisions to
the owner; this is what came back, on 2026-09-06. It is a record, not a
mechanism — nothing here computes anything. Its job is to give the tests a
single place to compare the implementation against, so a constant cannot drift
away from the decision it implements without something failing.

Where a decision is "keep what is already there", the record still names it.
A behaviour that happens to match a decision by accident is one refactor away
from silently violating it, and "already true" is exactly the kind of
implementation nobody writes a test for.

Two decisions (D2, D7) are settled in principle and await calibration against
CALIBRATION_RESERVED. They are recorded here with their provisional values and
a flag saying the value is not final.

SEALED_VALIDATION stays untouched. The owner's instruction is explicit and
carries past this phase: it is opened only on their express approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DECISIONS_VERSION = "v7-owner-decisions-2026-09-06b"

DECIDED_ON = "2026-09-06"


@dataclass(frozen=True)
class Decision:
    """One owner selection.

    ``provisional`` marks a value the owner chose to carry *for now*, pending
    calibration. ``carries_forward`` records a sensitivity or caveat the owner
    asked to be tracked rather than absorbed.
    """

    key: str
    question: str
    choice: str
    summary: str
    provisional: bool = False
    needs_calibration_reserved: bool = False
    carries_forward: tuple[str, ...] = field(default_factory=tuple)


DECISIONS: dict[str, Decision] = {
    decision.key: decision
    for decision in (
        Decision(
            "D1",
            "Does a score line gate what the reader sees?",
            "c",
            "Always show at least three Findings; apply the score gate to slots four "
            "and five only.",
        ),
        Decision(
            "D2",
            "What do the strength bands mean?",
            "c",
            "Drop the slight / moderate / pronounced bands entirely. A Finding "
            "carries direction, score and a shrunk estimate with an interval, and "
            "no adjective. CALIBRATION_RESERVED is not spent on this.",
            carries_forward=(
                "Revised from an earlier choice of absolute cut points, on "
                "measurement. Over 4,983 player-Findings the best cut points that "
                "keep all three bands populated leave 65.2% with a 95% interval "
                "straddling a band boundary: a typical interval on |z| * reliability "
                "is about 0.6 wide while three populated bands need cuts about 0.5 "
                "apart. The interval is wider than the band, and because it is "
                "dominated by within-player measurement error, more accounts cannot "
                "narrow it. See "
                "legacy/docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.md.",
            ),
        ),
        Decision(
            "D3",
            "Where the outcome-contamination screen cuts",
            "a",
            "Keep the modal-sign cut at 0.95.",
            carries_forward=(
                "last_hits_at_ten sits at 0.9466, four thousandths inside the cut, and "
                "wins 51% of recommendation slots. The owner asked for this sensitivity "
                "to be carried explicitly through calibration and final validation "
                "rather than absorbed.",
            ),
        ),
        Decision(
            "D4",
            "Which dimensions ship",
            "a",
            "Ship all sixteen dimensions carrying between-player signal. Reliability "
            "shrinkage is the only gate; no second hard reliability cutoff.",
        ),
        Decision(
            "D5",
            "Three tempo levels, or fewer",
            "a",
            "Keep early / mid / late.",
            carries_forward=(
                "Copy must present tempo as a relative tendency within the player's "
                "dominant mode stratum, not a large behavioural difference. Within a "
                "stratum the terciles sit 0.015-0.018 apart on a p5-p95 range of "
                "about 0.075.",
            ),
        ),
        Decision(
            "D6",
            "Do the two special archetypes ship?",
            "a",
            "Ship The Lighthouse and The Closer. Both stay positive and shareable.",
            provisional=True,
            carries_forward=(
                "The 98th-percentile cut is corpus-relative. With both reserved "
                "splits staying untouched it is fixed for the pilot and refreshed "
                "from real pilot data, not from a reserved split.",
            ),
        ),
        Decision(
            "D7",
            "Minimum matches per arm for a recommendation",
            "a",
            "Keep fifteen per arm. Settled by the DISCOVERY sensitivity sweep; "
            "CALIBRATION_RESERVED is not spent on this.",
            carries_forward=(
                "Sweeping the minimum from 10 to 30 moves median gap reliability "
                "from 0.981966 to 0.982515 while coverage falls from 265 players to "
                "258. The threshold does not bind anywhere in the range worth "
                "considering, so 15 stands because the curve is flat, not because "
                "15 was fitted.",
            ),
        ),
        Decision(
            "D8",
            "Which reserved split gets spent",
            "a",
            "Spend CALIBRATION_RESERVED on calibration. SEALED_VALIDATION stays "
            "untouched and is opened only on the owner's express approval.",
        ),
        Decision(
            "D9",
            "The parsed-match budget in production",
            "a",
            "Full-depth acquisition for every pilot user. Persist the acquired and "
            "derived data so repeat report generation, account creation and paid "
            "output all reuse it rather than refetching. Paid quality must not depend "
            "on having analysed more matches during the pilot.",
            carries_forward=(
                "Revisit acquisition depth only if real demand approaches provider capacity.",
            ),
        ),
    )
}

#: Decisions whose values are not final. After the 2026-09-06 update only the
#: archetype special cut remains open, and it is refreshed from pilot data
#: rather than from a reserved split.
PROVISIONAL = tuple(key for key, d in DECISIONS.items() if d.provisional)

#: Decisions still requiring a reserved split. Empty, and that is the point:
#: the owner closed D2 and D7 on DISCOVERY evidence, so no remaining decision
#: has a claim on CALIBRATION_RESERVED.
NEEDS_RESERVED_SPLIT = tuple(
    key for key, d in DECISIONS.items() if d.needs_calibration_reserved
)

#: Sensitivities and caveats the owner asked to be tracked rather than absorbed.
CARRIED_FORWARD: dict[str, tuple[str, ...]] = {
    key: d.carries_forward for key, d in DECISIONS.items() if d.carries_forward
}

#: Neither reserved split is spent. The owner closed D2 and D7 without one and
#: instructed that both stay untouched.
CALIBRATION_RESERVED_SPENT = False

#: Not a decision the owner delegated. Recorded as a constant so that any code
#: path that would read the sealed split has something unambiguous to fail
#: against.
SEALED_VALIDATION_APPROVED = False


__all__ = [
    "CALIBRATION_RESERVED_SPENT",
    "CARRIED_FORWARD",
    "DECIDED_ON",
    "DECISIONS",
    "DECISIONS_VERSION",
    "NEEDS_RESERVED_SPLIT",
    "PROVISIONAL",
    "SEALED_VALIDATION_APPROVED",
    "Decision",
]
