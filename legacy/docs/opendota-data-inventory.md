# OpenDota data inventory

Free DNA uses the public profile plus one previous-365-day
/players/{account_id}/matches history window. Normalized fields include timing,
duration, hero, side/result, kills, deaths, assists, and nullable role hints.
Missingness is preserved through every stage.

Free does not call /matches/{match_id} and does not request replay parsing.
Detail payloads, timelines, items, teamfights, objectives, drafts, and chat
belong to explicit Deep Scan work.

Summary fields are source observations, not replay-verified facts. lane_role,
patch, skill, and similar labels remain hints with documented confounders.

| Product path | Reads | Public result |
|---|---|---|
| Free DNA | One previous-365-day summary-history request | 18 Elements, 11 Patterns, Hero Portfolio, story, share |
| Deep Scan | Explicit detail requests | Separate detailed evidence report |
| Replay parse | Zero in Free | Never assumed available |
| Free DNA V6.1 | One physical previous-365-day summary-history request with the canonical 20-field projection | 7 Elements, 5 family roots, up to 3 corrected semantic outcomes |

See [data provenance](architecture/data-provenance.md) for storage and privacy.

V6.1 records whether the 10,000-row transport ceiling was reached; that state
means possibly truncated, not complete. Optional `version`, `party_size`,
`hero_variant`, `lane`, `lane_role`, and `is_roaming` context needs at least
80% coverage for public use. Rank/MMR/skill-bracket fields are forbidden.
