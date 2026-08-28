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

The Death Context reuse layer is kept in the execution worktree at:

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

The pilot leaves blocked analytical outputs in
`.local/diagnostics/free-dna-death-context-local-reuse-pilot/` rather than
fabricating player estimates. A future supplement must use the frozen panel,
request only its missing detail bodies, and obtain fresh owner approval.

## Future uses

Allowed: offline schema/semantics QA, bug investigation, descriptive Tier-2
research, approved calibration research, and provider-comparison research.

Forbidden: provider relabeling, validation unsealing, holdout reuse, outcome-
based replacement, changing historical provenance, or production analytical
changes.
