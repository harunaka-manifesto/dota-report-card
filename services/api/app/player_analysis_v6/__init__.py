"""Free DNA v6 analytical core.

This package is intentionally parallel to the frozen v5 implementation.  The
single integration seam is :func:`analyze_free_dna_v6`; callers that need the
API boundary can use ``report.as_dict()`` or
:func:`build_free_dna_report_v6`.
"""

from .baselines import (
    BASELINE_HIERARCHY,
    BaselineCell,
    BaselineContext,
    BaselineResolution,
    BaselineResolver,
    resolve_baseline,
)
from .constants import (
    BOOTSTRAP_VERSION,
    DEFAULT_BOOTSTRAP_ITERATIONS,
    ELEMENTS_VERSION,
    FINDING_FAMILY_KEYS,
    FINDINGS_VERSION,
    PUBLIC_ELEMENT_KEYS,
    REPORT_VERSION,
    STORY_BEAT_KEYS,
    THRESHOLDS_VERSION,
)
from .costs import (
    assert_free_cost,
    free_cost_invariant,
    is_free_cost_compliant,
    new_free_cost_ledger,
)
from .elements import ELEMENT_DEFINITIONS, compute_elements, element_registry
from .findings import (
    FAMILY_DEFINITIONS,
    evaluate_families,
    forbidden_inference_violations,
    qualify_family,
    rank_findings,
)
from .identity import deterministic_identity, synthesize_identity
from .metrics import (
    ConsistencyComparison,
    MultiSignalComparison,
    compare_consistency_signals,
    compare_transfer_signals,
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
    shannon_effective_count,
)
from .models import (
    DiagnosticQuestion,
    ElementDefinition,
    ElementResult,
    ElementResultV6,
    Estimate,
    FindingFamilyResult,
    FindingResult,
    FreeCostLedger,
    FreeDnaReportV6,
    IdentitySummary,
    ShareCandidate,
    StoryBeat,
)
from .pipeline import (
    InsufficientHistoryError,
    analyze_free_dna_v6,
    assemble_v6_report,
    build_free_dna_report_v6,
)
from .statistics import (
    BootstrapResult,
    benjamini_hochberg,
    bootstrap_session_clusters,
    bootstrap_stability,
    clustered_bootstrap,
    session_clustered_bootstrap,
)
from .story import (
    assemble_nine_beat_story,
    assemble_story,
    build_diagnostic_questions,
    build_share_candidates,
)
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, classify_metric, threshold_for

__all__ = [
    "REPORT_VERSION",
    "ELEMENTS_VERSION",
    "FINDINGS_VERSION",
    "BOOTSTRAP_VERSION",
    "DEFAULT_BOOTSTRAP_ITERATIONS",
    "PUBLIC_ELEMENT_KEYS",
    "FINDING_FAMILY_KEYS",
    "STORY_BEAT_KEYS",
    "THRESHOLDS_VERSION",
    "BaselineContext",
    "BaselineCell",
    "BaselineResolution",
    "BaselineResolver",
    "BASELINE_HIERARCHY",
    "resolve_baseline",
    "Estimate",
    "ElementDefinition",
    "ElementResultV6",
    "ElementResult",
    "FindingFamilyResult",
    "FindingResult",
    "IdentitySummary",
    "DiagnosticQuestion",
    "StoryBeat",
    "ShareCandidate",
    "FreeCostLedger",
    "FreeDnaReportV6",
    "ELEMENT_DEFINITIONS",
    "element_registry",
    "compute_elements",
    "FAMILY_DEFINITIONS",
    "qualify_family",
    "evaluate_families",
    "rank_findings",
    "synthesize_identity",
    "deterministic_identity",
    "assemble_story",
    "assemble_nine_beat_story",
    "build_diagnostic_questions",
    "build_share_candidates",
    "shannon_effective_count",
    "involvement_per_minute",
    "finishing_share",
    "death_exposure_per_ten_minutes",
    "MultiSignalComparison",
    "ConsistencyComparison",
    "compare_transfer_signals",
    "compare_consistency_signals",
    "BootstrapResult",
    "clustered_bootstrap",
    "session_clustered_bootstrap",
    "bootstrap_session_clusters",
    "bootstrap_stability",
    "benjamini_hochberg",
    "MetricThreshold",
    "DEFAULT_THRESHOLDS",
    "threshold_for",
    "classify_metric",
    "new_free_cost_ledger",
    "free_cost_invariant",
    "assert_free_cost",
    "is_free_cost_compliant",
    "InsufficientHistoryError",
    "analyze_free_dna_v6",
    "assemble_v6_report",
    "build_free_dna_report_v6",
    "forbidden_inference_violations",
]
