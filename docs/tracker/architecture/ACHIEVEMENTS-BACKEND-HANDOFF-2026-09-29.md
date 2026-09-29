# Match achievements backend handoff — 2026-09-29

This is a continuation note for the work Sol started on the 24-match achievement MVP. It records the current checkout, the owner's decisions, the implementation that exists, and the work that must happen before this branch is reviewable or safe to merge. It is a handoff, not an approved product SSOT or a release authorization.

## Status at a glance

- Branch: `codex/achievements-backend`.
- Checkout: `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`.
- Base/HEAD at handoff start: `3b7c30d` (`main` and `origin/main`). The achievement implementation is currently **uncommitted**.
- No migration was added. No deployment, merge, push, production flag, or provider call happened.
- OpenDota QA/calibration calls made for this implementation: **0**.
- Local lint, mypy, `git diff --check`, and the isolated achievement unit tests pass.
- A PostgreSQL-focused checkpoint before the latest small edits passed **33 tests, 1 skipped**. The new API collection test has not completed a PostgreSQL run after the latest edits because the approval runner hit the account usage limit. Treat the database/API work as needing another run.
- Figma was inspected read-only. The linked Content bank was not changed.

The current worktree also contains an earlier untracked research note, [`achievement-feasibility-2026-09-28.md`](evidence/achievement-feasibility-2026-09-28.md). Decide deliberately whether to commit that evidence with the handoff; it is not part of the implementation commit yet.

## Read these first

1. Root `AGENTS.md`.
2. [Tracker foundation SSOT](../app_foundation/SSOT.md).
3. [Tracker architecture](README.md), its ADRs, and the [implementation ledger](IMPLEMENTATION-LEDGER.md).
4. [Mobile API contract](../api/README.md).
5. [Achievement feasibility evidence](evidence/achievement-feasibility-2026-09-28.md).

Do not use `legacy/` as tracker product truth. Shared runtime changes still affect the live legacy product and require its release gates before merge.

## Owner decisions that are already locked

These came from the owner's implementation-planning answers and must not be reopened casually:

- The launch catalog is IDs **1, 2, 4, 6, 8, 10, 11, 13, 14, 15, 17, 18, 20, 22, 23, 25, 30, 37, 41, 42, 44, 45, 49, 50**.
- Standard matches only at launch. Turbo is ineligible.
- A loss can still earn a badge when the factual rule qualifies.
- All qualifying identities are awarded and shown, including nested/overlapping badges.
- Awards publish together at the existing single READY finalization point. There is no partial Stage 1 achievement award.
- Free and Pro use identical rules and collection access. The visible history, counts, and cross-match progress use the existing entitled-history scope, so expiry can reduce what is visible without deleting retained evidence.
- These match medals are separate from Role Mastery/progression medals. The Role Mastery Free Level 5 display cap remains unchanged; this collection has no level cap.
- #4 repeats when the same role-metric PB is set on a new distinct hero. Each additional new hero can earn it once; several qualifying metrics in one match still produce one #4 award.
- #30 is the same non-Common single-match feat on the same hero in three distinct Standard matches. The third and later qualifying match count. Roles may differ. #4 and #30 cannot be the repeated base feat.
- Rarity denominator: evaluable, eligible Standard player-matches in the badge's permitted roles. Bands are Common `>=20%`, Rare `5%–<20%`, Epic `1%–<5%`, Legendary `<1%`. Empty buckets are allowed.
- Unearned entries hide tier and numeric rarity. Earned entries may show a provisional estimate. #4/#30 are the only planned progress displays; single-match badges do not expose progress.
- Proof is factual and match-linked. Unearned entries get a general hint without exact numeric thresholds.
- Later PBs do not erase an earned-at-the-time badge. Role correction, entitlement scope changes, retained-data rebuilds, and future rule revisions recompute current truth from evidence without replaying old celebrations.
- Historical imports/backfills are quiet: no per-match achievement alerts. A live READY notification can name the rarest earned badge and `+N more`; a coalesced bundle uses the total count.
- Runtime achievement evaluation must add **zero** OpenDota/STRATZ calls and zero parse requests. Optional calibration reads are allowed only for a demonstrated gap and must stay below the owner's hard cap of **Rp10,000 all-in**, with every read/parse/poll counted.
- Backend code and EN/ID copy bank entries are in this phase. Native screens, Spline assets, share-card design/rendering, and share endpoints are later work.

## What Sol has implemented

### Evaluator and retained evidence

- [`services/api/app/tracker/achievements.py`](../../../services/api/app/tracker/achievements.py) contains the Standard-only evaluator, stable IDs, role gates, compact proof, cross-match history lookup, and `RULE_VERSION = "match-achievements-v1"`.
- Missing facts fail closed; a legitimate numeric zero remains usable. The evaluator returns `awards`, `evaluable_ids`, PB metric IDs, and #4/#30 progress.
- [`materialization.py`](../../../services/api/app/tracker/materialization.py) is now `FEATURE_VERSION = "tracker-features-5"`. It retains:
  - OpenDota credited observer-kill totals only when they match the player's credited observer-ward map;
  - OpenDota `stuns` as recorded disable seconds;
  - validated hero-kill timestamps for #17/#18, withheld when the log contradicts the summary kill count;
  - the raw `radiant_gold_adv` minute map for #25;
  - the existing replay checkpoints, event streams, and fight inputs.
- The current corpus checks found observer-kill totals matching the credited observer-ward map for **9,600/9,600 player rows** and numeric `stuns` for **9,600/9,600 rows** in the 960-match parsed Standard holdout. The kill log had summary-count contradictions in 232 rows, so those rows correctly lose #17/#18 evidence instead of being guessed.
- The implementation reuses the existing detected-fight validator and keeps fight awards core-only (#20/#22/#23/#25).

### Finalization and rebuild path

- [`finalization.py`](../../../services/api/app/tracker/finalization.py) now uses `ANALYSIS_VERSION = "tracker-analysis-8"` and evaluates achievements inside the existing ordered, profile-locked finalization transaction.
- The immutable `analyses.result` contains an `achievements` object and `achievement_pb_metrics`; no achievement ledger/table was added.
- Current counts are derived from visible Standard links and their active analyses. This is intentionally simple, but the collection read is an all-visible-ready-history scan; add a summary table only if measurement shows it is necessary.
- PBs use the existing five-prior gate. The evaluator records strict PB metrics before evaluating #1/#2/#4.
- Standard role correction was widened to rebuild all later Standard links across roles, because #30 can repeat across roles. Turbo keeps the prior role-limited closure.

### Catalog, rarity, and copy

- [`achievement_catalog.py`](../../../services/api/app/tracker/achievement_catalog.py) has all 24 EN/ID names, descriptions, general hints, factual proof templates, machine keys, and future Spline asset keys.
- Current English working names are: Double Record; Clean Sweep; Record on a New Hero; Two Clocks Ahead; 20-Minute Turnaround; Gold Engine; Mid Advantage, Real Siege; Relentless Presence; Untouchable Contributor; Flawless Finisher; Five in a Flash; Early Duelist; Fight Closer; Damage Anchor; Clean Teamfight; Behind but Fighting; Hero Specialist; Vision Double Duty; Camp Architect; Support Everywhere; Offlane Siege; Siege without Dying; Healing Hand; Control Specialist.
- `RATE_COUNTS` is a local, provisional rarity snapshot (`local-standard-estimate-1`), not population truth. It uses the 960-match parsed Standard holdout where fields are available and a smaller parsed discovery sample for net-worth/death-log rules.
- Current provisional tiers are: #6 Epic, #8 Epic, #10 Epic, #11 Rare, #13 Epic, #14 Legendary, #15 Legendary, #17 Epic, #18 Rare, #20 Rare, #22 Rare, #23 Epic, #25 Epic, #37 Rare, #41 Epic, #42 Rare, #44 Rare, #45 Legendary, #49 Rare, #50 Rare. #1, #2, #4, and #30 have no static rate yet.
- `REPEATABLE_IDS` currently derives from IDs with a rate estimate and excludes unknown-rate/common-history bases. This must be reviewed before freezing #30's eligible feat list.
- The starting thresholds are currently code literals in `achievements.py`; there is no standalone reviewed/frozen rule artifact yet. Extract one before enabling public awards.

### Mobile API and notifications

- [`mobile_api.py`](../../../services/api/app/tracker/mobile_api.py) adds:
  - `GET /achievements?locale=en|id` for the 24-entry collection;
  - `GET /achievements/{achievement_id}?locale=en|id` for one entry;
  - Match Detail `achievement_state` and earned award IDs/proof.
- Collection entries include machine key, asset key, role scope, copy, earned count, latest one earned match, #4/#30 progress, and rarity only after the first earn. The API defaults to English and is authenticated/account-scoped.
- [`notifications.py`](../../../services/api/app/tracker/notifications.py) extends the existing grouped READY payload with `achievement_ids`, `achievement_count`, `achievement_name`, and `achievement_more` while preserving event/outbox coalescing and live-only notification behavior.
- There is no achievement share endpoint or image renderer in this phase.

### Tests added or changed

- [`tests/tracker/test_achievements.py`](../../../tests/tracker/test_achievements.py) covers each ID with recorded-shaped data, Standard/Turbo, missing versus zero, overlap, non-overlapping fights, catalog coverage, ward-count validation, and gold-advantage translation. Latest run: **27 passed**.
- Existing notification tests were updated for the grouped achievement payload.
- A mobile collection/scope test was added to `test_mobile_api.py`, but it still needs a PostgreSQL-backed run after the latest edits.

## Local corpus and economics context

- The authorized local OpenDota corpus contains 960 unique full ten-player parsed Standard matches in the holdout set. It is a selected research corpus, not a population sample and not a license to commit raw provider data or identifiers.
- The feasibility note's original screening used 100 parsed mixed-mode matches / 1,000 player rows for qualitative incidence. The current evaluator calibration used the larger 960-match set where the required fields were present.
- All selected rules use existing OpenDota summary data or the same already-planned parsed match response. No achievement-specific runtime request, parse request, or STRATZ dependency was added.
- OpenDota's parse endpoint may consume rate-limit units, but this implementation makes no calls. Do not spend the Rp10,000 allowance just to validate UI, wiring, or fixtures.

## What is still pending or unsafe

1. **Freeze the contract before enablement.** Review every threshold against qualifying examples and the held-out corpus. Move thresholds and the #30 repeatable-feat list into a reviewed, versioned rule artifact. Hold a badge if its evidence cannot support the wording.
2. **Validate #25 clock alignment.** The current code accepts the retained minute gold map but does not yet enforce a complete origin/interval/last-real-checkpoint contract. Validate missing, nonzero-origin, short, and fight-boundary cases before enabling #25.
3. **Review #8 role-peer semantics.** The current evaluator selects Mid position 2 and Offlane position 3. Confirm that this is the approved unique enemy effective-role peer under the actual role assignment, rather than silently assuming a position.
4. **Make readiness explicit.** Match Detail currently returns a state but no achievement-specific reason/unavailable dependency list. Unsupported evidence should remain visibly unavailable, not look like an empty earned list.
5. **Backfill existing analyses quietly.** `ANALYSIS_VERSION`/`FEATURE_VERSION` changes make old analyses stale. Wire and run the provider-free methodology/rebuild path for retained eligible Standard matches, then verify #4/#30 chronology, Free→Pro→Free scope changes, role correction, late imports, and idempotent retry. Do not replay notifications.
6. **Add end-to-end fixtures.** The unit test calls the evaluator directly and the collection test manually edits an analysis result. Add a finalizer-backed production-shaped fixture that earns overlapping badges from retained source data, then reads Match Detail, collection, detail, notification, and rebuild outputs without provider I/O.
7. **Update tracker SSOT/docs.** Clarify in foundation/onboarding language that this match-achievement collection is separate from the Role Mastery Level 5 cap, document quiet historical backfill, and add the final rule/rarity version references to the implementation ledger and API docs.
8. **Update the Figma Content bank.** The target file is [Report](https://www.figma.com/design/D3uhn7WPXFsX1DiCIVklyg/Report?node-id=575-4018&p=f&t=SmoVKTLwehXAQCIe-11), page/node `575:4018`. The current bank has EN/ID tables and Friendly teammate voice but no Achievements section. Before any write, reread the `figma-use` skill, inspect the current page, then add the matching 24 EN/ID entries and return mutated node IDs.
9. **Regenerate and verify the mobile OpenAPI golden.** The public contract changed; run the repository's tracker OpenAPI export and golden tests after the response shape is finalized.
10. **Run all release gates.** At minimum: full `tests/tracker`, migration tests, `scripts/tracker_traceability.py --strict`, `make lint`, `make typecheck`, `make docs-check`, and the legacy/shared gates required by `AGENTS.md`. No merge/deploy is authorized by this note.

## Verification commands and current evidence

The temporary local PostgreSQL test cluster used during the prior run was:

```bash
TEST_POSTGRES_URL='postgresql+psycopg:///dota_tracker_test?host=/private/tmp/dota-pg-socket&port=55434'
```

The cluster is disposable and may not survive the session. The repository fixtures also require Redis for the full tracker suite.

Verified after the latest edits:

```text
27 passed — tests/tracker/test_achievements.py
ruff — affected implementation and test files pass
mypy — affected implementation modules pass
git diff --check — pass
```

Verified at the preceding PostgreSQL checkpoint, before the latest API/catalog edits:

```text
33 passed, 1 skipped — focused finalization/materialization/mobile/notification/role-correction tests
```

The follow-up PostgreSQL run for the new collection test was not completed because the approval service hit the account usage limit. Run it again when the test database is available. The full tracker suite, OpenAPI golden, docs-check, and legacy release gates remain unrun for this branch.

## Safe continuation order

1. Re-read this note and the SSOTs; inspect `git status` before editing.
2. Fix the evidence/readiness issues above and add finalizer-backed fixtures.
3. Freeze the rule artifact and provisional rarity snapshot only after corpus review; keep unsupported badges unavailable.
4. Implement quiet provider-free backfill/rebuild and verify entitlement/role-correction chronology.
5. Update API docs, SSOT wording, implementation ledger, Figma Content bank, and OpenAPI golden.
6. Run focused tests, then all tracker/shared/legacy gates. Do not make provider calls for QA.
7. Commit the validated branch and return the required `AGENTS.md` completion report. Do not merge, deploy, or enable public awards without an explicit owner request.

## Required completion report when implementation resumes

The final agent must report the fields required by root `AGENTS.md`, including base/new SHA, changed files, backend/public-contract status, persisted-report compatibility, production-shaped fixture, typecheck/lint/build, analytical behavior, holdout rerun, recalibration, exact OpenDota QA call count, deployment status, and `SAFE TO MERGE`.

## Continuation status (2026-09-29, second session)

Done: frozen rule artifact (`achievement_rules.py`, digest pinned); #25 gold-clock contract; #8/#11 own-position + unique-peer gate and reworded #8 copy (role counterpart, not lane); `achievement_unavailable` reasons on Match Detail; finalizer-backed fixtures (`test_achievements_flow.py`, rewritten collection test); quiet backfill verified through the existing methodology rebuild; API/SSOT/ledger docs; OpenAPI export and new golden `mobile-v1-match-achievements-v1`. Gates: full suite 1,898 passed / 6 skipped, ruff, mypy, docs-check, traceability `--strict`, `git diff --check`.

Figma Content bank section added (frame `659:666`). Still open: reviewed production rarity snapshot, per-threshold corpus review before public awards are enabled, and the owner's merge/deploy decision.
