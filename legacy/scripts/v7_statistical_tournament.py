#!/usr/bin/env python3
"""Run the V7 statistical feasibility tournament.

Three stages, in this order and no other:

    # 1. freeze the inference design, before any confirmation data is touched
    uv run python scripts/v7_statistical_tournament.py freeze-design \
        --out docs/evidence/v7-inference-design-2026-09-03.json

    # 2. everything that may be iterated on: DISCOVERY only
    uv run python scripts/v7_statistical_tournament.py discovery \
        --corpus-root <corpus> --design docs/evidence/v7-inference-design-2026-09-03.json \
        --out docs/evidence/v7-statistical-tournament-discovery-2026-09-03.json

    # 3. exactly one confirmation pass
    uv run python scripts/v7_statistical_tournament.py candidate-test \
        --corpus-root <corpus> --design docs/evidence/v7-inference-design-2026-09-03.json \
        --out docs/evidence/v7-statistical-tournament-candidate-test-2026-09-03.json

The confirmation stage refuses to run unless the frozen design file exists and
its digest still matches the code, and it appends one line to an access ledger
so the number of CANDIDATE_TEST reads is a fact on disk rather than a claim in
prose. ``CALIBRATION_RESERVED`` and ``SEALED_VALIDATION`` are unreachable from
here: ``corpus.iter_players`` fails closed on them.

No provider call of any kind is made by this script.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "legacy" / "services" / "api"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_API_ROOT = REPO_ROOT / "services" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from report_card.player_analysis_v7.research.corpus import (  # noqa: E402
    CANDIDATE_TEST,
    DISCOVERY,
    corpus_paths,
    manifest_digests,
    read_json,
)
from report_card.player_analysis_v7.research.features import (  # noqa: E402
    FEATURE_VERSION,
    load_frames,
)
from report_card.player_analysis_v7.research.inference import (  # noqa: E402
    INFERENCE_VERSION,
    design_digest,
    design_payload,
)
from report_card.player_analysis_v7.research.registry import (  # noqa: E402
    CANDIDATE_DEFINITION_VERSION,
    FAMILY_BY_NAME,
    REGISTRY_VERSION,
    digest,
    registry_payload,
)
from report_card.player_analysis_v7.research.screen import DEFAULT_SEED, spearman  # noqa: E402
from report_card.player_analysis_v7.research.tournament import (  # noqa: E402
    TOURNAMENT_VERSION,
    Denominators,
    agreement,
    collect,
    evaluate,
)
from report_card.player_analysis_v7.research.variants import (  # noqa: E402
    parsed_only,
    restrict_to_level,
    session_gap_override,
    volume_capped,
    without_non_chosen_hero_modes,
)
from report_card.player_analysis_v7.research.verdicts import (  # noqa: E402
    CONTROL_CHRONOLOGICAL_BAND,
    VERDICT_BY_FAMILY,
    VERDICT_VERSION,
    VERDICTS,
)

from legacy.scripts.v7_discovery_screen import FROZEN_SERIOUS_CANDIDATES  # noqa: E402

NEGATIVE_CONTROL = "side_sensitivity"
EVALUATED = (*FROZEN_SERIOUS_CANDIDATES, NEGATIVE_CONTROL)

#: Families whose estimand is about a hero the player chose. Single-draft and
#: random-draft matches do not offer that choice.
HERO_CHOICE_FAMILIES = (
    "hero_novelty",
    "post_loss_hero_switch",
    "transfer_risk",
    "transfer_activity",
)

#: Relaxed block geometry used only where two views are compared as point
#: estimates. No p-value from a relaxed run is read or reported.
DESCRIPTIVE_GEOMETRY = {"target_blocks": 20, "min_blocks": 4, "min_per_block": 25}

#: Session-gap thresholds swept against the 3-hour modelling choice.
SESSION_GAPS = (2 * 3600, 3 * 3600, 4 * 3600, 6 * 3600)

#: Families whose opportunity definition depends on the session boundary.
SESSION_FAMILIES = (
    "post_loss_session_continuation",
    "post_loss_hero_switch",
    "post_loss_requeue_latency",
    "position_flexibility",
)

#: Exposure cap for the volume-equalisation probe. It sits near the median of
#: product-context matches per account (526) and above the 400 opportunities the
#: level-family block geometry needs, so a player who survives the cap is still
#: information-eligible afterwards.
VOLUME_CAP = 500

LEDGER = REPO_ROOT / "docs" / "evidence" / "v7-candidate-test-access-ledger.jsonl"


def _repo_relative(path: Path) -> str:
    """Path relative to the repository root when it lies inside it, else as given."""

    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        return "unknown"




def denominators_for(frames: list[Any]) -> Denominators:
    return Denominators(
        sampled=len(frames),
        product_eligible=sum(1 for frame in frames if frame.rows),
        parsed_eligible=sum(1 for frame in frames if frame.parsed),
    )


def _volume_map(frames: list[Any]) -> dict[str, int]:
    return {frame.pseudonym: len(frame.rows) for frame in frames}


def _delta_volume_correlation(results: list[Any], volumes: dict[str, int]) -> float:
    import math

    pairs = [
        (math.log(max(volumes.get(r.pseudonym, 0), 1)), r.delta)
        for r in results
        if r.pseudonym in volumes
    ]
    if len(pairs) < 20:
        return float("nan")
    return spearman([p[0] for p in pairs], [p[1] for p in pairs])


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------


def stage_freeze_design(args: argparse.Namespace) -> int:
    payload = {
        "phase": "V7_LUNA_C_INFERENCE_DESIGN_FREEZE",
        "frozen_at_code_sha": git_sha(),
        "inference_version": INFERENCE_VERSION,
        "tournament_version": TOURNAMENT_VERSION,
        "feature_version": FEATURE_VERSION,
        "registry_version": REGISTRY_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "frozen_registry_digest": digest(registry_payload(FROZEN_SERIOUS_CANDIDATES)),
        "evaluated_families": list(EVALUATED),
        "negative_control": NEGATIVE_CONTROL,
        "seed": args.seed,
        "design": design_payload(),
        "design_digest": design_digest(),
        "declared_robustness_probes": {
            "hero_choice_draft_exclusion": list(HERO_CHOICE_FAMILIES),
            "session_gap_sweep_seconds": list(SESSION_GAPS),
            "session_gap_families": list(SESSION_FAMILIES),
            "volume_equalisation_cap": VOLUME_CAP,
            "hero_free_projection": ["transfer_risk", "transfer_activity"],
            "mode_split_agreement": ["duration_tempo"],
            "parsed_selection_probe": "history-only families recomputed on parsed matches only",
        },
        "candidate_test_passes_permitted": 1,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"design digest {payload['design_digest']}")
    return 0


def _check_design(path: str) -> dict[str, Any]:
    frozen = read_json(Path(path))
    if frozen["design_digest"] != design_digest():
        raise SystemExit(
            "frozen inference design does not match the code: "
            f"frozen {frozen['design_digest']} vs code {design_digest()}. "
            "Re-freezing after seeing data would break the confirmation discipline."
        )
    if frozen["frozen_registry_digest"] != digest(registry_payload(FROZEN_SERIOUS_CANDIDATES)):
        raise SystemExit("frozen candidate registry digest does not match the code")
    return frozen


def _evaluate_all(
    frames: list[Any],
    denominators: Denominators,
    split: str,
    seed: int,
    replicates: int,
) -> tuple[list[dict[str, Any]], dict[str, list[Any]]]:
    evaluations: list[dict[str, Any]] = []
    per_family_results: dict[str, list[Any]] = {}
    volumes = _volume_map(frames)
    for name in EVALUATED:
        family = FAMILY_BY_NAME[name]
        evaluation, results, _matrix = evaluate(
            name,
            family,
            frames,
            denominators,
            split=split,
            seed=seed,
            type_i_replicates=replicates,
        )
        row = evaluation.as_dict()
        row["delta_volume_spearman"] = _delta_volume_correlation(results, volumes)
        evaluations.append(row)
        per_family_results[name] = results
        print(
            f"  {name:32s} elig {evaluation.information_eligible:4d}"
            f"  q01 {evaluation.provisionally_qualified_01:4d}"
            f"  tau {evaluation.tau:.4f}"
            f"  chrono SB {evaluation.split_half_chrono_sb:+.3f}"
            f"  {evaluation.seconds:.0f}s",
            flush=True,
        )
    return evaluations, per_family_results


def _portfolio(per_family_results: dict[str, list[Any]], denominators: Denominators) -> dict[str, Any]:
    """How many of the frozen candidates each player provisionally qualifies for."""

    counts: dict[str, int] = {}
    for name, results in per_family_results.items():
        if name == NEGATIVE_CONTROL:
            continue
        for result in results:
            if result.p_value == result.p_value and result.p_value < 0.01:
                counts[result.pseudonym] = counts.get(result.pseudonym, 0) + 1
    histogram: dict[str, int] = {}
    for value in counts.values():
        histogram[str(value)] = histogram.get(str(value), 0) + 1
    zero = denominators.sampled - len(counts)
    histogram["0"] = histogram.get("0", 0) + zero
    at_least = {
        str(k): sum(1 for value in counts.values() if value >= k) for k in (1, 2, 3, 4, 5)
    }
    return {
        "histogram_of_qualified_findings_per_player": histogram,
        "players_with_at_least_k": at_least,
        "share_with_at_least_three_of_sampled": at_least["3"] / denominators.sampled,
        "share_with_at_least_three_of_product_eligible": (
            at_least["3"] / denominators.product_eligible if denominators.product_eligible else float("nan")
        ),
        "denominator_sampled": denominators.sampled,
        "denominator_product_eligible": denominators.product_eligible,
    }


def _redundancy(per_family_results: dict[str, list[Any]]) -> list[dict[str, Any]]:
    vectors = {
        name: {r.pseudonym: r.delta for r in results}
        for name, results in per_family_results.items()
        if name != NEGATIVE_CONTROL
    }
    out = []
    names = sorted(vectors)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            shared = sorted(set(vectors[left]) & set(vectors[right]))
            if len(shared) < 30:
                continue
            rho = spearman(
                [vectors[left][key] for key in shared],
                [vectors[right][key] for key in shared],
            )
            if rho == rho and abs(rho) >= 0.30:
                out.append({"left": left, "right": right, "players": len(shared), "spearman": rho})
    out.sort(key=lambda row: -abs(row["spearman"]))
    return out


def _probes(
    frames: list[Any],
    denominators: Denominators,
    seed: int,
    baseline: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """The declared robustness probes, all on DISCOVERY."""

    probes: list[dict[str, Any]] = []

    def run(name: str, label: str, **kwargs: Any) -> list[Any]:
        _evaluation, results, _matrix = evaluate(
            name,
            FAMILY_BY_NAME[name],
            frames,
            denominators,
            split=DISCOVERY,
            seed=seed,
            label=label,
            **kwargs,
        )
        return results

    # 1. Hero-choice families without single-draft and random-draft matches.
    trimmed = without_non_chosen_hero_modes(frames)
    for name in HERO_CHOICE_FAMILIES:
        evaluation, results, _m = evaluate(
            name,
            FAMILY_BY_NAME[name],
            trimmed,
            denominators,
            split=DISCOVERY,
            seed=seed,
            label="no_single_or_random_draft",
        )
        probes.append(
            {
                "probe": "draft_exclusion",
                "family": name,
                "agreement": agreement(baseline[name], results),
                "information_eligible": evaluation.information_eligible,
                "information_eligible_baseline": len(baseline[name]),
                "tau": evaluation.tau,
                "chronological_sb": evaluation.split_half_chrono_sb,
            }
        )
        print(f"  probe draft_exclusion {name}", flush=True)

    # 2. Session-gap sweep against the 3-hour modelling choice.
    for gap in SESSION_GAPS:
        if gap == 3 * 3600:
            continue
        with session_gap_override(gap):
            for name in SESSION_FAMILIES:
                evaluation, results, _m = evaluate(
                    name,
                    FAMILY_BY_NAME[name],
                    frames,
                    denominators,
                    split=DISCOVERY,
                    seed=seed,
                    label=f"session_gap_{gap // 3600}h",
                )
                probes.append(
                    {
                        "probe": "session_gap",
                        "family": name,
                        "gap_hours": gap // 3600,
                        "agreement": agreement(baseline[name], results),
                        "information_eligible": evaluation.information_eligible,
                        "information_eligible_baseline": len(baseline[name]),
                        "tau": evaluation.tau,
                        "chronological_sb": evaluation.split_half_chrono_sb,
                    }
                )
        print(f"  probe session_gap {gap // 3600}h", flush=True)

    # 3. Volume equalisation, aimed at hero_novelty.
    capped = volume_capped(frames, VOLUME_CAP)
    for name in ("hero_novelty", "duration_tempo"):
        evaluation, results, _m = evaluate(
            name,
            FAMILY_BY_NAME[name],
            capped,
            denominators,
            split=DISCOVERY,
            seed=seed,
            label=f"volume_capped_{VOLUME_CAP}",
            geometry_override=DESCRIPTIVE_GEOMETRY,
        )
        probes.append(
            {
                "probe": "volume_equalisation",
                "family": name,
                "cap": VOLUME_CAP,
                "geometry": "descriptive relaxation; point estimates only",
                "agreement": agreement(baseline[name], results),
                "information_eligible": evaluation.information_eligible,
                "information_eligible_baseline": len(baseline[name]),
                "tau": evaluation.tau,
                "delta_volume_spearman": _delta_volume_correlation(results, _volume_map(capped)),
                "chronological_sb": evaluation.split_half_chrono_sb,
            }
        )
        print(f"  probe volume_equalisation {name}", flush=True)

    # 4. Hero removed from the projection, for the Transfer families.
    for name in ("transfer_risk", "transfer_activity"):
        evaluation, results, _m = evaluate(
            name,
            FAMILY_BY_NAME[name],
            frames,
            denominators,
            split=DISCOVERY,
            seed=seed,
            label="hero_free_projection",
            drop_factors=("hero",),
        )
        probes.append(
            {
                "probe": "hero_free_projection",
                "family": name,
                "agreement": agreement(baseline[name], results),
                "information_eligible": evaluation.information_eligible,
                "tau": evaluation.tau,
                "tau_baseline_note": "compare with the primary evaluation's tau",
                "abs_delta_median": evaluation.abs_delta_median,
                "chronological_sb": evaluation.split_half_chrono_sb,
            }
        )
        print(f"  probe hero_free_projection {name}", flush=True)

    # 5. duration_tempo split by mode: is it a personal tempo or a mode mix?
    collected = collect("duration_tempo", frames)
    per_mode: dict[str, list[Any]] = {}
    for level in ("TURBO", "STANDARD"):
        subset = restrict_to_level(collected, "mode", level)
        evaluation, results, _m = evaluate(
            "duration_tempo",
            FAMILY_BY_NAME["duration_tempo"],
            frames,
            denominators,
            split=DISCOVERY,
            seed=seed,
            label=f"mode_{level}",
            per_player=subset,
            geometry_override=DESCRIPTIVE_GEOMETRY,
        )
        per_mode[level] = results
        probes.append(
            {
                "probe": "mode_split",
                "family": "duration_tempo",
                "mode": level,
                "geometry": "descriptive relaxation; point estimates only",
                "information_eligible": evaluation.information_eligible,
                "tau": evaluation.tau,
                "agreement_with_pooled": agreement(baseline["duration_tempo"], results),
            }
        )
    probes.append(
        {
            "probe": "mode_split_cross_agreement",
            "family": "duration_tempo",
            "detail": "Turbo-only against standard-only per-player estimates",
            "agreement": agreement(per_mode["TURBO"], per_mode["STANDARD"]),
        }
    )
    print("  probe mode_split duration_tempo", flush=True)

    # 6. Parsed-selection sensitivity for the history-only families.
    parsed_frames = parsed_only([frame for frame in frames if frame.parsed])
    parsed_denominators = Denominators(
        sampled=denominators.sampled,
        product_eligible=denominators.parsed_eligible,
        parsed_eligible=denominators.parsed_eligible,
    )
    for name in FROZEN_SERIOUS_CANDIDATES:
        if FAMILY_BY_NAME[name].parsed:
            continue
        evaluation, results, _m = evaluate(
            name,
            FAMILY_BY_NAME[name],
            parsed_frames,
            parsed_denominators,
            split=DISCOVERY,
            seed=seed,
            label="parsed_matches_only",
        )
        probes.append(
            {
                "probe": "parsed_selection",
                "family": name,
                "agreement": agreement(baseline[name], results),
                "information_eligible": evaluation.information_eligible,
                "denominator_parsed_accounts": denominators.parsed_eligible,
                "tau": evaluation.tau,
            }
        )
    print("  probe parsed_selection", flush=True)
    del run
    return probes


def stage_discovery(args: argparse.Namespace) -> int:
    frozen = _check_design(args.design)
    paths = corpus_paths(args.corpus_root)
    frames = load_frames(paths, frozenset({DISCOVERY}), with_parsed=True)
    denominators = denominators_for(frames)
    print(f"DISCOVERY frames {len(frames)}  product-eligible {denominators.product_eligible}")

    evaluations, results = _evaluate_all(
        frames, denominators, DISCOVERY, args.seed, args.replicates
    )
    probes = _probes(frames, denominators, args.seed, results) if not args.skip_probes else []

    document = {
        "phase": "V7_LUNA_C_STATISTICAL_TOURNAMENT_DISCOVERY",
        "split": DISCOVERY,
        "seed": args.seed,
        "code_sha": git_sha(),
        "feature_version": FEATURE_VERSION,
        "inference_version": INFERENCE_VERSION,
        "tournament_version": TOURNAMENT_VERSION,
        "registry_version": REGISTRY_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "frozen_registry_digest": digest(registry_payload(FROZEN_SERIOUS_CANDIDATES)),
        "design_digest": frozen["design_digest"],
        "corpus": manifest_digests(paths.root),
        "denominators": {
            "sampled": denominators.sampled,
            "product_eligible": denominators.product_eligible,
            "parsed_eligible": denominators.parsed_eligible,
        },
        "type_i_replicates": args.replicates,
        "evaluations": evaluations,
        "portfolio": _portfolio(results, denominators),
        "redundancy_spearman": _redundancy(results),
        "probes": probes,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


def stage_candidate_test(args: argparse.Namespace) -> int:
    frozen = _check_design(args.design)
    paths = corpus_paths(args.corpus_root)

    previous = 0
    if LEDGER.is_file():
        previous = sum(1 for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip())
    if previous >= frozen["candidate_test_passes_permitted"] and not args.acknowledge_repeat:
        raise SystemExit(
            f"CANDIDATE_TEST has already been read {previous} time(s); the frozen design permits "
            f"{frozen['candidate_test_passes_permitted']}. Refusing. A second pass would turn the "
            "confirmation split into a second discovery split."
        )

    frames = load_frames(paths, frozenset({CANDIDATE_TEST}), with_parsed=True)
    denominators = denominators_for(frames)
    print(
        f"CANDIDATE_TEST frames {len(frames)}  product-eligible {denominators.product_eligible}"
        f"  parsed {denominators.parsed_eligible}"
    )
    evaluations, results = _evaluate_all(
        frames, denominators, CANDIDATE_TEST, args.seed, args.replicates
    )

    document = {
        "phase": "V7_LUNA_C_STATISTICAL_TOURNAMENT_CANDIDATE_TEST",
        "split": CANDIDATE_TEST,
        "pass_number": previous + 1,
        "seed": args.seed,
        "code_sha": git_sha(),
        "feature_version": FEATURE_VERSION,
        "inference_version": INFERENCE_VERSION,
        "tournament_version": TOURNAMENT_VERSION,
        "frozen_registry_digest": digest(registry_payload(FROZEN_SERIOUS_CANDIDATES)),
        "design_digest": frozen["design_digest"],
        "corpus": manifest_digests(paths.root),
        "denominators": {
            "sampled": denominators.sampled,
            "product_eligible": denominators.product_eligible,
            "parsed_eligible": denominators.parsed_eligible,
        },
        "type_i_replicates": args.replicates,
        "evaluations": evaluations,
        "portfolio": _portfolio(results, denominators),
        "redundancy_spearman": _redundancy(results),
        "probes": [],
        "probe_policy": (
            "no robustness probe is run on CANDIDATE_TEST; every design decision was "
            "frozen on DISCOVERY and this stage only confirms"
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "read_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "pass_number": previous + 1,
                    "design_digest": frozen["design_digest"],
                    "code_sha": git_sha(),
                    "families": list(EVALUATED),
                    "output": _repo_relative(out),
                },
                sort_keys=True,
            )
            + "\n"
        )
    print(f"wrote {out}")
    print(f"CANDIDATE_TEST pass number {previous + 1}; ledger {LEDGER}")
    return 0


def stage_summarise(args: argparse.Namespace) -> int:
    """Join the graded verdicts to the measured numbers from both splits."""

    discovery = read_json(Path(args.discovery))
    confirmation = read_json(Path(args.candidate_test))
    d_by = {e["family"]: e for e in discovery["evaluations"]}
    c_by = {e["family"]: e for e in confirmation["evaluations"]}

    rows = []
    for verdict in VERDICTS:
        d = d_by[verdict.family]
        c = c_by[verdict.family]
        row = verdict.as_dict()
        row["discovery"] = {
            "structurally_eligible": d["structurally_eligible"],
            "information_eligible": d["information_eligible"],
            "provisionally_qualified_01": d["provisionally_qualified_01"],
            "provisionally_qualified_05": d["provisionally_qualified_05"],
            "reach_of_sampled": d["reach_of_sampled"],
            "reach_of_applicable": d["reach_of_applicable"],
            "obs_p25": d["obs_p25"],
            "obs_median": d["obs_median"],
            "obs_p75": d["obs_p75"],
            "tau": d["tau"],
            "i_squared": d["i_squared"],
            "shrinkage_p10": d["shrinkage_p10"],
            "shrinkage_median": d["shrinkage_median"],
            "shrinkage_p90": d["shrinkage_p90"],
            "shrinkage_reach_inflation": d["shrinkage_reach_inflation"],
            "split_half_chrono_sb": d["split_half_chrono_sb"],
            "split_half_random_sb": d["split_half_random_sb"],
            "mde_p25": d["mde_p25"],
            "mde_median": d["mde_median"],
            "mde_p75": d["mde_p75"],
            "delta_volume_spearman": d["delta_volume_spearman"],
            "variance_ratio": d["variance_ratio"],
            "eta2": d["eta2"],
            "type_i": d["type_i"],
        }
        row["candidate_test"] = {
            "structurally_eligible": c["structurally_eligible"],
            "information_eligible": c["information_eligible"],
            "provisionally_qualified_01": c["provisionally_qualified_01"],
            "reach_of_sampled": c["reach_of_sampled"],
            "reach_of_applicable": c["reach_of_applicable"],
            "tau": c["tau"],
            "i_squared": c["i_squared"],
            "split_half_chrono_sb": c["split_half_chrono_sb"],
            "type_i": c["type_i"],
        }
        rows.append(row)

    control_d = d_by[NEGATIVE_CONTROL]
    control_c = c_by[NEGATIVE_CONTROL]
    document = {
        "phase": "V7_LUNA_C_STATISTICAL_FEASIBILITY_TOURNAMENT",
        "verdict_version": VERDICT_VERSION,
        "inference_version": INFERENCE_VERSION,
        "tournament_version": TOURNAMENT_VERSION,
        "feature_version": FEATURE_VERSION,
        "registry_version": REGISTRY_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "frozen_registry_digest": digest(registry_payload(FROZEN_SERIOUS_CANDIDATES)),
        "design_digest": design_digest(),
        "code_sha": git_sha(),
        "seed": discovery["seed"],
        "corpus": discovery["corpus"],
        "candidate_test_passes_executed": confirmation["pass_number"],
        "denominators": {
            "discovery": discovery["denominators"],
            "candidate_test": confirmation["denominators"],
        },
        "negative_control": {
            "family": NEGATIVE_CONTROL,
            "discovery": {
                "information_eligible": control_d["information_eligible"],
                "provisionally_qualified_01": control_d["provisionally_qualified_01"],
                "provisionally_qualified_05": control_d["provisionally_qualified_05"],
                "tau": control_d["tau"],
                "i_squared": control_d["i_squared"],
                "split_half_chrono_sb": control_d["split_half_chrono_sb"],
                "type_i": control_d["type_i"],
            },
            "candidate_test": {
                "information_eligible": control_c["information_eligible"],
                "provisionally_qualified_01": control_c["provisionally_qualified_01"],
                "tau": control_c["tau"],
                "i_squared": control_c["i_squared"],
                "split_half_chrono_sb": control_c["split_half_chrono_sb"],
                "type_i": control_c["type_i"],
            },
            "chronological_noise_band": list(CONTROL_CHRONOLOGICAL_BAND),
        },
        "grades": {verdict.family: verdict.grade for verdict in VERDICTS},
        "decision_rows": rows,
        "portfolio": {
            "discovery": discovery["portfolio"],
            "candidate_test": confirmation["portfolio"],
        },
        "redundancy_spearman": discovery["redundancy_spearman"],
        "probes": discovery["probes"],
        "not_decided_in_this_phase": [
            "publication thresholds",
            "the final multiplicity family and q/alpha",
            "population percentiles",
            "the final five",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    for grade in ("A", "B", "C", "D"):
        names = [v.family for v in VERDICTS if v.grade == grade]
        print(f"  {grade}: {', '.join(names) if names else '-'}")
    assert set(VERDICT_BY_FAMILY) == set(FROZEN_SERIOUS_CANDIDATES)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)

    freeze = sub.add_parser("freeze-design")
    freeze.add_argument("--out", required=True)
    freeze.add_argument("--seed", type=int, default=DEFAULT_SEED)
    freeze.set_defaults(func=stage_freeze_design)

    for stage_name, handler in (("discovery", stage_discovery), ("candidate-test", stage_candidate_test)):
        stage = sub.add_parser(stage_name)
        stage.add_argument("--corpus-root", required=True)
        stage.add_argument("--design", required=True)
        stage.add_argument("--out", required=True)
        stage.add_argument("--seed", type=int, default=DEFAULT_SEED)
        stage.add_argument("--replicates", type=int, default=80)
        if stage_name == "discovery":
            stage.add_argument("--skip-probes", action="store_true")
        else:
            stage.add_argument("--acknowledge-repeat", action="store_true")
        stage.set_defaults(func=handler)

    summarise = sub.add_parser("summarise")
    summarise.add_argument("--discovery", required=True)
    summarise.add_argument("--candidate-test", required=True)
    summarise.add_argument("--out", required=True)
    summarise.set_defaults(func=stage_summarise)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
