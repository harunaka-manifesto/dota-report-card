#!/usr/bin/env python3
"""Offline V6.1 suppression trace; never loads a provider client."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

import app.reports.dna_assembly_v61 as assembly  # noqa: E402
from app.analysis.budget import DataCostLedger  # noqa: E402
from app.api.report_schemas_v61 import validate_free_dna_report_v61  # noqa: E402
from app.player_analysis_v61.artifacts import load_v61_artifact_bundle  # noqa: E402
from app.player_analysis_v61.calibration_corpus import (  # noqa: E402
    canonical_history,
    load_canonical_corpus,
)
from app.player_analysis_v61.corpus_reuse import profile_digest, sha256_file  # noqa: E402
from app.player_analysis_v61.legacy_adapter import current_taxonomy_mapping  # noqa: E402
from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY  # noqa: E402
from app.player_analysis_v61.versions import MODEL_VERSION  # noqa: E402

FAMILIES = ("pool_shape", "transfer", "post_loss_response", "combat_expression", "session_drift")
Q_GRID = (0.01, 0.025, 0.05, 0.075, 0.10)

_ROWS: dict[str, list[dict[str, Any]]] = {}
_COMPLETION: dict[str, dict[str, bool]] = {}
_BUNDLE: Any = None
_TAXONOMY: Any = None
_SUPPORTING: dict[str, Any] = {}
_BASE_REPORT: dict[str, Any] | None = None


def _stable_account_id(profile_id: str) -> int:
    return int.from_bytes(hashlib.sha256(("v61-eval:" + profile_id).encode()).digest()[:4], "big")


def _bh(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    result: dict[str, float] = {}
    running = 1.0
    for reverse_index, (key, value) in enumerate(reversed(ordered), start=1):
        rank = len(ordered) - reverse_index + 1
        running = min(running, float(value) * len(ordered) / max(1, rank))
        result[key] = max(0.0, min(1.0, running))
    return result


def _q(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p10": None, "p50": None, "p90": None, "min": None, "max": None}
    ordered = sorted(float(value) for value in values)
    def percentile(fraction: float) -> float:
        position = (len(ordered) - 1) * fraction
        low, high = math.floor(position), math.ceil(position)
        if low == high:
            return ordered[low]
        return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
    return {
        "p10": percentile(0.10), "p50": percentile(0.50), "p90": percentile(0.90),
        "min": ordered[0], "max": ordered[-1],
    }


def _num(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _write_json(path: Path, value: Any, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    finally:
        if os.path.exists(temporary):
            os.chmod(temporary, mode)
    os.replace(temporary, path)
    path.chmod(mode)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
    finally:
        if os.path.exists(temporary):
            os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    path.chmod(0o600)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    temporary = path.with_name(f".{path.name}.tmp")
    fields = [
        "profile_digest", "family", "history_matches", "history_sessions", "data_eligible",
        "minimum_support", "base_status", "base_published", "family_raw_p", "family_q",
        "family_qualified", "branch_key", "branch_raw_p", "branch_q", "branch_qualified",
        "final_published", "surfaced",
    ]
    with temporary.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.chmod(0o600)
    os.replace(temporary, path)
    path.chmod(0o600)


def _install_offline_guard() -> None:
    import httpx

    def blocked(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("offline autopsy attempted an HTTP request")

    httpx.Client.request = blocked  # type: ignore[method-assign]
    httpx.Client.send = blocked  # type: ignore[method-assign]
    httpx.AsyncClient.request = blocked  # type: ignore[method-assign]
    httpx.AsyncClient.send = blocked  # type: ignore[method-assign]


def _install_base_capture() -> None:
    if getattr(assembly, "_AUTOPSY_BASE_CAPTURED", False):
        return
    original = assembly.assemble_free_dna_report_v6

    def captured(**kwargs: Any) -> dict[str, Any]:
        global _BASE_REPORT
        result = original(**kwargs)
        _BASE_REPORT = result
        return result

    assembly.assemble_free_dna_report_v6 = captured  # type: ignore[assignment]
    assembly._AUTOPSY_BASE_CAPTURED = True


def _init_worker() -> None:
    _install_offline_guard()
    _install_base_capture()


def _surface_counts(report: dict[str, Any], family: str) -> dict[str, Any]:
    questions = sum(
        str(item.get("finding_family")) == family
        for item in report.get("diagnostic_questions", ())
        if isinstance(item, dict)
    )
    shares = sum(
        str(item.get("id", "")) == f"finding:{family}" and item.get("eligible") is True
        for item in report.get("share_candidates", ())
        if isinstance(item, dict)
    )

    def has_family(value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("family") == family or value.get("finding_family") == family:
                return True
            return any(has_family(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(has_family(child) for child in value)
        return False

    pages = sum(
        bool(page.get("available")) and has_family(page)
        for page in report.get("pages", ())
        if isinstance(page, dict)
    )
    return {
        "diagnostic_questions": int(questions),
        "finding_share_cards": int(shares),
        "finding_pages": int(pages),
        "surface_count": int(questions + shares + pages),
        "surfaced": bool(questions + shares + pages),
    }


def _support(
    family: str,
    matches: list[Any],
    evidence: dict[str, Any],
    base_finding: dict[str, Any],
) -> dict[str, Any]:
    portfolio = evidence.get("portfolio_shape", {})
    sessions = len({_stable_session(row, index) for index, row in enumerate(matches)})
    minimum_opportunities = 30
    minimum_sessions = 12
    if family == "pool_shape":
        opportunities = _int(portfolio.get("match_count", len(matches)))
        return {
            "opportunities": opportunities,
            "sessions": sessions,
            "minimum_opportunities": minimum_opportunities,
            "minimum_sessions": minimum_sessions,
            "runtime_support_pass": opportunities >= 30 and sessions >= 12,
            "semantic_contract_support_pass": opportunities >= 30 and sessions >= 12,
            "robustness": {"taxonomy_stable": bool(portfolio.get("taxonomy_sensitivity", {}).get("stable"))},
        }
    if family == "transfer":
        band = evidence.get("transfer_frontier", {}).get("bands", {}).get("reliable_stretch", {})
        opportunities = _int(band.get("match_count"))
        band_sessions = _int(band.get("sessions"))
        return {
            "opportunities": opportunities,
            "sessions": band_sessions,
            "minimum_opportunities": minimum_opportunities,
            "minimum_sessions": minimum_sessions,
            "runtime_support_pass": bool(band.get("supported")),
            "semantic_contract_support_pass": opportunities >= 30 and band_sessions >= 12,
            "robustness": {
                "cross_fitted": bool(evidence.get("transfer_frontier", {}).get("cross_fitted")),
                "frontier": evidence.get("transfer_frontier", {}).get("frontier"),
                "equivalent_components": band.get("equivalent", {}),
            },
        }
    if family == "post_loss_response":
        response = evidence.get("result_response", {})
        states = response.get("states", {})
        opportunities = _int(response.get("transition_count"))
        state_sessions = [_int(item.get("sessions")) for item in states.values() if isinstance(item, dict)]
        return {
            "opportunities": opportunities,
            "sessions": max(state_sessions, default=0),
            "minimum_opportunities": minimum_opportunities,
            "minimum_sessions": minimum_sessions,
            "runtime_support_pass": opportunities >= 30 and any(item.get("available") for item in states.values()),
            "semantic_contract_support_pass": opportunities >= 30 and max(state_sessions, default=0) >= 12,
            "state_opportunities": {key: _int(item.get("opportunities")) for key, item in states.items()},
            "state_sessions": {key: _int(item.get("sessions")) for key, item in states.items()},
            "robustness": {
                "cross_session_transitions": _int(response.get("cross_session_transitions")),
                "control_reuse": response.get("control_reuse"),
            },
        }
    if family == "combat_expression":
        involvement = evidence.get("involvement", {})
        death = evidence.get("death_exposure", {})
        opportunities = min(_int(involvement.get("matches")), _int(death.get("matches")))
        family_sessions = min(_int(involvement.get("sessions")), _int(death.get("sessions")))
        return {
            "opportunities": opportunities,
            "sessions": family_sessions,
            "minimum_opportunities": minimum_opportunities,
            "minimum_sessions": minimum_sessions,
            "runtime_support_pass": opportunities >= 30 and family_sessions >= 8,
            "semantic_contract_support_pass": opportunities >= 30 and family_sessions >= 12,
            "robustness": {
                "involvement_coverage": _num(involvement.get("coverage")),
                "death_coverage": _num(death.get("coverage")),
                "overdispersion": death.get("overdispersion"),
            },
        }
    curve = evidence.get("session_curve", {})
    positions = curve.get("positions", {})
    observed = [item for item in positions.values() if isinstance(item, dict) and item.get("available")]
    opportunities = max((_int(item.get("matches")) for item in observed), default=0)
    curve_sessions = max((_int(item.get("sessions")) for item in observed), default=0)
    return {
        "opportunities": opportunities,
        "sessions": curve_sessions,
        "minimum_opportunities": minimum_opportunities,
        "minimum_sessions": minimum_sessions,
        "runtime_support_pass": bool(observed),
        "semantic_contract_support_pass": opportunities >= 30 and curve_sessions >= 12,
        "positions_available": sorted(str(key) for key, item in positions.items() if item.get("available")),
        "censored_sessions": _int(curve.get("censored_sessions")),
        "robustness": {"position_count": len(observed)},
    }


def _family_trace(
    family: str,
    *,
    report: dict[str, Any],
    base: dict[str, Any],
    matches: list[Any],
    history_complete: bool,
) -> dict[str, Any]:
    base_finding = next(item for item in base.get("findings", ()) if item.get("family") == family)
    final_finding = next(item for item in report.get("findings", ()) if item.get("family") == family)
    evidence = report.get("supporting_evidence", {})
    portfolio = evidence.get("portfolio_shape", {})
    transfer = evidence.get("transfer_frontier", {})
    response = evidence.get("result_response", {})
    involvement = evidence.get("involvement", {})
    death = evidence.get("death_exposure", {})
    try:
        semantic_key = assembly._semantic_key(
            family, final_finding, portfolio, transfer, response, involvement, death
        )
    except (KeyError, TypeError, ValueError):
        semantic_key = None
    audit = report.get("selection_audit", {}).get(family, {})
    branch_audit = audit.get("branches", {}) if isinstance(audit, dict) else {}
    branch_raw = {
        str(key): _num(value.get("raw_p_value"), 1.0)
        for key, value in branch_audit.items()
        if isinstance(value, dict) and isinstance(value.get("raw_p_value"), (int, float))
    }
    branch_q = {
        str(key): _num(value.get("adjusted_q_value"), 1.0)
        for key, value in branch_audit.items()
        if isinstance(value, dict)
    }
    selected_branch = branch_audit.get(semantic_key, {}) if semantic_key else {}
    production = evidence.get("production_bootstrap", {}).get("semantic_statistics", {})
    availability = production.get("availability", {}).get(family, {})
    branch_samples = production.get("branches", {}).get(family, {})
    semantic_evidence_complete = bool(
        availability.get("available")
        and _int(availability.get("usable_iterations")) == 2000
        and semantic_key in branch_samples
        and len(branch_samples.get(semantic_key, ())) == 2000
    )
    support = _support(family, matches, evidence, base_finding)
    definition = SEMANTIC_OUTCOME_REGISTRY.get(str(semantic_key))
    final_published = final_finding.get("published") is True
    surface = _surface_counts(report, family)
    return {
        "base": {
            "status": base_finding.get("status"),
            "published": base_finding.get("published") is True,
            "raw_p": _num(base_finding.get("raw_p_value"), 1.0),
            "q": _num(base_finding.get("adjusted_q_value"), 1.0),
            "confidence": base_finding.get("confidence"),
            "bootstrap_stability": _num(base_finding.get("bootstrap_stability")),
            "sample_size": _int(base_finding.get("sample_size")),
            "independent_sessions": _int(base_finding.get("independent_session_count")),
            "coverage": _num(base_finding.get("coverage")),
        },
        "support": support,
        "stability": {
            "observed_bootstrap_stability": _num(final_finding.get("bootstrap_stability")),
            "observed_confidence": final_finding.get("confidence"),
            "standalone_gate_implemented": False,
            "status": "diagnostic signal only; no separate V6.1 publication boolean",
        },
        "confounder_gate": {
            "implemented": False,
            "pass": None,
            "status": "not explicit in V6.1 runtime selection",
        },
        "robustness_gate": {
            "implemented": False,
            "pass": None,
            "status": "registry checks are declared, but assembly does not evaluate a separate branch gate",
        },
        "semantic": {
            "key": semantic_key,
            "rollout_status": definition.rollout_status if definition else None,
            "minimum_opportunities": definition.minimum_opportunities if definition else None,
            "minimum_sessions": definition.minimum_sessions if definition else None,
            "evidence_complete": semantic_evidence_complete,
            "usable_iterations": _int(availability.get("usable_iterations")),
            "effect_or_equivalence_gate_implemented": False,
            "effect_or_equivalence_pass": None,
        },
        "family": {
            "raw_p": _num(audit.get("raw_p_value"), 1.0),
            "q": _num(audit.get("adjusted_q_value"), 1.0),
            "qualified": audit.get("qualified") is True,
        },
        "branch": {
            "raw_p": _num(selected_branch.get("raw_p_value"), 1.0),
            "q": _num(selected_branch.get("adjusted_q_value"), 1.0),
            "qualified": selected_branch.get("qualified") is True,
            "raw_p_values": branch_raw,
            "q_values": branch_q,
            "unconditional_q_values": _bh(branch_raw) if branch_raw else {},
        },
        "publication": {
            "public_candidate": bool(definition and definition.rollout_status == "public_candidate"),
            "history_complete": history_complete,
            "published": final_published,
            "inherited_v6_published": base_finding.get("published") is True,
        },
        "surface": surface,
        "gate_flags": {
            "data_eligible": True,
            "minimum_support": bool(support["semantic_contract_support_pass"]),
            "inherited_v6_publication_gate": base_finding.get("published") is True,
            "family_qualified": audit.get("qualified") is True,
            "branch_qualified": selected_branch.get("qualified") is True,
            "semantic_evidence_complete": semantic_evidence_complete,
            "public_candidate": bool(definition and definition.rollout_status == "public_candidate"),
            "history_complete": history_complete,
            "published": final_published,
            "surfaced": bool(final_published and surface["surfaced"]),
        },
    }


def _profile_task(profile_id: str) -> dict[str, Any]:
    global _BASE_REPORT
    try:
        rows = _ROWS[profile_id]
        account_id = _stable_account_id(profile_id)
        history = canonical_history(rows, account_id=account_id)
        matches = list(history.normalization.eligible_matches)
        _BASE_REPORT = None
        report = assembly.assemble_free_dna_report_v61(
            account_id=account_id,
            profile={"personaname": "Offline calibration subject"},
            matches=matches,
            canonical_history=history,
            processed_matches=len(matches),
            eligible_matches=len(matches),
            model_version=MODEL_VERSION,
            template_version="templates-1.0.0",
            cost_ledger=DataCostLedger(),
            analysis_version_fingerprint=str(_BUNDLE.manifest.get("code_fingerprint", "")),
            baseline_resolver=_BUNDLE.baseline.resolver(),
            thresholds=_BUNDLE.thresholds.metrics,
            taxonomy_by_hero=_TAXONOMY,
            completed_sessions=_COMPLETION[profile_id],
            artifact_checksums=_BUNDLE.checksums,
            supporting_artifacts=_SUPPORTING,
            bootstrap_mode="weighted",
            shadow_enabled=False,
            experimental_evolution_enabled=False,
            experimental_loops_enabled=False,
            protected_cohorts_out={},
        )
        validate_free_dna_report_v61(report)
        if _BASE_REPORT is None:
            raise RuntimeError("V6.1 base report capture failed")
        digest = hashlib.sha256(profile_id.encode()).hexdigest()
        audit = history.audit.as_dict()
        final_findings = [item for item in report.get("findings", ()) if isinstance(item, dict)]
        families = {
            family: _family_trace(
                family,
                report=report,
                base=_BASE_REPORT,
                matches=matches,
                history_complete=audit.get("completeness") == "complete",
            )
            for family in FAMILIES
        }
        elements = [item for item in report.get("elements", ()) if isinstance(item, dict)]
        published_count = sum(item.get("published") is True for item in final_findings)
        return {
            "profile_digest": digest,
            "status": "evaluated",
            "input": {
                "raw_count": _int(audit.get("raw_count")),
                "normalized_count": _int(audit.get("normalized_count")),
                "eligible_count": _int(audit.get("eligible_count")),
                "deduplicated_count": _int(audit.get("deduplicated_count")),
                "sessions": len({_stable_session(row, index) for index, row in enumerate(matches)}),
                "completed_sessions": sum(bool(value) for value in _COMPLETION[profile_id].values()),
                "history_completeness": audit.get("completeness"),
                "data_eligible": bool(audit.get("eligible_count", 0) >= 30),
                "window_days": 365,
            },
            "elements": {
                "count": len(elements),
                "available": sum(item.get("status") in {"available", "descriptive"} for item in elements),
                "statuses": dict(sorted(Counter(str(item.get("status")) for item in elements).items())),
            },
            "base_published_count": sum(
                item.get("published") is True for item in _BASE_REPORT.get("findings", ()) if isinstance(item, dict)
            ),
            "v61_family_qualified_count": sum(
                item["family"]["qualified"] for item in families.values()
            ),
            "v61_branch_qualified_count": sum(
                item["branch"]["qualified"] for item in families.values()
            ),
            "final_published_count": published_count,
            "families": families,
            "presentation": {
                "diagnostic_questions": len(report.get("diagnostic_questions", ())),
                "eligible_finding_share_cards": sum(
                    str(item.get("id", "")).startswith("finding:") and item.get("eligible") is True
                    for item in report.get("share_candidates", ()) if isinstance(item, dict)
                ),
                "available_pages": sum(bool(item.get("available")) for item in report.get("pages", ()) if isinstance(item, dict)),
                "published_families_surfaced": sum(
                    item["publication"]["published"] and item["surface"]["surfaced"]
                    for item in families.values()
                ),
            },
        }
    except Exception as exc:  # profile id stays private; only its digest is returned
        return {
            "profile_digest": hashlib.sha256(profile_id.encode()).hexdigest(),
            "status": "error",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:240],
        }


def _stable_session(row: Any, index: int) -> str:
    if isinstance(row, dict):
        value = row.get("session_id")
    else:
        value = getattr(row, "session_id", None)
    return str(value) if value not in (None, "") else f"row:{index}"


def _history_bin(matches: int) -> str:
    if matches < 60:
        return "30-59"
    if matches < 120:
        return "60-119"
    if matches < 250:
        return "120-249"
    if matches < 500:
        return "250-499"
    return "500+"


def _threshold_sensitivity(records: list[dict[str, Any]]) -> dict[str, Any]:
    def scenario(mode: str, family_threshold: float, branch_threshold: float) -> dict[str, Any]:
        total_with_gate = total_without_gate = 0
        profiles_with_gate = profiles_without_gate = 0
        per_family_with: Counter[str] = Counter()
        per_family_without: Counter[str] = Counter()
        for record in records:
            selected_with: list[str] = []
            selected_without: list[str] = []
            p_values = {family: record["families"][family]["family"]["raw_p"] for family in FAMILIES}
            family_q = _bh(p_values)
            for family in FAMILIES:
                detail = record["families"][family]
                raw_branches = detail["branch"]["raw_p_values"]
                branch_q = _bh(raw_branches) if family_q[family] <= family_threshold else {
                    key: 1.0 for key in raw_branches
                }
                key = detail["semantic"]["key"]
                branch_pass = key in branch_q and branch_q[key] <= branch_threshold
                candidate = (
                    family_q[family] <= family_threshold
                    and branch_pass
                    and detail["publication"]["public_candidate"]
                    and detail["publication"]["history_complete"]
                )
                if candidate:
                    selected_without.append(family)
                    per_family_without[family] += 1
                    if detail["publication"]["inherited_v6_published"]:
                        selected_with.append(family)
                        per_family_with[family] += 1
            total_without_gate += min(3, len(selected_without))
            total_with_gate += min(3, len(selected_with))
            profiles_without_gate += bool(selected_without)
            profiles_with_gate += bool(selected_with)
        return {
            "mode": mode,
            "family_q_threshold": family_threshold,
            "branch_q_threshold": branch_threshold,
            "with_inherited_v6_gate": {
                "profiles_with_any": profiles_with_gate,
                "published_findings": total_with_gate,
                "by_family": dict(per_family_with),
            },
            "ignoring_inherited_v6_gate_diagnostic_only": {
                "profiles_with_any": profiles_without_gate,
                "candidate_findings": total_without_gate,
                "by_family": dict(per_family_without),
            },
        }

    scenarios = []
    for value in Q_GRID:
        scenarios.append(scenario("family_q_only", value, 0.05))
        scenarios.append(scenario("branch_q_only", 0.05, value))
        scenarios.append(scenario("both", value, value))
    return {
        "threshold_grid": list(Q_GRID),
        "interpretation": "Counterfactuals reuse frozen training traces; they do not change runtime thresholds or artifacts.",
        "scenarios": scenarios,
    }


def _aggregate(records: list[dict[str, Any]], provenance: dict[str, Any]) -> dict[str, Any]:
    evaluated = [record for record in records if record.get("status") == "evaluated"]
    family_summary: dict[str, Any] = {}
    for family in FAMILIES:
        details = [record["families"][family] for record in evaluated]
        support = [item["support"] for item in details]
        family_p = [item["family"]["raw_p"] for item in details]
        family_q = [item["family"]["q"] for item in details]
        branch_p = [item["branch"]["raw_p"] for item in details]
        branch_q = [item["branch"]["q"] for item in details]
        unconditional_branch_q = [
            item["branch"]["unconditional_q_values"].get(item["semantic"]["key"], 1.0)
            for item in details
        ]
        reasons = Counter()
        for item in details:
            flags = item["gate_flags"]
            if not flags["data_eligible"]:
                reasons["data_eligibility"] += 1
            if not flags["minimum_support"]:
                reasons["minimum_support"] += 1
            if not flags["inherited_v6_publication_gate"]:
                reasons["inherited_v6_publication_gate"] += 1
            if not flags["family_qualified"]:
                reasons["family_omnibus_q"] += 1
            if not flags["branch_qualified"]:
                reasons["branch_q"] += 1
            if not flags["semantic_evidence_complete"]:
                reasons["semantic_evidence"] += 1
            if not flags["published"]:
                reasons["final_publication"] += 1
        family_summary[family] = {
            "profiles": len(details),
            "base_status": dict(Counter(item["base"]["status"] for item in details)),
            "base_published_profiles": sum(item["base"]["published"] for item in details),
            "base_published_family_count": sum(item["base"]["published"] for item in details),
            "support": {
                "opportunities": _q([_num(item.get("opportunities")) for item in support]),
                "sessions": _q([_num(item.get("sessions")) for item in support]),
                "runtime_support_pass": sum(item["runtime_support_pass"] for item in support),
                "semantic_contract_support_pass": sum(item["semantic_contract_support_pass"] for item in support),
            },
            "family_raw_p": _q(family_p),
            "family_q": _q(family_q),
            "family_qualified_profiles": sum(item["family"]["qualified"] for item in details),
            "selected_branch_raw_p": _q(branch_p),
            "selected_branch_q_runtime": _q(branch_q),
            "selected_branch_q_unconditional_diagnostic": _q(unconditional_branch_q),
            "branch_qualified_profiles": sum(item["branch"]["qualified"] for item in details),
            "semantic_evidence_complete_profiles": sum(item["semantic"]["evidence_complete"] for item in details),
            "final_published_profiles": sum(item["publication"]["published"] for item in details),
            "surfaced_profiles": sum(item["publication"]["published"] and item["surface"]["surfaced"] for item in details),
            "suppression_stage_counts": dict(sorted(reasons.items())),
        }

    history = Counter()
    history_rows: dict[str, list[dict[str, Any]]] = {}
    for record in evaluated:
        label = _history_bin(_int(record["input"]["eligible_count"]))
        history[label] += 1
        history_rows.setdefault(label, []).append(record)
    history_summary = {}
    for label, rows in history_rows.items():
        history_summary[label] = {
            "profiles": len(rows),
            "match_count": _q([_num(row["input"]["eligible_count"]) for row in rows]),
            "any_base_published": sum(bool(row["base_published_count"]) for row in rows),
            "any_family_qualified": sum(bool(row["v61_family_qualified_count"]) for row in rows),
            "any_branch_qualified": sum(bool(row["v61_branch_qualified_count"]) for row in rows),
            "any_final_published": sum(bool(row["final_published_count"]) for row in rows),
            "by_family_final_published": {
                family: sum(row["families"][family]["publication"]["published"] for row in rows)
                for family in FAMILIES
            },
        }

    funnel = [
        {"stage": "training_profiles", "count": len(records)},
        {"stage": "offline_reports_assembled", "count": len(evaluated)},
        {"stage": "all_seven_elements_available_or_descriptive", "count": sum(row["elements"]["available"] == 7 for row in evaluated)},
        {"stage": "any_inherited_v6_family_published", "count": sum(bool(row["base_published_count"]) for row in evaluated)},
        {"stage": "any_v61_family_qualified", "count": sum(bool(row["v61_family_qualified_count"]) for row in evaluated)},
        {"stage": "any_v61_branch_qualified", "count": sum(bool(row["v61_branch_qualified_count"]) for row in evaluated)},
        {"stage": "any_final_finding_published", "count": sum(bool(row["final_published_count"]) for row in evaluated)},
        {"stage": "any_published_finding_surfaced", "count": sum(bool(row["presentation"]["published_families_surfaced"]) for row in evaluated)},
    ]

    near_misses = {
        family: {
            "q_at_or_below_0_05": sum(item["family"]["q"] <= 0.05 for item in (record["families"][family] for record in evaluated)),
            "q_in_0_05_to_0_07": sum(0.05 < item["family"]["q"] <= 0.07 for item in (record["families"][family] for record in evaluated)),
            "q_in_0_07_to_0_10": sum(0.07 < item["family"]["q"] <= 0.10 for item in (record["families"][family] for record in evaluated)),
            "q_over_0_10": sum(item["family"]["q"] > 0.10 for item in (record["families"][family] for record in evaluated)),
            "smallest_q_gap_above_0_05": min(
                (item["family"]["q"] - 0.05 for item in (record["families"][family] for record in evaluated) if item["family"]["q"] > 0.05),
                default=None,
            ),
            "support_failures": sum(not record["families"][family]["gate_flags"]["minimum_support"] for record in evaluated),
            "base_gate_failures": sum(not record["families"][family]["gate_flags"]["inherited_v6_publication_gate"] for record in evaluated),
        }
        for family in FAMILIES
    }

    presentation = {
        "profiles_with_zero_final_findings": sum(row["final_published_count"] == 0 for row in evaluated),
        "diagnostic_questions_total": sum(row["presentation"]["diagnostic_questions"] for row in evaluated),
        "eligible_finding_share_cards_total": sum(row["presentation"]["eligible_finding_share_cards"] for row in evaluated),
        "published_family_surfaces_total": sum(row["presentation"]["published_families_surfaced"] for row in evaluated),
        "page_availability": dict(Counter(
            row["presentation"]["available_pages"] for row in evaluated
        )),
    }
    return {
        "version": "v61-suppression-autopsy-1.0.0",
        "provenance": provenance,
        "funnel": funnel,
        "family_summary": family_summary,
        "history_depth_bins": history_summary,
        "near_misses": near_misses,
        "presentation": presentation,
        "threshold_sensitivity": _threshold_sensitivity(evaluated),
        "errors": [record for record in records if record.get("status") == "error"],
        "opendota_calls": 0,
    }


def _provenance(corpus_path: Path, split_path: Path, artifact_dir: Path, manifest: dict[str, Any], corpus: Any) -> dict[str, Any]:
    summary = corpus.payload.get("summary", {})
    profile_counts = [
        _int(profile.get("eligible_match_count"))
        for profile in corpus.profile_summaries.values()
    ]
    timestamps = [int(row["start_time"]) for row in corpus.matches]
    return {
        "classification": {
            "training_subset": {"class": "A", "scope": "791 profiles bound by the frozen train digest", "use": "exploratory/counterfactual only"},
            "replacement_holdout": {"class": "B", "scope": "339 profiles", "use": "descriptive-only; not loaded by this run"},
            "historical_corpus_2_0": {"class": "C", "scope": "superseded 2.0.0 corpus/artifacts", "use": "historical provenance only"},
            "legacy_compact_corpus": {"class": "C", "scope": "legacy paginated compact corpus", "use": "historical provenance only"},
            "tracked_runtime_artifacts": {"class": "B", "scope": "frozen release inputs", "use": "runtime reproduction; not tuning"},
        },
        "source": manifest.get("source"),
        "corpus": {
            "path": str(corpus_path),
            "sha256": sha256_file(corpus_path),
            "schema_version": corpus.payload.get("schema_version"),
            "profile_count": len(corpus.profile_ids),
            "eligible_profile_count": len(corpus.usable_profile_ids),
            "eligible_match_count": _int(summary.get("eligible_match_count")),
            "profile_match_count": _q([float(value) for value in profile_counts]),
            "window_mode": corpus.window_mode,
            "window_days": 365,
            "provider_limit": 10000,
            "max_profile_match_count_below_provider_limit": max(profile_counts, default=0) < 10000,
            "completeness_counts": dict(Counter(
                str(profile.get("history_audit", {}).get("completeness"))
                for profile in corpus.profile_summaries.values()
            )),
            "earliest_match": datetime.fromtimestamp(min(timestamps), tz=UTC).date().isoformat() if timestamps else None,
            "latest_match": datetime.fromtimestamp(max(timestamps), tz=UTC).date().isoformat() if timestamps else None,
        },
        "split": {
            "path": str(split_path),
            "sha256": sha256_file(split_path),
            "train_profile_count": manifest.get("split", {}).get("train_profile_count"),
            "holdout_profile_count": manifest.get("split", {}).get("holdout_profile_count"),
            "overlap_count": manifest.get("split", {}).get("overlap_count"),
            "train_profile_digest": manifest.get("split", {}).get("train_profile_digest"),
            "holdout_profile_digest": manifest.get("split", {}).get("holdout_profile_digest"),
        },
        "artifacts": {
            "directory": str(artifact_dir),
            "manifest_sha256": sha256_file(artifact_dir / "build-manifest-6.1.0.json"),
            "checksums": {name: sha256_file(artifact_dir / name) for name in _BUNDLE.checksums},
            "release_authorized": manifest.get("release_authorized"),
            "holdout_output_inspected": manifest.get("holdout_output_inspected"),
        },
        "runtime_contract": {
            "history_endpoint": "summary history only; date=365; limit=10000",
            "physical_request_count": 1,
            "detail_requests": 0,
            "parse_requests": 0,
            "session_gap_minutes": 90,
            "free_history_limit": None,
            "opendota_calls": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    manifest = json.loads((args.artifact_dir / "build-manifest-6.1.0.json").read_text())
    split = json.loads(args.split.read_text())
    corpus = load_canonical_corpus(args.corpus)
    corpus_sha = sha256_file(args.corpus)
    split_sha = sha256_file(args.split)
    if corpus_sha != manifest.get("corpus_sha256") or split_sha != manifest.get("split_manifest_checksum"):
        raise SystemExit("artifact/corpus/split binding mismatch")
    train = {str(value) for value in split.get("train_profile_ids", ())}
    holdout = {str(value) for value in split.get("holdout_profile_ids", ())}
    if train & holdout or train | holdout != set(corpus.profile_ids):
        raise SystemExit("split integrity mismatch")
    if profile_digest(tuple(train)) != manifest.get("split", {}).get("train_profile_digest"):
        raise SystemExit("train profile digest mismatch")
    if len(train) != 791 or len(holdout) != 339:
        raise SystemExit("unexpected frozen split counts")

    global _ROWS, _COMPLETION, _BUNDLE, _TAXONOMY, _SUPPORTING
    _ROWS = {profile: [] for profile in train}
    for row in corpus.matches:
        profile = str(row["profile_id"])
        if profile in _ROWS:
            _ROWS[profile].append(dict(row))
    _COMPLETION = {
        profile: dict(corpus.completion_for_profile(profile))
        for profile in train
    }
    if set(_ROWS) != train or any(len(rows) < 30 for rows in _ROWS.values()):
        raise SystemExit("training rows do not satisfy the 30-match boundary")

    _BUNDLE = load_v61_artifact_bundle(
        args.artifact_dir,
        expected_corpus_sha256=corpus_sha,
        expected_split_checksum=split_sha,
        expected_source_revision=str(manifest["source"]["repository_commit"]),
        expected_dirty_worktree=False,
    )
    _TAXONOMY = current_taxonomy_mapping()
    _SUPPORTING = {
        "summary_prior": _BUNDLE.summary_prior,
        "distance_calibration": _BUNDLE.distance_calibration,
        "session_reliability": _BUNDLE.session_reliability,
        "semantic_calibration": _BUNDLE.semantic_calibration,
        "manifest": _BUNDLE.manifest,
    }
    provenance = _provenance(args.corpus, args.split, args.artifact_dir, manifest, corpus)
    context = mp.get_context("fork")
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=context, initializer=_init_worker) as executor:
        futures = {executor.submit(_profile_task, profile): profile for profile in sorted(train)}
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda record: record.get("profile_digest", ""))

    summary = _aggregate(records, provenance)
    _write_json(args.output_dir / "provenance.json", provenance)
    _write_json(args.output_dir / "summary.json", summary)
    _write_json(args.output_dir / "threshold-sensitivity.json", summary["threshold_sensitivity"])
    _write_jsonl(args.output_dir / "profile-family-trace.jsonl", records)
    csv_rows = []
    for record in records:
        if record.get("status") != "evaluated":
            continue
        for family in FAMILIES:
            detail = record["families"][family]
            csv_rows.append({
                "profile_digest": record["profile_digest"],
                "family": family,
                "history_matches": record["input"]["eligible_count"],
                "history_sessions": record["input"]["sessions"],
                "data_eligible": detail["gate_flags"]["data_eligible"],
                "minimum_support": detail["gate_flags"]["minimum_support"],
                "base_status": detail["base"]["status"],
                "base_published": detail["base"]["published"],
                "family_raw_p": detail["family"]["raw_p"],
                "family_q": detail["family"]["q"],
                "family_qualified": detail["family"]["qualified"],
                "branch_key": detail["semantic"]["key"],
                "branch_raw_p": detail["branch"]["raw_p"],
                "branch_q": detail["branch"]["q"],
                "branch_qualified": detail["branch"]["qualified"],
                "final_published": detail["publication"]["published"],
                "surfaced": detail["surface"]["surfaced"],
            })
    _write_csv(args.output_dir / "profile-family-trace.csv", csv_rows)
    print(json.dumps({
        "output_dir": str(args.output_dir),
        "profiles": len(records),
        "evaluated": len(summary["errors"]) == 0,
        "errors": len(summary["errors"]),
        "final_published_profiles": summary["funnel"][-2]["count"],
        "opendota_calls": 0,
    }, sort_keys=True))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
