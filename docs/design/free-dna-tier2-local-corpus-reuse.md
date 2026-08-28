# Free DNA — Tier-2 Local Corpus Reuse

## Purpose

This convention lets Death Context research reuse retained OpenDota data
without copying raw bodies or making provider calls. It is research-only and
does not alter production reports, V6.1 artifacts, thresholds, or contracts.

## Source and output layers

The source campaign is the 2026-08-28 V6.1 Session Drift expansion:

- provider: OpenDota;
- raw corpus: `.local/corpora/opendota/v61-session-drift-expansion/raw/`;
- normalized summary corpus: `.local/corpora/opendota/v61-session-drift-expansion/normalized/`;
- source raw digest: recorded in the local pilot manifest;
- source normalized digest: recorded in the local pilot manifest; and
- source marker: exact `source_version == "22"`.

The Death Context reuse layer is kept in the canonical repository-local
ignored storage root at:

```text
.local/corpora/opendota/free-dna-tier2/
├── manifests/
├── normalized/
└── derived/
```

Raw responses are referenced by immutable path and SHA-256; they are not
copied. Normalized records are one record per available parsed detail and keep
the provider, source campaign, source body digest, match identity, slot,
hero, role, side/result, duration, patch, total deaths, indexed teamfight
deaths, teamfight windows, gold-advantage series, parse marker, and field-shape
audit. Missing and null values remain explicit.

## Privacy and provenance

- Local manifests and normalized records are mode `0600`; containing
  directories are mode `0700`.
- The new panel salt is 32 random bytes and only its SHA-256 digest is recorded
  in manifests. The salt itself is never tracked.
- Local detail indexes may retain private match/profile identities for
  reproducibility. Tracked reports contain aggregates and digests only.
- OpenDota data remains OpenDota data and is never relabeled as STRATZ.
- Sealed-validation and old-holdout records are excluded; validation metadata
  is not treated as an analytical result.

## Reuse decision recorded on 2026-08-28

The source corpus contains 19 parsed detail bodies. The deterministic
32-profile/960-match panel selected from development summary rows has zero
body matches in that local detail set. Therefore the local layer is reusable
for shape, provenance, and future offline research, but is not sufficient for
the registered Death Context outcome analysis.

The overnight live supplement on 2026-08-29 made 60 direct detail GETs before
stopping on one HTTP 500. It retained 59 new raw responses and normalized
them alongside the 19 earlier referenced records, for 78 total normalized
records. The frozen 960-detail panel remains incomplete, so no player
estimates or analytical outcome results were generated. The local live
diagnostics record `PILOT_COLLECTION_BLOCKED`; the remaining 900-call budget
was not used.

The canonical corpus manifest records normalized digest
`09b7322304a001e2fe08e84f742f5e66da15eb5aa97b2dcf235be73f2b6223c3` and
manifest SHA-256
`0aa3b41f89812dbced0d8dda138d00845e3b8db4aa25e49091755635e9c2f7b8`.
The corpus remains reusable for offline schema QA and future research, but it
does not authorize retrying this campaign. Any future supplement must use a
newly named, separately approved campaign and preserve this ledger as
historical provenance.

## Future uses

Allowed: offline schema/semantics QA, bug investigation, descriptive Tier-2
research, approved calibration research, and provider-comparison research.

Forbidden: provider relabeling, validation unsealing, holdout reuse, outcome-
based replacement, changing historical provenance, or production analytical
changes.
