"""Frozen vocabulary and version identifiers for Free DNA v6.

The v6 package deliberately has its own names.  None of these values are
aliases to the v5 Element or Pattern registries; keeping the vocabulary local
lets historical v5 snapshots remain readable when the public contract evolves.
"""

from __future__ import annotations

REPORT_VERSION = "free-dna-report-6.0.0"
ELEMENTS_VERSION = "free-elements-6.0.0"
FINDINGS_VERSION = "free-findings-6.0.0"
EXPRESSION_VERSION = "summary-expression-multisignal-1.0.0"
BOOTSTRAP_VERSION = "stats-cluster-bootstrap-1.0.0"
BASELINE_VERSION = "context-baseline-2.0.0"
THRESHOLDS_VERSION = "metric-thresholds-6.0.0"
CLAIM_VERSION = "claim-contract-1.0.0"
STORY_VERSION = "free-story-6.0.0"
SEMANTIC_COPY_VERSION = "free-dna-semantic-copy-6.0.0"
DIAGNOSTICS_VERSION = "deep-diagnostics-2.0.0"
SHARE_VERSION = "share-svg-6.0.0"
INTERACTION_VERSION = "report-interactions-1.0.0"

STATS_BOOTSTRAP_METHOD = "clustered-bca-approximation-1.0.0"
DEFAULT_BOOTSTRAP_ITERATIONS = 2_000
BOOTSTRAP_CONFIDENCE_LEVEL = 0.95
FDR_Q = 0.05

MIN_ELIGIBLE_MATCHES = 30
NORMAL_REPORT_MATCHES = 60
MIN_STABLE_SESSIONS = 8
MIN_CONSISTENCY_SESSIONS = 12

# Public identity Elements.  Lane context, familiarity, post-loss tempo,
# drift, and form remain supporting evidence and are intentionally absent.
PUBLIC_ELEMENT_KEYS = (
    "breadth",
    "toolkit",
    "involvement",
    "finishing",
    "death_exposure",
    "transfer",
    "consistency",
)

FINDING_FAMILY_KEYS = (
    "pool_shape",
    "transfer",
    "post_loss_response",
    "combat_expression",
    "session_drift",
)

STORY_BEAT_KEYS = (
    "self_estimate",
    "identity_reveal",
    "pool_prediction",
    "combat_expression",
    "strongest_finding",
    "secondary_finding",
    "recommendation",
    "hero_mirror",
    "deep_fork",
)

SUPPORTED_LANE_CONTEXTS = frozenset(
    {"carry", "mid", "offlane", "roamer", "safe_lane", "mid_lane", "off_lane", "unknown"}
)

# Public language guards.  These are also used by the tiny forbidden-inference
# checker in :mod:`findings` and are intentionally conservative.
FORBIDDEN_FREE_TERMS = (
    "position 1",
    "position 2",
    "position 3",
    "position 4",
    "position 5",
    "pos1",
    "pos2",
    "pos3",
    "pos4",
    "pos5",
    "aggression",
    "aggressive",
    "tilt",
    "fatigue",
    "warm-up",
    "warm up",
    "intention",
    "intent",
    "positioning",
    "fight entry",
    "death quality",
    "objective conversion",
    "item timing",
    "personality",
    "skill",
    "because",
    "causes",
    "causal",
    "causality",
    "mmr",
)
