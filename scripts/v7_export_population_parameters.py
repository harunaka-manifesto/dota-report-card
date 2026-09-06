#!/usr/bin/env python3
"""Freeze the population parameters the V7 runtime needs.

Every V7 analytical output is population-relative (see
``docs/architecture/v7-runtime-capability-payload.md`` section 1): a Finding's
``z`` needs ``mu`` and ``tau`` fitted across a cohort, its ``reliability``
needs ``tau`` and the dependence inflation ``D``; a recommendation's
standardized gap divides by the dimension's pooled scale; archetype axes are
cut at population quantiles within a mode stratum. A runtime request has
**one** player and cannot fit a population, so the runtime loads parameters
frozen once and shipped with the app.

**Source of truth: the committed evidence documents, not a fresh fit.** The
three evidence JSONs under ``docs/evidence/`` are the reviewed, published
output of the research phase; they already carry every parameter the runtime
needs. Deriving the artifact from them rather than refitting means the runtime
uses exactly the numbers that were reviewed, and that the artifact can be
rebuilt on any checkout without the multi-gigabyte corpus being present.

That last property stopped being theoretical on 2026-09-07, when the Pass-1
history corpus was lost from a ``/private/tmp`` worktree
(``docs/evidence/v7-corpus-loss-2026-09-07.md``). The published parameters
survived because they were committed; the corpus did not.

Each source document's SHA-256 is recorded in the artifact, so a parameter can
always be traced back to the evidence that established it, and a silently
edited evidence file changes the digest.

Reads no corpus. Makes no provider call. Touches no reserved split.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from app.player_analysis_v7.research.archetype import (  # noqa: E402
    ARCHETYPE_VERSION,
    MODE_STRATA,
)
from app.player_analysis_v7.research.owner_decisions import DECISIONS_VERSION  # noqa: E402
from app.player_analysis_v7.research.ranking import RANKING_MODEL_VERSION  # noqa: E402
from app.player_analysis_v7.research.recommendation import (  # noqa: E402
    RECOMMENDATION_VERSION,
)

POPULATION_PARAMETERS_VERSION = "v7-population-parameters-1.0.0"

#: How these numbers came to be, stated on the artifact and on every entry in
#: it. They are a *transcription* of the reviewed DISCOVERY evidence, not a
#: fresh population fit, and the distinction is load-bearing: the Pass-1 source
#: corpus no longer exists, so those fits cannot be re-derived from source
#: (docs/evidence/v7-corpus-loss-incident-2026-09-07.md). Describing them as a
#: fresh fit would claim a reproducibility the repository does not have.
DERIVATION_METHOD = "DERIVED FROM COMMITTED DISCOVERY EVIDENCE — NOT REFIT FROM SOURCE CORPUS"

EVIDENCE = REPO_ROOT / "docs" / "evidence"
PIPELINE_EVIDENCE = EVIDENCE / "v7-finding-pipeline-2026-09-05.json"
RECOMMENDATION_EVIDENCE = EVIDENCE / "v7-recommendation-selection-2026-09-06.json"
ARCHETYPE_EVIDENCE = EVIDENCE / "v7-archetype-axes-2026-09-06.json"

#: The six cuts an archetype stratum needs, named so a missing one fails loudly
#: rather than defaulting.
ARCHETYPE_CUT_KEYS = (
    "tempo_low",
    "tempo_high",
    "participation_low",
    "deaths_median",
    "lighthouse_cut",
    "closer_cut",
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_finding_dimensions() -> dict[str, Any]:
    """Per Finding dimension: the population fit the ranking model divides by.

    Withheld dimensions are included with ``ships: false`` rather than omitted.
    The runtime needs to know they exist and are deliberately silent, so that a
    dimension appearing in a payload can be rejected as a defect instead of
    passing unnoticed as an unknown key.
    """

    pipeline = _read(PIPELINE_EVIDENCE)
    source_document = str(PIPELINE_EVIDENCE.relative_to(REPO_ROOT))
    source_sha = _digest(PIPELINE_EVIDENCE)
    out: dict[str, Any] = {}
    for key, row in sorted(pipeline["dimensions"].items()):
        tau = row.get("tau")
        if tau is None:
            raise SystemExit(f"{key}: evidence carries no tau; cannot freeze a parameter set")
        ships = tau > 0.0
        entry: dict[str, Any] = {
            "mu": row["mu"],
            "tau": tau,
            "dependence_inflation": row["dependence_inflation"],
            "dependence_batch_length": row.get("dependence_batch_length"),
            "dependence_curve_plateaued": row.get("dependence_curve_plateaued"),
            "reliability_is_upper_bound": not row.get("dependence_curve_plateaued", True),
            "section": row["section"],
            "source_pass": row["source"],
            "players_fitted": row["players"],
            "ships": ships,
            "status": "shipping" if ships else "withheld",
            "negative_control": bool(row.get("negative_control")),
            "derivation_method": DERIVATION_METHOD,
            "source_evidence_document": source_document,
            "source_evidence_sha256": source_sha,
            "source_analytical_version": pipeline["ranking_model_version"],
            "source_inference_version": pipeline["inference_version"],
            "source_feature_version": (
                pipeline["pass2_feature_version"]
                if row["source"] == "pass2"
                else pipeline["feature_version"]
            ),
            "source_reproducible": row["source"] == "pass2",
            "source_reproducibility_note": (
                "Pass-2 corpus intact; canonical is re-derivable from normalized."
                if row["source"] == "pass2"
                else "Pass-1 history corpus permanently unavailable "
                "(docs/evidence/v7-corpus-loss-incident-2026-09-07.md); auditable "
                "but not source-reproducible."
            ),
        }
        if not ships:
            entry["withheld_reason"] = (
                "negative control; a deliberate placebo whose silence is the "
                "evidence that the estimator does not manufacture Findings"
                if entry["negative_control"]
                else "tau collapsed to zero: no measurable between-player signal"
            )
        out[key] = entry
    return out


def build_recommendation_dimensions() -> dict[str, Any]:
    """Per recommendation dimension: the scale the personal gap divides by.

    Note this is the dimension's own pooled match-to-match spread, never the
    between-player spread of gaps -- that is exactly zero everywhere, and
    dividing by it would silence the section entirely. See
    ``docs/evidence/v7-cut-point-calibration-dry-run-2026-09-06.md``.
    """

    evidence = _read(RECOMMENDATION_EVIDENCE)
    source_document = str(RECOMMENDATION_EVIDENCE.relative_to(REPO_ROOT))
    source_sha = _digest(RECOMMENDATION_EVIDENCE)
    out: dict[str, Any] = {}
    for key, row in sorted(evidence["dimensions"].items()):
        scale = row.get("dimension_scale")
        if scale is None or scale <= 0.0:
            raise SystemExit(f"{key}: recommendation evidence carries no usable scale")
        out[key] = {
            "dimension_scale": scale,
            "dependence_inflation": row["dependence_inflation"],
            "modal_sign_share": row["modal_sign_share"],
            "eligible": bool(row["eligible"]),
            "status": "eligible" if row["eligible"] else "excluded",
            "outcome_contaminated": bool(row.get("outcome_contaminated")),
            "derivation_method": DERIVATION_METHOD,
            "source_evidence_document": source_document,
            "source_evidence_sha256": source_sha,
            "source_analytical_version": evidence["recommendation_version"],
            "source_reproducible": True,
        }
    return out


def build_archetype_cuts() -> dict[str, Any]:
    """Per mode stratum: the quantile cuts each archetype axis is read against.

    Stratified because a mode-blind axis measures the queue rather than the
    player: the fixed-window tempo candidate correlated 0.889 with a player's
    turbo share.
    """

    evidence = _read(ARCHETYPE_EVIDENCE)
    cuts = evidence["population_cuts_by_stratum"]
    out: dict[str, Any] = {}
    for stratum in MODE_STRATA:
        if stratum not in cuts:
            raise SystemExit(f"archetype evidence has no cuts for stratum {stratum!r}")
        row = cuts[stratum]
        missing = [name for name in ARCHETYPE_CUT_KEYS if row.get(name) is None]
        if missing:
            raise SystemExit(f"stratum {stratum!r} is missing cuts {missing!r}")
        out[stratum] = {name: row[name] for name in ARCHETYPE_CUT_KEYS}
    return out


def build_document() -> dict[str, Any]:
    pipeline = _read(PIPELINE_EVIDENCE)
    archetype = _read(ARCHETYPE_EVIDENCE)
    recommendation = _read(RECOMMENDATION_EVIDENCE)

    findings = build_finding_dimensions()
    return {
        "schema_version": POPULATION_PARAMETERS_VERSION,
        "fitted_on_split": "DISCOVERY",
        "derivation_method": DERIVATION_METHOD,
        "refit_from_source_corpus": False,
        "provenance_note": (
            "Every parameter is transcribed from a committed evidence document "
            "and carries that document's path, SHA-256 and analytical version. "
            "Pass-1 parameters are auditable but not source-reproducible: the "
            "Pass-1 history corpus was lost on 2026-09-07 "
            "(docs/evidence/v7-corpus-loss-incident-2026-09-07.md)."
        ),
        "production_certified": False,
        "validation_status": "development",
        "source_code_sha": _git_sha(),
        "source_evidence": {
            "finding_pipeline": {
                "path": str(PIPELINE_EVIDENCE.relative_to(REPO_ROOT)),
                "sha256": _digest(PIPELINE_EVIDENCE),
            },
            "recommendation_selection": {
                "path": str(RECOMMENDATION_EVIDENCE.relative_to(REPO_ROOT)),
                "sha256": _digest(RECOMMENDATION_EVIDENCE),
            },
            "archetype_axes": {
                "path": str(ARCHETYPE_EVIDENCE.relative_to(REPO_ROOT)),
                "sha256": _digest(ARCHETYPE_EVIDENCE),
            },
        },
        "model_versions": {
            "ranking": RANKING_MODEL_VERSION,
            "recommendation": RECOMMENDATION_VERSION,
            "archetype": ARCHETYPE_VERSION,
            "owner_decisions": DECISIONS_VERSION,
        },
        "denominators": {
            "pass1_discovery_players": pipeline["denominators"]["pass1_discovery_players"],
            "pass2_discovery_players": pipeline["denominators"]["pass2_discovery_players"],
            "players_with_any_finding": pipeline["denominators"]["players_with_any_finding"],
            "archetype_joinable_players": archetype["denominators"]["joinable_players"],
            "recommendation_players": recommendation["denominators"][
                "players_with_at_least_one_candidate"
            ],
        },
        "finding_dimensions": findings,
        "recommendation_dimensions": build_recommendation_dimensions(),
        "archetype_cuts": build_archetype_cuts(),
    }


def _serialize(document: dict[str, Any]) -> str:
    serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if "v7p_" in serialized:
        raise SystemExit("a corpus account identifier reached the population parameters")
    return serialized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(
            REPO_ROOT
            / "services"
            / "api"
            / "app"
            / "player_analysis_v7"
            / "data"
            / "population-parameters-1.0.0.json"
        ),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    serialized = _serialize(build_document())
    out = Path(args.out)
    if args.check:
        if not out.exists() or out.read_text(encoding="utf-8") != serialized:
            print(f"{out} is stale; regenerate with scripts/v7_export_population_parameters.py")
            return 1
        print("population parameters are current")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialized, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
