#!/usr/bin/env python3
"""Measure the section-6 archetype axes over DISCOVERY and report the grid.

Answers the question the grid has to survive: does ``3 x 3 x 2`` actually
spread people out, or does one cell swallow the corpus? Emits an
**aggregate-only** document — how many players each axis level and each of the
20 archetypes lands on, plus the population cuts used — and never a per-player
row, account or match identifier.

Tempo and fight style need Pass-2 per-event data; the modifier needs the
Pass-1 session history. A player therefore needs both corpora, which in
research means the Pass-2 subset. In production the report fetches parsed
matches for the single player it is about, so the constraint is a research
one, not a product one.

Read-only. No provider call. DISCOVERY only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.v7_research.archetype import (  # noqa: E402
    ARCHETYPE_VERSION,
    FIGHT_STYLE_LEVELS,
    GRID_LABELS,
    MODE_STRATA,
    MODIFIER_LEVELS,
    SPECIAL_LABELS,
    TEMPO_LEVELS,
    ArchetypeError,
    assign,
    measure,
    population_cuts,
)
from scripts.v7_research.corpus import DISCOVERY, corpus_paths, manifest_digests  # noqa: E402
from scripts.v7_research.features import load_frames  # noqa: E402
from scripts.v7_research.pass2_features import (  # noqa: E402
    closer_vs_comeback,
    group_rows_by_account,
    vision_coverage,
)
from scripts.v7_research.pass2_observations import chronological  # noqa: E402
from scripts.v7_research.pass2_tables import (  # noqa: E402
    is_pass2_product_context,
    iter_pass2_players,
)

AXES_RUN_VERSION = "v7-archetype-axes-run-1.0.0"

QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def _quantile(ordered: list[float], q: float) -> float:
    index = min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))
    return ordered[index]


def _describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    out: dict[str, Any] = {
        "n": len(ordered),
        "mean": round(statistics.fmean(ordered), 6),
        "min": round(ordered[0], 6),
        "max": round(ordered[-1], 6),
    }
    for q in QUANTILES:
        out[f"p{int(q * 100)}"] = round(_quantile(ordered, q), 6)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--pass2-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    paths = corpus_paths(args.corpus_root)
    history = {
        frame.pseudonym: frame.rows
        for frame in load_frames(paths, frozenset({DISCOVERY}), with_parsed=False)
    }

    rows = (row for row in iter_pass2_players(args.pass2_root) if is_pass2_product_context(row))
    pass2 = {
        pseudonym: chronological(account_rows)
        for pseudonym, account_rows in group_rows_by_account(rows).items()
    }

    joinable = sorted(set(pass2) & set(history))
    measurements = {p: measure(pass2[p], history[p]) for p in joinable}

    # The two specials reuse dimensions already defined and measured
    # elsewhere rather than inventing a second definition of "wards a lot".
    vision = {}
    closing = {}
    for pseudonym in joinable:
        result = vision_coverage(pass2[pseudonym])
        if result is not None:
            vision[pseudonym] = result.primary.value
        contrast = closer_vs_comeback(pass2[pseudonym])
        if contrast is not None:
            closing[pseudonym] = contrast.primary.value

    # Cuts are per mode stratum: a turbo player is called "early" relative to
    # other turbo players, never against a corpus that is 63% turbo and would
    # otherwise turn every axis into a mode detector.
    cuts_by_stratum = {}
    for stratum in MODE_STRATA:
        members = [p for p in joinable if measurements[p].stratum == stratum]
        if not members:
            continue
        try:
            cuts_by_stratum[stratum] = population_cuts(
                [measurements[p] for p in members],
                vision_coverage=[vision[p] for p in members if p in vision],
                closing_rate=[closing[p] for p in members if p in closing],
            )
        except ArchetypeError:
            continue  # no member of this stratum supports the axes

    archetypes = {}
    for pseudonym, m in measurements.items():
        cuts = cuts_by_stratum.get(m.stratum) if m.stratum else None
        if cuts is None:
            continue
        archetype = assign(
            m,
            cuts,
            vision_coverage=vision.get(pseudonym),
            closing_rate=closing.get(pseudonym),
        )
        if archetype is not None:
            archetypes[pseudonym] = archetype

    tempo = Counter(a.tempo for a in archetypes.values())
    fight_style = Counter(a.fight_style for a in archetypes.values())
    modifier = Counter(a.modifier for a in archetypes.values())
    grid = Counter(
        (a.tempo, a.fight_style, a.modifier) for a in archetypes.values() if not a.is_special
    )
    specials = Counter(a.special_label for a in archetypes.values() if a.is_special)

    unsupported = Counter()
    for m in measurements.values():
        if m.stratum is None:
            unsupported["no_dominant_mode_stratum"] += 1
        if m.impact_centroid is None:
            unsupported["impact_centroid"] += 1
        if m.fight_participation is None:
            unsupported["fight_participation"] += 1
        if m.session_dispersion is None:
            unsupported["session_dispersion"] += 1

    document: dict[str, Any] = {
        "schema_version": AXES_RUN_VERSION,
        "archetype_version": ARCHETYPE_VERSION,
        "split": DISCOVERY,
        "identities_included": False,
        "new_provider_calls": 0,
        "candidate_test_read": False,
        "corpus": manifest_digests(paths.root),
        "denominators": {
            "pass1_discovery_players": len(history),
            "pass2_discovery_players": len(pass2),
            "joinable_players": len(joinable),
            "players_with_an_archetype": len(archetypes),
        },
        "axis_without_support": dict(unsupported),
        "population_cuts_by_stratum": {
            stratum: cut.as_dict() for stratum, cut in sorted(cuts_by_stratum.items())
        },
        "players_by_stratum": {
            stratum: sum(1 for m in measurements.values() if m.stratum == stratum)
            for stratum in MODE_STRATA
        },
        "archetypes_by_stratum": {
            stratum: sum(1 for a in archetypes.values() if a.stratum == stratum)
            for stratum in MODE_STRATA
        },
        "axis_distributions": {
            "impact_centroid": _describe(
                [m.impact_centroid for m in measurements.values() if m.impact_centroid is not None]
            ),
            "fight_participation": _describe(
                [
                    m.fight_participation
                    for m in measurements.values()
                    if m.fight_participation is not None
                ]
            ),
            "deaths_per_fight_minute": _describe(
                [
                    m.deaths_per_fight_minute
                    for m in measurements.values()
                    if m.deaths_per_fight_minute is not None
                ]
            ),
            "session_dispersion": _describe(
                [
                    m.session_dispersion
                    for m in measurements.values()
                    if m.session_dispersion is not None
                ]
            ),
        },
        "axis_levels": {
            "tempo": {level: tempo.get(level, 0) for level in TEMPO_LEVELS},
            "fight_style": {level: fight_style.get(level, 0) for level in FIGHT_STYLE_LEVELS},
            "modifier": {level: modifier.get(level, 0) for level in MODIFIER_LEVELS},
        },
        "grid": {
            GRID_LABELS[key]: grid.get(key, 0)
            for key in sorted(GRID_LABELS, key=lambda k: GRID_LABELS[k])
        },
        "specials": {label: specials.get(label, 0) for label in sorted(SPECIAL_LABELS.values())},
        "grid_cells_occupied": sum(1 for key in GRID_LABELS if grid.get(key, 0) > 0),
        "largest_cell_share": (round(max(grid.values()) / sum(grid.values()), 6) if grid else 0.0),
    }

    serialized = json.dumps(document, indent=2, sort_keys=True)
    if "v7p_" in serialized:
        raise RuntimeError("a player pseudonym reached the archetype output document")
    Path(args.out).write_text(serialized + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(
        f"archetypes: {len(archetypes)} of {len(joinable)} joinable players; "
        f"{document['grid_cells_occupied']}/18 cells occupied; "
        f"largest cell {document['largest_cell_share']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
