"""The owner's nine V7 selections, recorded so code can be checked against them.

`docs/evidence/v7-owner-selection-packet-2026-09-06.md` put nine decisions to
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

DECISIONS_VERSION = "v7-owner-decisions-2026-09-06"

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
            "b",
            "Absolute cut points on |z| * reliability, not population terciles. Final "
            "cut points fitted against CALIBRATION_RESERVED.",
            provisional=True,
            needs_calibration_reserved=True,
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
            needs_calibration_reserved=True,
            carries_forward=(
                "The 98th-percentile cut is corpus-relative and is refreshed during calibration.",
            ),
        ),
        Decision(
            "D7",
            "Minimum matches per arm for a recommendation",
            "a",
            "Keep fifteen per arm for now; use CALIBRATION_RESERVED to decide whether "
            "it should move.",
            provisional=True,
            needs_calibration_reserved=True,
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

#: Decisions whose values are not final until calibration lands.
PROVISIONAL = tuple(key for key, d in DECISIONS.items() if d.provisional)

#: Sensitivities and caveats the owner asked to be tracked rather than absorbed.
CARRIED_FORWARD: dict[str, tuple[str, ...]] = {
    key: d.carries_forward for key, d in DECISIONS.items() if d.carries_forward
}

#: Not a decision the owner delegated. Recorded as a constant so that any code
#: path that would read the sealed split has something unambiguous to fail
#: against.
SEALED_VALIDATION_APPROVED = False


__all__ = [
    "CARRIED_FORWARD",
    "DECIDED_ON",
    "DECISIONS",
    "DECISIONS_VERSION",
    "PROVISIONAL",
    "SEALED_VALIDATION_APPROVED",
    "Decision",
]
