"""Machine-readable evidence and product capability tiers."""

from typing import Literal

EvidenceTier = Literal["summary_history", "match_detail", "parsed_replay"]
ProductTier = Literal["free", "paid"]
ModelStatus = Literal["active", "planned", "legacy"]
DataCapability = str

SUMMARY_CAPABILITIES = frozenset(
    {
        "summary.hero",
        "summary.outcome",
        "summary.kda",
        "summary.time",
        "summary.role_hint",
        "summary.party",
        "summary.chronology",
        "hero.taxonomy",
        "hero.knowledge",
    }
)

DEEP_CAPABILITIES = frozenset(
    {
        "detail.economy",
        "detail.items",
        "parsed.teamfights",
        "parsed.objectives",
        "parsed.vision",
        "parsed.position",
        "parsed.timelines",
    }
)


def capability_supported_by_free(capability: str) -> bool:
    """Return whether a capability is available from the bounded summary read."""

    return capability in SUMMARY_CAPABILITIES
