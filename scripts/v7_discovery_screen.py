#!/usr/bin/env python3
"""Run the V7 discovery-only early screen over the candidate universe.

DISCOVERY only. No provider call, no reserved split, no raw payload written.
Every table in the Luna B evidence document is reproducible from this script.

    uv run python scripts/v7_discovery_screen.py \
        --corpus-root <corpus> --out docs/evidence/<name>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.v7_research.corpus import (  # noqa: E402
    DISCOVERY,
    corpus_paths,
    manifest_digests,
)
from scripts.v7_research.features import FEATURE_VERSION, load_frames  # noqa: E402
from scripts.v7_research.registry import (  # noqa: E402
    CANDIDATE_DEFINITION_VERSION,
    FAMILIES,
    FAMILY_BY_NAME,
    REGISTRY_VERSION,
    digest,
    registry_payload,
)
from scripts.v7_research.screen import (  # noqa: E402
    DEFAULT_SEED,
    SCREEN_VERSION,
    effect_vectors,
    screen_family,
    spearman,
)

#: The serious-candidate set frozen at the end of the discovery phase, chosen
#: *after* the screen ran over the whole universe. Anything not on this list was
#: explored and pruned; the lineage stays in the registry so the later
#: tournament can account for the full multiplicity universe.
#:
#: Three rules did the cutting. Outcome estimands are out: every family whose
#: response was a match result showed almost no between-player heterogeneity
#: (split-half 0.11-0.33), which is the honest reading that whether you win the
#: next game is not a personal trait. Level statistics are out even when they
#: are extremely stable: deaths per ten minutes, involvement per ten minutes,
#: session length and inter-match gap reproduce beautifully but they are
#: population percentiles or calendar facts, not behavioural responses, and
#: two of them are KDA in costume. Redundant restatements are out: first-fight
#: timing and early-fight rate say what the fight-timing centroid already says.
FROZEN_SERIOUS_CANDIDATES: tuple[str, ...] = (
    # History-only families. High structural reach; no parsed dependence.
    "post_loss_session_continuation",
    "post_loss_hero_switch",
    "post_loss_requeue_latency",
    "hero_novelty",
    "transfer_risk",
    "transfer_activity",
    "duration_tempo",
    # Parsed-dependent families. Near-total reach *within* the parsed subset.
    "position_flexibility",
    "fight_timing_centroid",
    "purchase_tempo",
    "lead_retention",
    "lane_recovery_participation",
)


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:  # pragma: no cover - provenance is best-effort
        return "unknown"


def _deep_find(node: Any, key: str) -> Any:
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for value in node.values():
            found = _deep_find(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _deep_find(item, key)
            if found is not None:
                return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--families",
        default="",
        help="comma-separated subset of family names; default is the whole universe",
    )
    parser.add_argument(
        "--skip-redundancy",
        action="store_true",
        help="skip the cross-family redundancy matrix (the slow step)",
    )
    args = parser.parse_args()

    paths = corpus_paths(args.corpus_root)
    frames = load_frames(paths, frozenset({DISCOVERY}), with_parsed=True)

    sampled = len(frames)
    eligible = sum(1 for frame in frames if frame.rows)
    parsed_accounts = sum(1 for frame in frames if frame.parsed)
    truncated = sum(1 for frame in frames if frame.truncated)

    selected = (
        [FAMILY_BY_NAME[name] for name in args.families.split(",") if name]
        if args.families
        else list(FAMILIES)
    )

    results: list[dict[str, Any]] = []
    for family in selected:
        denominator_sampled = sampled
        denominator_eligible = eligible
        if family.parsed:
            denominator_sampled = sampled
            denominator_eligible = parsed_accounts
        result = screen_family(
            family.name,
            frames,
            parsed_dependent=family.parsed,
            arm_family=family.arm_family,
            treated=family.treated,
            control=family.control,
            support=family.support,
            arm_support=family.arm_support,
            denominator_sampled=denominator_sampled,
            denominator_eligible=denominator_eligible,
            seed=args.seed,
        )
        payload = result.as_dict()
        payload["negative_control"] = family.negative_control
        payload["frozen_serious"] = family.name in FROZEN_SERIOUS_CANDIDATES
        results.append(payload)
        print(
            f"{family.name:34s} n={result.opportunities:>7d} "
            f"players={result.players_supported:>3d} "
            f"reach={result.reach_of_sampled:.3f} "
            f"sigma_b={result.sigma_between:.4g} "
            f"rel={result.reliability:.3f} "
            f"sb={result.spearman_brown:.3f} "
            f"({result.seconds:.1f}s)",
            flush=True,
        )

    redundancy: dict[str, dict[str, float]] = {}
    if not args.skip_redundancy:
        vectors: dict[str, dict[str, float]] = {}
        for name in FROZEN_SERIOUS_CANDIDATES:
            family = FAMILY_BY_NAME[name]
            vectors[name] = effect_vectors(
                name,
                frames,
                arm_family=family.arm_family,
                treated=family.treated,
                control=family.control,
                support=family.support,
                arm_support=family.arm_support,
            )
        for left in FROZEN_SERIOUS_CANDIDATES:
            redundancy[left] = {}
            for right in FROZEN_SERIOUS_CANDIDATES:
                shared = sorted(set(vectors[left]) & set(vectors[right]))
                if len(shared) < 20:
                    redundancy[left][right] = float("nan")
                    continue
                redundancy[left][right] = spearman(
                    [vectors[left][key] for key in shared],
                    [vectors[right][key] for key in shared],
                )

    frozen_registry = registry_payload(FROZEN_SERIOUS_CANDIDATES)
    document = {
        "phase": "V7_LUNA_B_FINDING_DISCOVERY",
        "split": DISCOVERY,
        "seed": args.seed,
        "code_sha": git_sha(),
        "feature_version": FEATURE_VERSION,
        "screen_version": SCREEN_VERSION,
        "registry_version": REGISTRY_VERSION,
        "candidate_definition_version": CANDIDATE_DEFINITION_VERSION,
        "corpus": manifest_digests(paths.root),
        "denominators": {
            "discovery_sampled_accounts": sampled,
            "discovery_product_eligible_accounts": eligible,
            "discovery_parsed_accounts": parsed_accounts,
            "discovery_truncated_accounts": truncated,
            "corpus_wide_sampled_accounts": 900,
            "corpus_wide_product_eligible_accounts": 835,
        },
        "full_registry_digest": digest(registry_payload()),
        "frozen_registry_digest": digest(frozen_registry),
        "frozen_serious_candidates": list(FROZEN_SERIOUS_CANDIDATES),
        "screen": results,
        "redundancy_spearman": redundancy,
        "registry": registry_payload(),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {out_path}")
    print(f"full registry digest   {document['full_registry_digest']}")
    print(f"frozen registry digest {document['frozen_registry_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
