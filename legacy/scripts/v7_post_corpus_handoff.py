#!/usr/bin/env python3
"""Validate the completed V7 STRATZ corpus before any Finding research runs.

The script is deliberately independent of the acquisition runner: it recomputes
the reconciliation from the immutable artefacts instead of trusting the
runner's own manifest.  It performs no provider call of any kind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "legacy" / "services" / "api"))

from report_card.player_analysis_v7.research.corpus import (  # noqa: E402
    RESERVED_SPLITS,
    CorpusPaths,
    corpus_paths,
    forbidden_fields_in,
    freeze_paths,
    iter_ledger,
    read_json,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def check_split_manifest(freeze_root: Path, run_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest_path = freeze_root / "manifests" / "split-manifest.json"
    digest = sha256_file(manifest_path)
    manifest = read_json(manifest_path)
    members = manifest["members"]
    by_pseudonym: dict[str, list[str]] = defaultdict(list)
    for member in members:
        by_pseudonym[member["pseudonym"]].append(member["split"])
    overlap = {name: splits for name, splits in by_pseudonym.items() if len(splits) > 1}
    counts = Counter(member["split"] for member in members)
    parsed_counts = Counter(
        member["split"] for member in members if member.get("parsed_subset")
    )
    return {
        "path": str(manifest_path),
        "sha256": digest,
        "sha256_matches_freeze": digest == run_manifest["freeze"]["split_manifest_sha256"],
        "members": len(members),
        "unique_pseudonyms": len(by_pseudonym),
        "identity_overlap_count": len(overlap),
        "split_counts": dict(counts),
        "parsed_subset_counts": dict(parsed_counts),
        "reserved_parsed_members": sum(
            parsed_counts.get(split, 0) for split in RESERVED_SPLITS
        ),
        "split_membership": {
            member["pseudonym"]: member["split"] for member in members
        },
    }


def check_ledger_and_raw(paths: CorpusPaths) -> dict[str, Any]:
    ledger_rows = 0
    physical_ordinals: Counter[int] = Counter()
    statuses: Counter[Any] = Counter()
    error_kinds: Counter[Any] = Counter()
    operations: Counter[str] = Counter()
    operation_digests: dict[str, set[str]] = defaultdict(set)
    schema_versions: Counter[str] = Counter()
    immutable_success = 0
    cache_hits = 0
    expected_bodies: dict[str, str] = {}
    failed_attempt_bodies: set[str] = set()
    response_bytes = 0
    token_bearing_headers: set[str] = set()
    variables_retained = 0

    for row in iter_ledger(paths):
        ledger_rows += 1
        physical_ordinals[row["physical_ordinal"]] += 1
        statuses[row.get("http_status")] += 1
        error_kinds[row.get("error_kind")] += 1
        operations[row["operation"]] += 1
        operation_digests[row["operation"]].add(row["operation_document_sha256"])
        schema_versions[row["schema_version"]] += 1
        response_bytes += row.get("response_bytes") or 0
        if row.get("immutable_success"):
            immutable_success += 1
        if row.get("cache_hit"):
            cache_hits += 1
        if row.get("raw_body_path") and row.get("response_sha256"):
            expected_bodies[row["raw_body_path"]] = row["response_sha256"]
            if not row.get("immutable_success"):
                failed_attempt_bodies.add(row["raw_body_path"])
        if "variables" in row:
            variables_retained += 1
        for header in (row.get("safe_headers") or {}):
            lowered = header.lower()
            if lowered in {"authorization", "cookie", "set-cookie", "x-api-key"}:
                token_bearing_headers.add(lowered)

    body_files = sorted(paths.raw.glob("*.body"))
    metadata_files = sorted(paths.raw.glob("*.json"))

    hash_mismatches: list[str] = []
    missing_bodies: list[str] = []
    malformed_json: list[str] = []
    graphql_errors = 0
    partial_data = 0
    failed_attempt_non_json = 0

    for relative, expected in expected_bodies.items():
        path = paths.root / relative
        if not path.is_file():
            missing_bodies.append(relative)
            continue
        actual = sha256_file(path)
        if actual != expected:
            hash_mismatches.append(relative)
            continue
        # Only successful immutable responses are research evidence.  A failed
        # attempt archives whatever the edge returned (an HTML or plain-text
        # error page), which is auditable provenance rather than corruption.
        succeeded = relative not in failed_attempt_bodies
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            if succeeded:
                malformed_json.append(relative)
            else:
                failed_attempt_non_json += 1
            continue
        if not isinstance(payload, dict):
            if succeeded:
                malformed_json.append(relative)
            else:
                failed_attempt_non_json += 1
            continue
        if not succeeded:
            continue
        if payload.get("errors"):
            graphql_errors += 1
            if payload.get("data"):
                partial_data += 1

    orphan_bodies = sorted(
        path.name for path in body_files if f"raw/{path.name}" not in expected_bodies
    )

    body_digest = hashlib.sha256()
    for path in body_files:
        body_digest.update(path.name.encode("utf-8"))
        body_digest.update(sha256_file(path).encode("utf-8"))

    return {
        "ledger_rows": ledger_rows,
        "physical_attempts": len(physical_ordinals),
        "duplicate_physical_ordinals": sum(
            1 for count in physical_ordinals.values() if count > 1
        ),
        "ordinal_gaps": sorted(
            set(range(1, max(physical_ordinals) + 1)) - set(physical_ordinals)
        )[:20]
        if physical_ordinals
        else [],
        "immutable_successes": immutable_success,
        "cache_hits": cache_hits,
        "raw_body_objects": len(body_files),
        "raw_metadata_objects": len(metadata_files),
        "ledger_referenced_bodies": len(expected_bodies),
        "hash_mismatches": hash_mismatches,
        "missing_bodies": missing_bodies,
        "orphan_bodies": orphan_bodies,
        "malformed_json_bodies": malformed_json,
        "failed_attempt_bodies": len(failed_attempt_bodies),
        "failed_attempt_non_json_bodies": failed_attempt_non_json,
        "graphql_error_responses": graphql_errors,
        "graphql_partial_data_responses": partial_data,
        "http_statuses": {str(key): value for key, value in sorted(statuses.items(), key=lambda item: str(item[0]))},
        "error_kinds": {str(key): value for key, value in error_kinds.items() if key},
        "operations": dict(operations),
        "operation_document_digests": {
            name: sorted(digests) for name, digests in operation_digests.items()
        },
        "operation_digest_mixing": {
            name: sorted(digests)
            for name, digests in operation_digests.items()
            if len(digests) > 1
        },
        "ledger_schema_versions": dict(schema_versions),
        "response_bytes": response_bytes,
        "variables_retained_rows": variables_retained,
        "token_bearing_headers_retained": sorted(token_bearing_headers),
        "recomputed_body_manifest_sha256": body_digest.hexdigest(),
    }


def check_canonical(
    paths: CorpusPaths,
    table: str,
    split_membership: dict[str, str],
    window: dict[str, Any],
) -> dict[str, Any]:
    directory = paths.canonical_history if table == "history" else paths.canonical_parsed
    players = 0
    rows = 0
    split_counts: Counter[str] = Counter()
    reserved_documents: list[str] = []
    membership_mismatches: list[str] = []
    unknown_pseudonyms: list[str] = []
    duplicate_match_rows = 0
    cross_player_matches: Counter[int] = Counter()
    intra_player_duplicate_players = 0
    out_of_window_rows = 0
    invalid_timestamp_rows = 0
    forbidden: set[str] = set()
    schema_versions: Counter[str] = Counter()
    completeness: Counter[str] = Counter()
    per_player_rows: list[int] = []

    start = window["start_timestamp"]
    end = window["end_timestamp"]

    for path in sorted(directory.glob("v7p_*.json")):
        document = read_json(path)
        players += 1
        split = document.get("split", "__MISSING__")
        split_counts[split] += 1
        schema_versions[document.get("schema_version", "__MISSING__")] += 1
        if table == "history":
            completeness[document.get("completeness", "__MISSING__")] += 1
        if split in RESERVED_SPLITS:
            reserved_documents.append(path.name)
        pseudonym = document.get("account_pseudonym")
        declared = split_membership.get(pseudonym)
        if declared is None:
            unknown_pseudonyms.append(path.name)
        elif declared != split:
            membership_mismatches.append(path.name)
        forbidden |= forbidden_fields_in(document.get("profile", {}))
        document_rows = document.get("rows", [])
        rows += len(document_rows)
        per_player_rows.append(len(document_rows))
        if document.get("duplicate_match_count"):
            duplicate_match_rows += int(document["duplicate_match_count"])
        seen: set[int] = set()
        for row in document_rows:
            match_id = row.get("match_id")
            if match_id in seen:
                intra_player_duplicate_players += 1
            seen.add(match_id)
            cross_player_matches[match_id] += 1
            started = row.get("started_at")
            if not isinstance(started, int) or started <= 0:
                invalid_timestamp_rows += 1
            elif not (start <= started <= end):
                out_of_window_rows += 1
        if document_rows:
            forbidden |= forbidden_fields_in(document_rows[0])

    per_player_rows.sort()
    median = per_player_rows[len(per_player_rows) // 2] if per_player_rows else 0

    return {
        "players": players,
        "rows": rows,
        "unique_match_ids": len(cross_player_matches),
        "matches_seen_for_multiple_players": sum(
            1 for count in cross_player_matches.values() if count > 1
        ),
        "intra_player_duplicate_rows": intra_player_duplicate_players,
        "runner_reported_deduplicated_rows": duplicate_match_rows,
        "split_counts": dict(split_counts),
        "reserved_split_documents": reserved_documents,
        "split_membership_mismatches": membership_mismatches,
        "pseudonyms_absent_from_split_manifest": unknown_pseudonyms,
        "rows_outside_window": out_of_window_rows,
        "rows_with_invalid_timestamp": invalid_timestamp_rows,
        "forbidden_field_hits": sorted(forbidden),
        "schema_versions": dict(schema_versions),
        "completeness": dict(completeness),
        "median_rows_per_player": median,
        "min_rows_per_player": per_player_rows[0] if per_player_rows else 0,
        "max_rows_per_player": per_player_rows[-1] if per_player_rows else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default=None)
    parser.add_argument("--freeze-root", default=None)
    parser.add_argument("--out", default=None, help="write the JSON report here")
    args = parser.parse_args()

    paths = corpus_paths(args.corpus_root)
    freeze_root = freeze_paths(args.freeze_root)
    run_manifest = read_json(paths.run_manifest)

    split_report = check_split_manifest(freeze_root, run_manifest)
    membership = split_report.pop("split_membership")
    ledger_report = check_ledger_and_raw(paths)
    window = run_manifest["window"]
    history_report = check_canonical(paths, "history", membership, window)
    parsed_report = check_canonical(paths, "parsed", membership, window)

    critical: list[str] = []
    if not split_report["sha256_matches_freeze"]:
        critical.append("split manifest digest does not match the frozen binding")
    if split_report["identity_overlap_count"]:
        critical.append("split identity overlap detected")
    if split_report["reserved_parsed_members"]:
        critical.append("reserved/sealed accounts appear in the parsed subset")
    for report, label in ((history_report, "history"), (parsed_report, "parsed")):
        if report["reserved_split_documents"]:
            critical.append(f"{label}: reserved/sealed split materialised in the corpus")
        if report["split_membership_mismatches"]:
            critical.append(f"{label}: split membership disagrees with the frozen manifest")
        if report["pseudonyms_absent_from_split_manifest"]:
            critical.append(f"{label}: canonical document outside the frozen cohort")
        if report["rows_outside_window"]:
            critical.append(f"{label}: rows outside the frozen 365-day window")
        if report["rows_with_invalid_timestamp"]:
            critical.append(f"{label}: invalid match timestamps")
        if report["intra_player_duplicate_rows"]:
            critical.append(f"{label}: duplicate match rows within a player")
        if report["forbidden_field_hits"]:
            critical.append(f"{label}: forbidden provider field present")
    if ledger_report["hash_mismatches"]:
        critical.append("raw response hash mismatch")
    if ledger_report["missing_bodies"]:
        critical.append("ledger references a missing raw body")
    if ledger_report["malformed_json_bodies"]:
        critical.append("malformed raw GraphQL response body")
    if ledger_report["graphql_error_responses"]:
        critical.append("GraphQL error response archived as success")
    if ledger_report["operation_digest_mixing"]:
        critical.append("operation document digest mixing")
    if ledger_report["token_bearing_headers_retained"]:
        critical.append("token-bearing header retained in the ledger")
    if ledger_report["duplicate_physical_ordinals"]:
        critical.append("duplicate physical ordinals in the request ledger")

    report = {
        "corpus_root": str(paths.root),
        "freeze_root": str(freeze_root),
        "run_manifest": run_manifest,
        "split": split_report,
        "ledger_and_raw": ledger_report,
        "canonical_history": history_report,
        "canonical_parsed": parsed_report,
        "reserved_split_touched": bool(
            history_report["reserved_split_documents"]
            or parsed_report["reserved_split_documents"]
            or split_report["reserved_parsed_members"]
        ),
        "critical_findings": critical,
        "research_ready": not critical,
        "new_provider_calls": 0,
    }

    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if not critical else 1


if __name__ == "__main__":
    raise SystemExit(main())
