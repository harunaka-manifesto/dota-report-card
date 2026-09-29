# Achievements backend QA — merged report (2026-09-29)

- Branch: `codex/achievements-backend`, base 3b7c30d, head 52d2c83. The head did not change during the review.
- Eight independent tracks (A–H) reviewed the branch. Nothing was fixed, committed, merged or deployed.
- Provider traffic: 0 OpenDota calls, 0 STRATZ calls, 0 parse requests.
- `git status` is clean. All scratch tests were deleted from the repo; copies are in this folder: `test_zzqa_*.py` and `trackG/`.

Legend: [C] = confirmed by a reproduction. [S] = suspected, based on reading the code only. Track IDs in brackets show where each finding came from; duplicates across tracks are merged into one entry.

## BLOCKER

**1. #4 is awarded twice to the same hero through a different metric [C]** (C-1, A-12, G-1)
- Location: `achievements.py:105-115`.
- The qualifying check runs per (metric, hero). It never checks whether this hero has already earned #4.
- Reproduction: hero 99 earns #4 on camps_stacked in match 6, then earns #4 again on fight_presence in match 7.
- This contradicts the handoff doc (line 39, "Each additional new hero can earn it once") and locked decision 4 ("once per new hero").
- Fix: exclude heroes found in prior `awards[id==4].proof.hero_id`.
- If the owner actually intends per-(metric, hero) repeats, this is not a bug and the docs are wrong instead.

## HIGH

**2. #25 gold-clock origin rejects the only recent real OpenDota parse in the repo [C]** (B-1, re-verified by me)
- Location: `materialization.py:83`, `achievements.py:70`.
- The code requires `radiant_gold_adv[0] == 0`. In the paired-replay fixture, `adv[0]` is 403, which equals Σradiant `gold_t[0]` − Σdire `gold_t[0]`. So index 0 is a real reading at 0:00, not a misaligned clock.
- Result: #25 is EVIDENCE_MISSING on that match.
- If this data shape is common, the Epic #25 badge is effectively unearnable. Its rate of 4.27% would then have been measured under different conditions.
- Owner action: check the index-0 distribution in the corpus.
- Fix: validate the origin against `gold_t[0]`, or drop the "equals 0" requirement.

**3. The FEATURE_VERSION bump strands in-flight finalizations [C]** (B-2)
- Location: `finalization.py:88-111`, which only accepts features at the current FEATURE_VERSION.
- Links materialized as `tracker-features-4` before deploy hit "Terminal match has no retained feature projection". After 5 retries they end up ACTION_REQUIRED/INTERNAL_FAILURE, and a user Retry cannot recover them.
- Fix: rematerialize from the stored snapshot, the same provider-free path that `rebuild_inputs` uses.

**4. Standard role correction leaves PB pointers for other roles aimed at superseded analyses [C]** (C-2)
- Location: `role_correction.py:209-212` rebuilds every role, but lines 242-244 recompute PBs only for `{previous, new}`.
- Effect: `owns_personal_best` becomes false for PB matches in any third role.
- Fix: call `recompute_indexes(roles=None)` for Standard corrections.

**5. #30 proof names one feat but gives another feat's count [C]** (D-1)
- Location: `achievements.py:264`. `feat_id` is the lowest qualifying id, while `distinct_matches` is `best` across all feats.
- Reproduction: proof reads `{feat_id: 14, distinct_matches: 5}`, but #14 was earned in only 3 matches.
- Fix: pick the feat first and report that feat's own count. This changes rule output, so bump the rule version.

**6. Ineligible Standard matches show AVAILABLE with empty earned and unavailable lists [C]** (A-1, D-4, G-4, F-5)
- Affected matches: leaver, abandon, under 10 minutes, integrity-invalid, or role unassigned.
- Location: `achievements.py:84` returns empty lists, and `mobile_api.py:1653` then reports AVAILABLE. The `match_states.json` golden already shows this for `<ref:5>`.
- This violates locked decision 8.
- Fix: return UNAVAILABLE when `progression != "STANDARD"`, or emit a new reason such as `MATCH_INELIGIBLE`.

**7. #30 progress in the collection comes from the latest match only [C]** (A-2, D-2, C-5, F-1, G-2)
- Location: `mobile_api.py:849-851` (last row wins) together with `achievements.py:257-263` (only feats earned in the current match are counted).
- Effect: a match with no feat, or a match on another hero, resets progress. For example, 2/3 becomes 1/3 or 0/3.
- Fix: compute progress at read time as the maximum over (hero, feat) across visible current analyses.

## MEDIUM

**8. #4 progress lags one match [C]** (A-3, D-3, G-3)
- Location: `achievements.py:110`. The current match's PBs are excluded.
- Fix: compute at read time, together with #7.

**9. Rule changes are never detected as stale, and readers ignore `rule_version` [C]** (C-3, D-9)
- `stale_analysis` does not look at RULE_VERSION or `rules_digest`.
- Collection and Match Detail check only that the `achievements` key exists.
- The docstring in `achievement_rules.py` promises a replay path that does not trigger.

**10. A live match finalized after a version bump, before the methodology rebuild, sees mixed-version history [C]** (C-4)
- #30 counts awards from old-version analyses.
- #1/#2/#4 report INSUFFICIENT_HISTORY, and the missed celebration is never replayed.
- This conflicts with §14.3.
- Fix: filter `prior_award_rows` by version, or hold Standard finalization while the profile has stale analyses. Also make the rebuild a required deploy step.

**11. Real zeros are reported as EVIDENCE_MISSING [C]** (A-4, A-5, G-6)
- Team kills below 10 makes #13/#41/#42 unavailable, even though evidence is present.
- Zero team tower damage makes #11/#44/#45 unavailable.
- Awards are never wrong here, but the reasons and rarity denominators are.
- #41 and #42 silently reuse #13's `team_kills_min`.

**12. A kill log shorter than the summary kill count is treated as complete [C]** (A-11, B-3)
- Location: `materialization.py:55-57` withholds the log only when it has more entries than the summary.
- Effect: #17 becomes "not earned" instead of unavailable, and #18 undercounts. This contradicts the handoff doc.
- The deaths check uses strict equality, so the two checks are inconsistent.

**13. `rules_digest` is incomplete and contains a dead key [C]** (A-7, A-8)
- The digest omits `ROLES` gates, the #1/#2/#4 counts, peer positions 2/3, #25 `FAVORABLE`, and checkpoint seconds.
- `THRESHOLDS[22]["separate_fights"]` is never read.

**14. The collection reports AVAILABLE while the first or Pro history import is still running [C]** (D-5)
- The `new_user_importing` and `pro_importing` goldens show this.
- Mastery reports BACKFILLING in the same situation.

**15. Performance on long histories [C]** (G-5, B-4, C-7, D-10)
- `prior_award_rows` loads full `analyses.result` for every prior match, which is O(N²) across a closure replay.
- The Standard correction closure now covers all roles.
- `correction_available` loads the full snapshot payload for every later link.
- Measured costs:

| Operation | History size | Time |
|---|---|---|
| `correct_role` | 400 matches | 19.7 s |
| `correct_role` | 1,000 matches | 73 s |
| `GET /matches/{earliest}` | 2,000 matches | 25.6 s |
| Collection | 2,000 matches | about 0.1 s |
| Finalize | 2,000 matches | 0.9 s |

**16. Coalesced notification bundles repeat ids across matches [C]** (E-1)
- Example: `[14,15,18,14,15,18]` with count 6 and "+5 more".
- The owner needs to choose: a union of ids plus a total count, or a per-match map. Then document it.

**17. The notification badge name is always English [C]** (E-2, F-6)
- Location: `notifications.py:21`.
- Fix: send the rarest badge id and let the client localize it.

**18. Stale docs [C]** (F-7, F-8, F-9, H-1, D-9)
- These docs still say no achievement contract exists:
  - `docs/tracker/README.md:51`
  - `architecture/README.md:193`
  - `MOBILE-API-DRAFT.md:63`
- The handoff doc is out of date:
  - It still describes provisional rarity and `local-standard-estimate-1`.
  - It lists old tiers: #11 Rare, #23 Epic, #42 Rare.
  - It says "uncommitted".
  - It says "OpenDota QA calls 0", while the ledger records 1,352.
  - It says "no Achievements section" in Figma.
- `achievement_catalog.py:42` still has the comment "tiers stay provisional".
- The ledger's "Open before enabling public awards" item is not closed.
- The review note, lines 3, 40 and 107, still says "provisional".
- There is no feature SSOT and there are no traceability rows for achievements.

**19. The role-correction flow test asserts nothing [C]** (F-2, C-8)
- Location: `test_achievements_flow.py:76` compares match-id keys only.
- The correction actually removes #4, and the test would still pass.

## LOW
- #41 reports EVIDENCE_MISSING instead of MATCH_TOO_SHORT for matches under 20 minutes (A-6).
- The #4 proof lists metrics that are not new-hero records, and can include the current hero (A-9).
- #18 is not gated by a quarantined death count (A-10, B S-2).
- A `hero_id` quarantine does not gate #4/#30 (A-13).
- A fresh match can be folded into an old bundle and cancelled at MAX_AGE (E-3).
- An unknown locale returns 422 (FastAPI shape) instead of falling back (D-6).
- Proof templates include raw ids, ratios and objects that are not displayable, and only `{feat_name}` is documented (D-7).
- `rarity` and `progress` are untyped in OpenAPI (D-8).
- `achievement_source` indexes players by position, not by slot (B-5).
- The methodology rebuild never settles when stale links are hidden by scope; this predates the branch (C-6).
- Rule tests only cover positive cases, with no below-threshold checks (F-3).
- The Figma rows show no catalog ID or key (H-2).
- The notification payload has no size cap, and APNs encoding is untested (E-6).

## NIT
- #45 has no absolute tower-damage floor; this is a design question (A-14).
- Negative values pass the evaluator but are guarded upstream (A-15).
- Loose `==` and float checks for observer kills; `stuns` has no upper bound (B-6).
- Unmeasured history badges always sort last within their tier (E-4).
- Goldens were edited in place; acceptable before merge only (F-10).
- A `hero_id` of None is not failed closed, but the schema blocks it (G-7).
- Figma layer names do not match the visible text, and #4/#30 progress is not noted (H-3, H-4, H-5).
- The pending push payload is frozen at READY time; this is accepted by §4.7 (E-5).

## Refuted
- F-4 (Pro-scope history never recomputes #30): Tracks C and G showed that the scope rebuild does recompute #30 quietly.
- Owner question: #30 earned from pre-link history disappears on Pro→Free. Is that the intended user experience?

## Checked and correct (summary)
- **Provider I/O:** the diff adds no provider I/O, and runtime `provider_calls` is 0 throughout.
- **STRATZ:** STRATZ-sourced snapshots produce None evidence, not zero.
- **Hostile payloads:** 3,000 fuzzed payloads caused no crash and no bad counter.
- **Immutability:** immutable feature and snapshot tables have triggers, and the digest is idempotent.
- **Thresholds:** all threshold comparisons are inclusive and match the review note.
- **#25 gold clock:** apart from the index-0 issue (#2 above), the sign flip, the "strictly before fight start" rule and contiguity are correct.
- **Other badge logic:** the #8/#11 peer gate, #17 sliding window, #22 non-overlap and #30 base exclusions (#4, #30, #42) are correct.
- **Locking and publishing:**
  - Lock order is correct.
  - Chronology tie-break is correct.
  - Retry is idempotent.
  - Awards publish in one transaction, with no partial Stage-1 award.
- **Quiet paths:** late import triggers a quiet CLOSURE_REBUILD. Free→Pro→Free, role correction and methodology rebuild are all quiet.
- **Turbo:** Turbo is excluded everywhere.
- **Personal bests:** the PB tie rule and the 5-prior gate are correct.
- **Delete and relink:** deleting and relinking Steam behaves correctly.
- **Auth:** 401s and 404s are correct, and there is no cross-account leak.
- **Response fields:**
  - `order` runs 1–24.
  - Rarity appears only after the first earn.
  - Tiers come from `BADGE_TIERS`.
  - Progress is exposed only for #4/#30.
- **Copy:** placeholder coverage is complete for EN and ID, and no forbidden vocabulary appears.
- **Contract drift:** there is no OpenAPI or golden drift.
- **Notifications:** notifications fire only on READY and only for live matches; historical imports are silent. The rarest badge is chosen by tier, then rate, then id. Dedup key is correct.
- **Figma:** 24 rows, Badge 01–24 in ascending catalog-ID order, frozen tiers, and EN/ID text that matches `COPY` exactly (hash-verified).
- **Legacy:** no shared or legacy paths were touched, and the V6.1 package verifies.

## Gates (Track F, head 52d2c83)

| Gate | Result |
|---|---|
| `pytest -q -p no:cacheprovider --ignore-glob='*test_zzqa_*'` (full repo, including legacy) | 1900 passed, 6 skipped, exit 0 (9 min 17 s) |
| Migrations (`RUN_POSTGRES_MIGRATION_TEST=1`, integration and legacy integration) | 9 passed |
| `ruff check …` | All checks passed |
| `mypy` | Success, 321 files |
| `scripts/check_docs.py` | ok (85 docs, 620 links) |
| `legacy/scripts/check_legacy_docs.py` | ok (27) |
| `tracker_traceability.py --strict` | exit 0 (no rows for achievements) |
| `git diff --check` | clean |
| taxonomy-validate, dna-catalog-check, api-client | ok, no drift |
| V6.1 verify | sha256 `22206d20…58f9` ok |
| CI web job | not run; web is untouched |

## Counts
BLOCKER 1 · HIGH 6 · MEDIUM 12 · LOW 13 · NIT 8

## Verdict: NO
Before the branch is ready to finalize:
1. The owner rules on #4 semantics (#1).
2. Fix #2–#7 and the progress items (#8).
3. Add staleness/version handling for rule and feature bumps (#9, #10).
4. Clean up the docs (#18).
5. Strengthen the correction test (#19).
6. Treat the performance issues (#15) as a pre-launch condition, because correction is a synchronous request path.
