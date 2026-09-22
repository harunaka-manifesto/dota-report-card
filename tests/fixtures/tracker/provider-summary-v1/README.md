# Provider summary specimens, version 1

Sanitized subsets of retained 2026-09-20 live acquisition responses in the
ignored OpenDota architecture investigation. No new provider calls.

`paired-players.json` contains 13 same-match, same-slot, same-hero player pairs
from OpenDota account history and STRATZ deep match responses. A field allowlist
removes account/match identifiers, names, ranks, provider scores and unrelated
content. Missing and null fields remain absent/null. These prove only the
jointly present summary values, not ten-player replay parity.

`unparsed-match.json` preserves the ten-player summary shape of a real response;
its match ID is synthetic and all player identity fields are removed. It is a
summary normalization specimen, not proof of replay-field equivalence. Expand
with new versioned specimens; do not overwrite these when contracts change.
