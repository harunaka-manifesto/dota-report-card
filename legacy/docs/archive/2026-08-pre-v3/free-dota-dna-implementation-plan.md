# Free Dota DNA — Technical Implementation Plan

**Status:** implementation-ready proposal  
**Audience:** product engineering, data/analytics engineering, frontend, UX, QA  
**Primary specifications:** `docs/dota_report_card_free_dna_ux_blueprint.md`, `docs/opendota-data-inventory.md`  
**Repository baseline reviewed:** 2026-08-16 at `c2713a9`

## 1. Executive Summary

Build the Free Dota DNA experience as a new deterministic report product on top of the repository's existing summary-only analysis branch. Keep the current Next.js 14 web/FastAPI service split, OpenDota transport boundary, raw-payload persistence, background job model, report permalink, and production PostgreSQL/Celery seams. Replace neither the paid Deep Scan nor its evidence engine; add a dedicated DNA analytics package and a versioned `free_dna_report` payload beside it.

The target cost invariant is one OpenDota history call returning up to the latest 500 `/players/{account_id}/matches` rows, then zero match-detail or replay-parse requests. The repository currently applies the same shape but hard-caps Free history at 200 and also fetches an OpenDota profile; implementation must raise the history cap to 500 and keep any identity/profile lookup separate from the one history-call budget. The code already normalizes core summary facts, infers 90-minute-gap sessions, stores reports, publishes progress events, and renders a basic report route. It does **not** yet implement the eight DNA dimensions, confidence-aware archetype taxonomy, hero identity/recommendations, story-page UI, share rendering, or analytics instrumentation. Its current `_archetype()` is a four-label placeholder derived from generic pattern categories and must not be extended into the product classifier.

Recommended shape:

- Extend the summary match contract so every inventory field needed by DNA stays nullable and traceable.
- Add pure, versioned `dna/` and `heroes/` domain packages; the UI receives results and never recalculates them.
- Store factual hero identity separately from a source-controlled, editorial semantic taxonomy snapshot.
- Add a coherent report schema with eight `DimensionResult`s, one `ArchetypeResult`, and one `HeroIdentityResult`.
- Build the 23-state experience from 10–12 reusable story primitives using native vertical scrolling and CSS snap.
- Render share images server-side from the same report snapshot and keep a client-side DOM capture only as a fallback.

Highest risks are unreliable role hints, uncalibrated thresholds, session-sensitive dimensions with small samples, the subjective hero taxonomy, share-render consistency, and desktop scroll-snap comfort. The first working session must ship all three outcomes together: credible analysis, a complete fixture-backed story prototype, and a live vertical slice. Analysis correctness is the priority and gates UI claims; the fixture story and live path may proceed in parallel but cannot redefine or duplicate analytics.

## 2. Current-State Repository Assessment

### Stack and runtime architecture

| Area | Current implementation | Decision for Free DNA |
|---|---|---|
| Web | Next.js 14 App Router, React 18, TypeScript in `apps/web` | Extend. Keep report data fetching server-side; add a client story shell for navigation, overlays, sharing, and analytics. |
| API | FastAPI/Pydantic in `services/api/app` | Extend with DNA domain modules and typed report schemas. Do not put analytics in routes. |
| Execution | In-process bounded async tasks locally; Celery in production | Reuse. Add finer real progress checkpoints; keep report building idempotent. |
| Storage | In-memory local repository and SQLAlchemy/PostgreSQL production repository; Alembic migrations | Extend with model/taxonomy versions and optional share-artifact metadata. Reports remain immutable snapshots. |
| Cache | In-process OpenDota cache with single-flight request coalescing; completed-job reuse | Reuse transport cache; strengthen versioned analysis cache identity. Redis is execution infrastructure, not yet a shared response cache. |
| Deployment | Separate API/worker/web containers plus Postgres and Redis; Vercel-compatible web proxy | Reuse. Fix `HISTORY_LIMIT: 50` in `infra/compose.yaml` to `FREE_HISTORY_LIMIT: 500` before production DNA validation. |
| Tests | Pytest unit/contract/integration/live suites; Playwright web tests; Ruff, mypy, TypeScript | Extend heavily. Current baseline passes: 40 passed, 2 skipped; mypy and TypeScript pass. No repository CI workflow is present. |

### Relevant files and treatment

| Path | What exists | Treatment |
|---|---|---|
| `services/api/app/analysis/service.py` | Free/deep orchestration, job stages, raw profile/history persistence, early Free return | **Extend** with a dedicated DNA pipeline call. Preserve the early Free return and zero detail reads. |
| `services/api/app/opendota/client.py` | Authenticated, retrying, cached OpenDota client; current 200-row cap; no replay-parse method | **Extend the bounded history maximum to 500** and preserve its one-request behavior. This remains the only OpenDota HTTP boundary. |
| `services/api/app/opendota/schemas.py` | Minimal raw payload/profile wrappers | **Extend or supersede with typed summary adapters** while still preserving raw JSON. |
| `services/api/app/ingestion/eligibility.py` | Ranked/standard All Pick, outcome, duration, abandon, pro/league rules | **Extend** to produce per-dimension eligibility flags rather than one all-or-nothing gate. Keep a common corpus gate. |
| `services/api/app/features/summary_models.py` | Nullable `SummaryMatchFeature`, `PlayerSession`, `SummaryFeatureSet` | **Extend/rename deliberately.** Add lane, roaming, patch, region, leaver status, duplicate provenance, eligibility flags, and explicit end time. |
| `services/api/app/features/summary_calculators.py` | Win attribution and duration-aware 90-minute session grouping | **Reuse and extract.** Preserve order invariance; move session policy to its own versioned module. |
| `services/api/app/patterns/detector.py` | Generic summary patterns for Deep Scan candidate discovery | **Leave intact for Deep Scan.** Some primitives can be shared, but DNA dimensions need separate definitions and contracts. |
| `services/api/app/reports/assembly.py` | Basic `free_player_dna` dictionary and placeholder `_archetype()` | **Replace the Free assembly path** with a typed DNA report builder. Leave `assemble_report()` for deep reports. |
| `services/api/app/storage/repository.py` | Idempotent jobs, report/evidence storage, SQL implementation | **Extend** cache lookup keys and persisted metadata; do not create a second repository abstraction. |
| `services/api/app/storage/models.py` | Raw payload, features, jobs, reports, evidence, cohorts | **Extend minimally.** Prefer immutable report JSON for DNA output; add explicit analysis-version columns only if operational querying needs them. |
| `services/api/app/api/routes.py` | Create/status/SSE/report/evidence endpoints | **Reuse.** Add profile-resolution confirmation and share-image endpoints only if needed; keep versioning under `/v1`. |
| `apps/web/app/components/analysis-form.tsx` | Input, bounded polling, failure handling, redirect | **Refactor** into input/found/analysis states and consume SSE with polling fallback. |
| `apps/web/app/report/[reportId]/page.tsx` | Server-fetched, revalidated grid report | **Replace for `free_dna_report` only** with report-variant dispatch and a client `ReportStory`; retain a legacy/deep renderer. |
| `apps/web/app/globals.css` | Small generic card visual system | **Extend through scoped tokens/components.** Do not bind data logic to paper styling. |
| `packages/api-client/src/index.ts` | Handwritten create/status types only | **Generate/extend** with report contracts; make this the web's API type source. |
| `heroes_metadata/*.md` | 127 scraped DotaCoach pages with patch stats, roles, abilities, and strategy prose | **Use only as editorial research input.** It lacks stable hero IDs, normalized traits, provenance granularity, and licensing/validation guarantees required for runtime taxonomy. |
| `docs/system-behavior-baseline.md` | Current executable product boundary and Free/Deep split | **Update after implementation** so DNA-specific behavior becomes regression policy. |
| `PLAN.md` | Earlier deep insight architecture plan | **Leave as historical architecture context.** This document owns the Free DNA plan. |

### Existing gaps and constraints

- Free output currently exposes generic strengths/weaknesses and coaching-oriented Deep Scan prompts, which conflicts with identity-first DNA copy.
- Summary normalization drops `lane`, `is_roaming`, `patch` (separate from `version`), `region`, `skill`, and `hero_variant`.
- Eligibility currently rejects non-ranked lobbies implicitly via mode assumptions but has no explicit per-dimension eligibility/coverage matrix.
- Sessions are present, but resilience, endurance, and rhythm features do not exist as stable contracts.
- No product archetype taxonomy is encoded; no descriptor selection exists.
- Hero files are unstructured source material, not the requested semantic taxonomy.
- The frontend has no reusable story primitives, share/export path, methodology sheets, page restoration, or event instrumentation.
- There is no authentication or user account model. Free reports are anonymous public-data snapshots; do not introduce auth for V1.
- No analytics SDK is installed. Define a vendor-neutral adapter before choosing a provider.
- No CI configuration exists in the repository. Release hardening needs a hosted workflow for the existing commands and browser matrix.

## 3. Product-to-System Mapping

| Product capability | System responsibility | Likely module |
|---|---|---|
| Resolve Steam/OpenDota identifier | Parse Steam32/Steam64, OpenDota URL, numeric Steam profile URL, or resolve Steam vanity URL; confirm public identity | extended `core/security.py`, new `identity/steam.py`, staged analysis |
| Analyze up to 500 matches | One OpenDota history request, preserve raw payload, normalize, deduplicate, eligibility-tag | existing analysis/ingestion plus `dna/normalization.py` |
| Breadth | Hero distribution features and deterministic score | `dna/features/hero_pool.py`, `dna/dimensions/breadth.py` |
| Role | Role-hint mapping, coverage, distribution entropy | `dna/features/role.py`, `dna/dimensions/role.py` |
| Adaptability | Familiar/off-pool comparison with role-aware composite outcome | `dna/dimensions/adaptability.py` |
| Activity | K+A/min distribution with role adjustment/fallback | `dna/dimensions/activity.py` |
| Orientation | Kill share of involvements with role adjustment/fallback | `dna/dimensions/orientation.py` |
| Sessions | Duration-aware inactivity-gap inference and sensitivity metadata | `dna/sessions.py` |
| Resilience | Within-session previous-result transition contrasts | `dna/dimensions/resilience.py` |
| Endurance | Within-session game-index performance slope | `dna/dimensions/endurance.py` |
| Rhythm | Session length/duration distribution | `dna/dimensions/rhythm.py` |
| Confidence | Coverage, effective sample, stability, sensitivity penalties | `dna/confidence.py` |
| Archetype | Versioned prototype distance and tie-breaking | `dna/archetypes/classifier.py`, `dna/archetypes/v1.json` |
| Descriptors | Distinctiveness × confidence with group-diversity rule | `dna/archetypes/descriptors.py` |
| Signature Hero | Frequency/recency/persistence/role/comfort/semantic composite | `heroes/identity.py` |
| Comfort Picks | Smoothed repeat/recency/fit scores | `heroes/comfort.py` |
| Hero Pattern | IDF-weighted taxonomy trait synthesis | `heroes/patterns.py` |
| Recommendations | Role-compatible similarity + novelty + adjacent capability + diversity | `heroes/recommendations.py` |
| Copy | Versioned editorial templates and parameterized evidence renderers | `content/free_dna/en.json`, `dna/copy.py` |
| Report payload | One coherent immutable frontend contract | `reports/dna_assembly.py`, `api/report_schemas.py` |
| 23-state story | Reusable page definitions and presentation primitives | `apps/web/app/report/.../dna/*` |
| Progress | Real job events mapped to copy; no fabricated percentage | existing repository/SSE, expanded analysis stages |
| Share cards | Deterministic server renderer, signed/cacheable artifacts, Web Share client | API `share/`, web `ShareAction` |
| Deep Dive handoff | Teaser state and existing `mode="deep_scan"` entry | report payload CTA plus existing analysis-mode contract |

## 4. Data Flow Architecture

```text
Steam/OpenDota identifier
  -> parse/convert numeric Steam IDs or resolve a Steam vanity URL
  -> fetch one OpenDota summary-history payload (<= 500)
  -> persist raw response + source hash
  -> common eligibility + dedupe
  -> normalize nullable summary matches
  -> dimension-specific eligibility masks
  -> infer sessions
  -> extract immutable feature vector
  -> score 8 dimensions + confidence
  -> classify archetype + choose 3 descriptors
  -> load versioned hero taxonomy snapshot
  -> select Signature + Comfort
  -> extract Hero Pattern + recommendations
  -> render parameterized copy
  -> persist immutable report snapshot
  -> render 23 story states from one payload
  -> render/share privacy-safe card variants
```

| Stage | Input -> output | Owner | Cache/persistence | Failure and execution |
|---|---|---|---|---|
| Parse/resolve identity | Steam32, Steam64, OpenDota URL, `steamcommunity.com/profiles/{steam64}`, or vanity URL -> canonical OpenDota account ID | extended `core/security.py`, `identity/steam.py` | cache vanity mapping for 30 days | Numeric conversions are synchronous. Vanity `/id/{name}` requires a separate Steam identity resolver call and key; it does not consume the one OpenDota history call. Reject unsupported/malformed hosts before network. |
| Confirm player | canonical account ID + Steam identity -> sanitized public profile | identity service | raw/sanitized identity, short profile cache | Player Found occurs here. If an OpenDota profile request is retained, count it separately and document that the one-call constraint refers to match history; prefer resolved Steam identity so Free analytics needs only the history call from OpenDota. |
| Fetch history | account ID -> <=500 raw rows | OpenDota client | raw payload; 2–5 minute upstream cache | Async network; exactly one OpenDota history request per cache miss. On 429/5xx use existing retry/backoff, then actionable failure. |
| Normalize | raw rows -> `NormalizedSummaryMatch[]` | ingestion/DNA normalizer | optionally derived feature records; always report provenance | Deterministic/synchronous. Malformed rows are ledgered, not silently coerced. |
| Infer sessions | eligible dated rows -> sessions + positions | `dna/sessions.py` | part of feature snapshot | Deterministic. Undated/corrupt rows get no session assignment and remain usable elsewhere. |
| Extract features | matches/sessions -> `DnaFeatureSet` | `dna/features/*` | immutable versioned feature snapshot | Deterministic. Every feature carries denominator/coverage/source IDs. |
| Score dimensions | feature set -> eight results | `dna/dimensions/*` | report snapshot, optionally derived features | Deterministic. Each dimension can be `available`, `limited`, or `unavailable`; one failure does not fail report. |
| Archetype | dimension vector -> archetype/descriptors | `dna/archetypes/*` | report snapshot | Deterministic. Low confidence yields a broader fallback, never a fabricated precise fit. |
| Hero identity | features + taxonomy -> identity result | `heroes/*` | taxonomy-versioned report snapshot | Deterministic. Taxonomy absence suppresses pattern/recommendations but not Signature/Comfort if factual hero map exists. |
| Copy | structured evidence -> display text keys/values | `dna/copy.py` | template version in report | Deterministic templates. Never use an LLM in core V1 report generation. |
| Assemble | all results -> `FreeDnaReport` | `reports/dna_assembly.py` | immutable report JSON keyed by versions and data hash | Synchronous inside background job. Validate schema before completion. |
| Render | report -> server page + client story | Next.js | `revalidate` for immutable report | Report fetch failures use route boundaries; partial analytics render explicit folded-note pages. |
| Share | report/card/privacy/ratio -> image | share API/renderer | content-addressed artifact or CDN | Server render async-on-first-use; client download fallback. Failure never loses story position. |

All analytical and textual outputs are deterministic for the tuple `(raw_payload_hash, eligibility_version, session_version, feature_version, dna_scoring_version, archetype_version, hero_taxonomy_version, recommendation_version, template_version)`. Report IDs point to immutable snapshots; refresh creates or resolves a new compatible snapshot rather than mutating a historical report.

## 5. Data Contracts and Schemas

### Raw OpenDota match summary

Persist the returned array unchanged through the existing raw-payload repository with endpoint, account/source ID, fetched time, SHA-256 payload hash, requested limit/projection, and an adapter/schema version. Do not store only the projected normalized fields.

### Normalized summary match

```ts
type EligibilityKey =
  | "overall" | "breadth" | "role" | "adaptability"
  | "activity" | "orientation" | "resilience" | "endurance" | "rhythm";

interface NormalizedSummaryMatch {
  matchId: number;
  sourceIndex: number;
  accountId: number;
  heroId: number | null;
  heroVariant: number | null;
  startedAt: number | null;
  durationSeconds: number | null;
  endedAt: number | null;
  side: "radiant" | "dire" | null;
  won: boolean | null;
  gameMode: number | null;
  lobbyType: number | null;
  leaverStatus: number | null;
  kills: number | null;
  deaths: number | null;
  assists: number | null;
  partySize: number | null;
  laneRole: number | null;
  lane: number | null;
  isRoaming: boolean | null;
  roleHint: "carry" | "mid" | "offlane" | "soft_support" | "hard_support" | "roamer" | null;
  roleConfidence: number | null;
  patch: string | null;
  skillBracket: number | null;
  region: number | null;
  sessionId: string | null;
  sessionIndex: number | null;
  eligibility: Record<EligibilityKey, { included: boolean; reasons: string[] }>;
}
```

Do not reuse the detail-oriented `NormalizedMatch`: it requires ten-player data and would blur the Free/Deep boundary. Extend the current `SummaryMatchFeature` or introduce this explicit sibling and migrate the current summary detectors through an adapter.

### Analysis feature layer

`DnaFeatureSet` contains scalar/distribution features plus `sampleSize`, `coverage`, `sourceMatchIds`, and `featureVersion` for each. Required features include normalized hero entropy; top-3/5/10 shares; unique heroes; dominant role share and normalized role entropy; familiar hero/role sets; smoothed familiar/off-pool win and K+A/min contrasts; K+A/min; kill share; previous-result transitions; loss-streak transitions; session index buckets; robust within-session slopes; matches/session and session-duration quantiles. Raw per-match feature rows remain internal so UI cannot cherry-pick analytics.

### Dimension result

```ts
interface DimensionResult {
  key: "breadth" | "role" | "adaptability" | "activity" | "orientation" |
       "resilience" | "endurance" | "rhythm";
  status: "available" | "limited" | "unavailable";
  score: number | null;              // 0 = left label, 1 = right label
  centeredScore: number | null;      // -1..1 for classification
  label: string | null;
  confidence: "high" | "moderate" | "low" | "unavailable";
  confidenceScore: number;
  sampleSize: number;
  effectiveSampleSize: number;
  coverage: number;
  evidence: Array<{ key: string; value: number | string; unit: string; denominator: number }>;
  confounders: string[];
  missingReasons: string[];
  copy: { headlineKey: string; receiptKey: string; receiptParams: Record<string, unknown> } | null;
  methodologyVersion: string;
  sourceMatchIds: number[];
}
```

### Archetype result

```ts
interface ArchetypeResult {
  key: string;
  label: string;
  fit: number;
  runnerUp: { key: string; fit: number } | null;
  descriptors: Array<{ key: string; label: string; dimension: DimensionResult["key"] }>;
  contributingDimensions: Array<{ key: DimensionResult["key"]; weight: number; contribution: number }>;
  confidence: "high" | "moderate" | "low";
  explanationEvidence: string[];
  classifierVersion: string;
}
```

### Hero result

`HeroIdentityResult` contains `signature`, 3–5 `comfortPicks`, 1–3 `patterns`, and 0–3 `recommendations`. Each hero includes stable hero ID/name/portrait asset version, score, component scores, match sample, receipts, role fit, and taxonomy version. Each recommendation separately lists familiar traits, new traits, plausible roles, and a deterministic reason key. Internally retain full candidate scores; expose only useful receipts, not a false precision score, in the primary UI.

### Report payload

One `FreeDnaReport` owns identity, coverage, versions, dimensions, archetype, hero identity, ordered page definitions, share-card content, privacy defaults, Deep Dive state, and warnings. The frontend may format numbers and resolve copy keys, but must not compute labels, select descriptors, choose heroes, or infer confidence.

## 6. Match Eligibility and Normalization

Use two layers: a common history corpus and dimension-specific masks.

### Common corpus

Include a row when it has a unique positive `match_id`, valid `hero_id`, known player side/outcome, supported public matchmaking mode, no material abandon, and duration >= 5 minutes. The decided V1 corpus includes **both ranked and unranked public All Pick**. Validate `game_mode` as All Pick/Ranked All Pick (`1`, `22`) and use `lobby_type` to distinguish ranked from unranked; rename the current misleading `NON_RANKED` exclusion. Exclude Turbo, custom/event modes, bot matches, pro/league matches, and unsupported modes until separately calibrated.

Deduplicate by `match_id`; retain the first row in newest-first source order only if duplicates are identical, otherwise choose the row with more non-null required fields and ledger `duplicate_conflict`. Sort analytics chronologically by `(startedAt, matchId)` but retain source order metadata. Clamp neither K/D/A nor duration silently; negative or implausible values make the affected field/dimension ineligible.

### Dimension masks

| Dimension | Additional requirements | Missing-field behavior |
|---|---|---|
| Breadth | valid hero | Common corpus is sufficient. |
| Role | credible `lane_role`/`lane`/roaming mapping | Exclude only from Role; hero prior may support but never manufacture a role. |
| Adaptability | hero, outcome; K/D/A and role improve composite | Use outcome-only with lower confidence if K/D/A absent; require both familiar and off-pool groups. |
| Activity | K, A, positive duration; credible role for adjusted V2 | Exclude row from Activity if any numerator field is null. |
| Orientation | non-null K/A and K+A > 0 | Zero-involvement games are valid context but not a defined kill-share ratio; report their count. |
| Resilience | timestamp, outcome, next match in same inferred session; next-match outcome or K/D/A | Never bridge undated rows/session gaps. |
| Endurance | timestamp/duration, session position; outcome/KDA composite | Require repeated multi-game sessions and sufficient late games. |
| Rhythm | timestamp and duration | Single-match sessions count; undated rows do not. |

Patch boundaries do not exclude matches. Store patch and expose persistence/sensitivity; dimensions should not compare tiny patch cells. For hero persistence, count distinct observed patches only when patch exists and also use calendar windows so missing patch does not erase evidence. Matches with missing timestamps still count for Breadth/Role/Adaptability/Activity/Orientation but not session dimensions or recency. Extremely short games (<5 minutes) are excluded globally; 5–10 minute games remain in Breadth/Role but are excluded from performance composites by default.

Recommended report minimum is 30 common eligible matches. At 30–59, issue a limited-history report with conservative confidence. Always return all eight dimension pages: a scorer that fails its own requirements emits a weak/unavailable result with honest explanatory copy instead of disappearing. Below 30, return insufficient history. Never require exactly 500.

## 7. Session Inference

Move session inference from `summary_calculators.py` into `dna/sessions.py` with policy `sessions-1.0.0`.

- Sort only dated matches ascending.
- Compute `previous_end = previous.start + max(valid_duration, 0)` and `queue_gap = current.start - previous_end`.
- Start a new session when `queue_gap > 90 minutes`. Ninety minutes matches the existing repository default and sits inside the blueprint's 90–120-minute range.
- Do not split at midnight; a 23:30–01:00 sequence is one session if the inactivity rule holds.
- A long pause inside a day splits normally. A negative gap beyond a small clock tolerance marks both rows session-corrupt and prevents that transition from use.
- An undated match receives no session ID and never connects two dated matches.
- Keep one-match sessions for Rhythm; Resilience needs at least a pair; Endurance needs positions 1/2 and a late bucket.
- Aggregate Endurance as Game 1, Game 2, Game 3, Game 4+; retain exact positions internally up to 8 and collapse the tail for stable reporting.

Run every session-dependent score at 60, 90, and 120-minute gaps in validation. The displayed V1 score uses 90 minutes; confidence is multiplied by `1.0`, `0.8`, or `0.6` depending on whether the direction agrees across all three, two, or fewer sensitivity runs. Store the threshold and sensitivity result in methodology evidence.

Resilience compares a next game only within the same session. Endurance compares game positions within sessions and should use within-session deltas when possible, preventing habitual long-session players from dominating the estimate. Rhythm uses the full session distribution and is independent of performance. None of these outputs uses the word “tilt” or claims emotional causation.

## 8. Dimension Algorithms

All scores are `0..1`, where 0 is the left spectrum label and 1 is the right. Apply a neutral band of `0.42..0.58`; within it, use a balanced/neutral statement and exclude the dimension from descriptors unless all available dimensions are similarly neutral. Confidence combines coverage (35%), effective sample (35%), temporal/bootstrap stability (20%), and model-specific quality (10%); hard requirements override the weighted score.

### Breadth

1. **Definition:** concentration versus distribution of hero choice, not skill or willingness to adapt. 2. **Fields:** `hero_id`, optionally `start_time`. 3. **Features:** unique count, top-3/5/10 share, normalized Shannon entropy `H/log(min(uniqueHeroes, eligibleMatches))`, and effective hero count `exp(H)`. 4. **V1 normalization:** compute concentration `C = .45*top5Share + .35*(1-normalizedEntropy) + .20*min(1, 10/effectiveHeroCount)`; Breadth score (Exploratory) is `1-C`, winsorized to `[0,1]`. 5. **Role adjustment:** none; role belongs to another dimension. 6. **Minimum:** 30 hero-valid matches; high confidence >=100. 7. **Confidence:** sample + hero coverage + score stability across recent 50/100/full windows. 8. **Neutral:** label “Balanced pool” internally; UI uses “Your pool has a center, with room to roam.” 9. **Evidence:** top-N share plus unique hero count; never show entropy by default. 10. **Confounders:** bans, patch, role demand, new-account roster exposure. 11. **Tests:** one-trick, uniform 30-hero, same unique count/different concentration, order invariance, missing hero, window instability.

### Role

1. **Definition:** concentration of credible role/lane identity. 2. **Fields:** `lane_role`, `lane`, `is_roaming`, supporting hero factual/common-role priors. 3. **Features:** mapped role probabilities, classifiable coverage, dominant share, normalized entropy. 4. **V1 normalization:** use only source hints with confidence >=0.6; `anchoring = .65*dominantShare + .35*(1-normalizedRoleEntropy)`, Role score (Fluid) = `1-anchoring`. Do not collapse position 4/5 unless source data cannot distinguish them; if forced, represent three role families and version it. 5. **Role adjustment:** not applicable; this is the role model. 6. **Minimum:** >=30 classified matches and >=40% corpus coverage; high confidence requires >=60 and >=65% coverage. 7. **Confidence:** sample × coverage × agreement between lane-role and hero prior; a prior may reduce/raise certainty, not replace missing fields. 8. **Neutral:** “No single role fully owns your history.” 9. **Evidence:** dominant role share/denominator or maximum role share. 10. **Confounders:** inaccurate summary labels, role swaps, dual lanes, hero flexibility. 11. **Tests:** anchored, even distribution, low coverage unavailable, conflicting hints, roaming, prior-only suppression.

### Adaptability

1. **Definition:** whether observable output transfers outside familiar heroes/roles; not pool size. 2. **Fields:** hero, role hints, win, K/D/A, duration. 3. **Features:** familiar hero set determined without outcomes; familiar role; smoothed win rate and role-adjusted K+A/min inside/outside; sample balance. Define familiar heroes as the smallest top-frequency set covering 50% of valid games, bounded 3–10, with >=5 games each. 4. **V1 normalization:** compute empirical-Bayes-smoothed win-rate delta and standardized K+A/min delta, `penalty = .6*winDelta + .4*activityDelta` when both exist, otherwise outcome only; map a +/-15-point practical range to `[0,1]`, where flat/off-pool-positive is Transferable. Use time-split validation: define familiarity on older 70%, evaluate on newer 30%; fall back to leave-one-window-out when sample is too small. 5. **Role adjustment:** compare within role strata with >=8 matches per side, then weighted-average; otherwise include a visible role-mix confounder and reduce confidence. 6. **Minimum:** >=20 familiar and >=20 off-pool evaluation matches; >=2 represented contexts. 7. **Confidence:** smaller group size, role overlap, KDA coverage, bootstrap sign stability. 8. **Neutral:** differences under 3 win-rate points and 0.1 standardized output are neutral. 9. **Evidence:** familiar/off-pool delta and denominators. 10. **Confounders:** draft quality, hero learning, patch changes, different role mix, selection bias. 11. **Tests:** broad-but-comfort-bound, narrow-but-transferable, outcome-only fallback, tiny off-pool suppression, role-confounded Simpson case, no leakage from evaluation outcomes.

### Activity

1. **Definition:** observable K+A events per minute, not quality or full teamfight participation. 2. **Fields:** kills, assists, duration, role hints. 3. **Features:** per-match `(K+A)/minutes`, median, trimmed mean, IQR, role-cell residuals. 4. **V1 normalization:** absent population baselines, use a role-mix expected table calibrated from fixtures/initial sample and checked into `dna/baselines/activity-v1.json`; score the median standardized residual through a logistic mapping. If role coverage is insufficient, use within-player percentile distribution only to describe consistency and return an unadjusted score with low confidence—do not say “high relative to your role mix.” 5. **Role adjustment:** required for moderate/high confidence. 6. **Minimum:** >=30 K/A/duration matches and >=20 role-adjusted matches. 7. **Confidence:** K/A coverage, role coverage, median stability across halves, duration validity. 8. **Neutral:** residual within ±0.15 involvements/minute. 9. **Evidence:** raw rate; role-relative language only when adjusted. 10. **Confounders:** team kill totals absent, stomps, hero style, match tempo. 11. **Tests:** zero K/A, support/core role equivalence after adjustment, extreme duration, missing assists, outlier robustness, unadjusted copy guard.

### Orientation

1. **Definition:** kill-versus-assist composition among observable involvements. 2. **Fields:** kills, assists, role hints. 3. **Features:** aggregate kill share `sum(K)/sum(K+A)`, median match kill share, zero-involvement rate, role residual. 4. **V1 normalization:** compare aggregate kill share to versioned role expectations; map a residual of -0.20 to Facilitator (`1`) and +0.20 to Finisher (`0`), with shrinkage toward neutral based on total involvements. 5. **Role adjustment:** required for descriptor eligibility; without it show only descriptive composition with low confidence. 6. **Minimum:** >=30 matches, >=100 total K+A, >=20 role-classified matches. 7. **Confidence:** involvement count, role coverage, consistency across hero/role cells. 8. **Neutral:** role residual within ±0.05. 9. **Evidence:** “X% of kill-or-assist involvement is yours to finish,” optionally role-adjusted qualifier. 10. **Confounders:** no team kill denominator, kill credit mechanics, hero/role composition. 11. **Tests:** all-zero, support/core expectations, aggregation versus mean-of-ratios, low-involvement shrinkage, missing role copy guard.

### Resilience

1. **Definition:** association between previous outcome and next-game observable result within an inferred session. 2. **Fields:** chronological start/duration, win, K/D/A, hero/role. 3. **Features:** next-game smoothed win rate and standardized KDA/activity composite after win, single loss, and 2+ losses; paired deviation from player baseline. 4. **V1 normalization:** primary effect is `nextPerformanceAfterLoss - nextPerformanceAfterWin`, adjusted by next-game role/hero familiarity when strata permit. Map effect magnitude rather than positive/negative moral value: near zero -> Resetting (`0`); larger absolute outcome-conditioned shift -> Outcome-sensitive (`1`). Preserve direction separately (“better” or “lower”) for evidence; do not equate sensitivity with decline. 5. **Role adjustment:** residualize next-game composite by role expectation; outcome-only fallback lowers confidence. 6. **Minimum:** >=15 after-loss and >=15 after-win transitions across >=10 sessions; 2+ loss receipt needs >=8. 7. **Confidence:** transition counts, session-threshold sensitivity, covariate overlap, bootstrap effect stability. 8. **Neutral:** absolute smoothed delta <5 points/0.15 SD. 9. **Evidence:** “Your next-game results change by X after losses”; “barely changes” only if interval is narrow. 10. **Confounders:** matchmaking, party changes, hero swaps, stopping behavior, regression to mean. 11. **Tests:** never cross session, improvement-after-loss still outcome-sensitive, zero delta resetting, streak sample suppression, gap sensitivity, forbidden psychology copy.

### Endurance

1. **Definition:** change in observable performance as session game index increases. 2. **Fields:** sessions, index, win/KDA/activity, role/hero context. 3. **Features:** position-bucket performance, within-session Game 1-to-later differences, robust slope, late-game sample. 4. **V1 normalization:** build a shrunk composite of win (60%) and standardized K+A/min/KDA availability (40%); estimate a player-fixed-effect slope across session positions capped at 4+. Map meaningful negative slope to Front-loaded (`0`); flat or positive to Sustained (`1`). “Sustained” means holding level, not necessarily improving. 5. **Role adjustment:** residualize per-match performance when reliable role exists; otherwise compare only sessions whose role mix does not materially change and reduce confidence. 6. **Minimum:** >=12 multi-game sessions, >=15 Game-1 observations, >=12 Game-3+ and >=8 Game-4+ observations for a strong call. 7. **Confidence:** late sample, number of independent sessions, sensitivity, slope interval, role/hero mix stability. 8. **Neutral:** slope within ±0.05 outcome-equivalent per game. 9. **Evidence:** first-two versus Game-4+ delta or flatness with denominators. 10. **Confounders:** player stops after losses/wins, time of day, parties, draft and opponent changes. 11. **Tests:** one-match sessions ignored, grinder decline, sustained flat, improving sessions, tail collapse, within-session weighting, missing late sample.

### Rhythm

1. **Definition:** natural session-length pattern, independent of performance. 2. **Fields:** session timestamps/durations. 3. **Features:** median and mean matches/session, median elapsed session duration, share of 1–2 and 5+ sessions, long-chain recurrence. 4. **V1 normalization:** score `0.5*scaledMedianMatches + .3*share5Plus + .2*scaledMedianDuration`, with 2 matches/2 hours near Short-burst and 5 matches/5 hours near Grinder; publish exact thresholds in versioned policy and recalibrate. 5. **Role adjustment:** none. 6. **Minimum:** >=10 inferred sessions and >=25 dated matches. 7. **Confidence:** number of sessions, timestamp coverage, sensitivity across gap thresholds, observation-window coverage. 8. **Neutral:** median 3 and neither short nor long sessions dominate. 9. **Evidence:** typical matches/session and share reaching 5+. 10. **Confounders:** 500-match truncation can cut the oldest session, missing timestamps, account sharing, unusual events. 11. **Tests:** all solos, repeated marathons, mixed neutral, boundary gaps, truncated first/last session exclusion sensitivity, independence from outcomes.

## 9. Population Baselines and Normalization Strategy

### V1

Use direct behavioral measures for Breadth and Rhythm; within-player contrasts for Adaptability, Resilience, and Endurance; and small versioned role expectation tables for Activity/Orientation. Do not manufacture global percentiles from the player's own 500 games. Each baseline file records source cohort, collection window, patch range, filters, sample size, generation code version, and review date. Until a real calibration corpus exists, label role-relative outputs as provisional and cap their confidence at moderate.

### V2+

Build offline cohort aggregates through the existing `cohorts`/storage seams, never through extra requests during report generation. Prefer hierarchical shrinkage:

1. game mode + patch family + dominant role;
2. add skill bracket when coverage and privacy are adequate;
3. add sample-size band for uncertainty, not behavioral expectations;
4. region only if analysis proves a stable, meaningful effect and sample support.

Activity and Orientation need role-aware percentiles most. Adaptability may use role/skill/patch cohort distributions of within-player deltas. Endurance/Resilience should normalize effect uncertainty but keep the player's within-session contrast as the meaning. Breadth and Rhythm should not be role-normalized by default: doing so would redefine “what/how much you play” as conformity to a cohort. Archetype inputs remain stable `0..1`; changing baseline versions creates a new report snapshot, not a reinterpretation of an old one.

Migration path: calculators emit raw features plus a `Normalizer` interface; V1 loads fixed/within-player normalizers, V2 loads persisted cohort snapshots. The `DimensionResult` contract and story UI do not change.

## 10. Archetype Classification System

Encode the blueprint's 13 working archetypes as versioned prototypes in `dna/archetypes/v1.json`, not UI conditions. Each prototype specifies expected centered dimension positions, per-dimension weights, optional acceptable ranges, editorial meaning key, and minimum required groups. Omitted dimensions contribute neither reward nor penalty.

For every available dimension, multiply squared distance to the prototype by dimension weight and confidence. Normalize by total active weight; convert distance to a `0..1` fit. Apply a small missingness penalty. Tie-break by: higher fit margin on high-confidence dimensions, then greater coverage of prototype dimensions, then stable lexical key. If top-two fit differs by <0.03, choose the prototype with fewer extreme assumptions and report low archetype confidence.

Neutral players use an explicitly broad prototype/fallback such as `Adapter` or `Free Agent` only if its actual ranges fit. If fewer than four dimensions across at least three groups are reliable, return `The Developing Competitor` as a clearly provisional fallback; do not force a precise working archetype. This is a recommended adjustment to the UX taxonomy for statistical honesty.

Descriptor score is `abs(centeredScore) * confidenceScore * reliabilityMultiplier`. Choose exactly three from available dimensions, suppressing descriptors that restate the archetype label or have low confidence. Prefer different groups: hero identity (Breadth/Role/Adaptability), combat expression (Activity/Orientation), session response (Resilience/Endurance/Rhythm). A max-marginal-relevance penalty prevents near-redundant choices. If fewer than three reliable extremes exist, fill with neutral but truthful descriptors (for example `Balanced involvement`) rather than low-confidence extremes.

The classifier exposes contributing dimensions/evidence, never embeds synthesis prose, and is covered by golden vectors for each archetype, near ties, neutral profiles, missing dimensions, and descriptor diversity. Later clustering, validated prototypes, or learned classification can implement the same `classify(DimensionResult[]) -> ArchetypeResult` interface and increment `classifierVersion` without changing the report contract.

## 11. Signature Hero Algorithm

Score only heroes with >=5 eligible games, except low-history fallback (>=3 and explicitly low confidence). Use components normalized within the player:

- frequency 25%: empirical-Bayes-smoothed share, preventing one small sample from dominating;
- recency 15%: exponential decay with a 60-day half-life, bounded so older identity is not erased;
- repeat behavior 15%: presence across rolling quartiles/calendar months rather than one binge;
- patch/calendar persistence 10%: distinct observed patches or 30-day windows, normalized by player coverage;
- role alignment 10%: hero appearances inside the player's credible dominant role mix;
- comfort output 10%: smoothed outcome/activity residual, capped so win rate cannot define identity;
- semantic cluster fit 15%: similarity to the other high-relevance comfort candidates.

If taxonomy is unavailable, redistribute semantic weight proportionally across frequency/recency/repeat/persistence and mark limitation. Select the highest score; ties within 0.02 resolve by repeat persistence, then sample size, then stable hero ID. Run a leave-one-window-out stability check: if a winner changes in most windows, lower confidence and phrase it as “best current signature.”

“Most played” is insufficient because a past one-patch binge may not represent current/persistent identity, and a tiny undefeated sample is noise. The UI should show three categorical receipts (`keeps returning`, `across N windows`, `fits your role/pattern`), not the weighted formula or a 0.783 score; methodology can disclose components.

## 12. Comfort Picks

Eligibility: hero ID present, >=5 games (or max of 3 and 5% of corpus for 30–59-match reports), appearances in at least two time windows unless the observation window is short. Score frequency 35%, recency 20%, repeat persistence 20%, credible role fit 10%, smoothed observable comfort output 15%. Do not use raw win rate or KDA as a gate.

Return 3–5 picks: 3 for <60 matches or only three eligible heroes, otherwise up to 5. Signature Hero may appear and is labeled centerpiece. To avoid statistical artifacts, shrink rates toward the player's overall mean with a Beta prior/equivalent; cap performance contribution; require stable recurrence. Do **not** diversify Comfort Picks merely to make them semantically different—comfort can legitimately be narrow—but suppress duplicates caused by hero aliases/ID mapping and avoid filling to five with weak samples.

Tap evidence includes games, recency window, repeat windows, role alignment, smoothed outcome context, and the reason key. Tests cover tiny high-win samples, old high-frequency heroes, recent binge versus persistent pick, ties, only two eligible heroes, and missing role/taxonomy.

## 13. Hero Semantic Taxonomy

Use a hybrid, source-controlled snapshot model:

- `services/api/app/heroes/data/factual/<version>.json`: Valve/OpenDota facts (hero ID, canonical/localized name, attack type, roster availability, portraits, official roles), each field with source and fetched/effective version.
- `services/api/app/heroes/data/editorial/<version>.json`: product judgments on common positions and numeric `0..1` traits: initiation, mobility, pickoff, teamfight, save, sustain, burst, sustained damage, wave clear, push, frontline, scaling, farm dependency, global presence, micro intensity, complexity, repositioning.
- `taxonomy-manifest.json`: factual/editorial versions, schema version, effective patch/date, provenance, reviewer, checksum.

The implementer must read **all 127** `heroes_metadata/*.md` files during the hero-semantics milestone and use them as the supplied research corpus for building the recommendation taxonomy. They must not parse those Markdown files at report runtime. The milestone converts reviewed facts/semantics into stable hero-ID-keyed taxonomy snapshots with field-level provenance; volatile statistics and third-party prose are not copied into product claims without review.

Validate with JSON Schema/Pydantic: unique hero IDs/keys, complete current roster, values in range, known roles/traits only, provenance present, no impossible portrait refs, and semantic review status. A generator produces a frozen typed artifact; changes require review from product plus a Dota-literate reviewer. Hero additions/reworks create a new taxonomy version. Patch-sensitive overrides are additive (`base` plus `effectiveFromPatch`) rather than overwriting history.

Every report stores the exact taxonomy manifest/version and resolved traits used. Historical rendering uses the embedded hero result/portrait asset version, so a taxonomy edit never changes an existing report. Begin with source control because the corpus is small, diffable, and release-coupled. Add an admin editor later only if edit cadence/ownership demands it; it must still publish immutable reviewed snapshots to source/object storage.

## 14. Hero Pattern Extraction

Input Signature plus Comfort Picks with normalized relevance weights. For each trait, compute weighted agreement and multiply by inverse-document-frequency `log((N+1)/(heroesWithTrait+1))`; this prevents generic traits such as “teamfight” from always winning. Role traits are handled separately from playstyle traits so “support” does not drown out “mobile initiator.”

Require at least 60% weighted agreement across at least two non-signature comfort heroes, or 75% across a three-hero pool. Remove mutually contradictory themes using a curated exclusivity matrix and choose the highest theme; optionally emit a second theme only if its score is >=80% of the first and it adds a distinct trait family. Pattern labels come from source-controlled combinations (`mobility + initiation -> mobile initiators`) before falling back to a single trait (`pickoff-focused heroes`).

Copy is fully template-based in V1. The engine outputs trait IDs, scores, contributing heroes, and a copy key. Templates turn `Earth Spirit + Tusk + Clockwerk` into “You gravitate toward mobile initiators” and a one-sentence explanation. If no theme clears agreement, fall back deterministically to “Your comfort pool spans several different toolsets” and omit over-specific claims. An LLM can later propose editorial variants offline, but cannot determine the report's traits or live copy.

## 15. Hero Recommendation Engine

Candidate set is the current factual roster minus heavily played heroes (>=5 games or top-10 personal share), unavailable heroes, and heroes lacking reviewed taxonomy. Score:

- semantic similarity to weighted Signature/Comfort centroid: 40%;
- plausible role compatibility: 25%;
- novelty (not/recently little played): 15%;
- adjacent-trait bonus (one useful new capability): 15%;
- complexity-gap fit: 5%, soft penalty only.

Require at least one familiar high-weight trait and one adjacent trait not dominant in the comfort centroid. A role-outside candidate can survive only when similarity is exceptional and its reason explicitly says it changes role; by default cap such candidates at one. Select three via maximal marginal relevance, penalizing pairwise similarity so results are not clones. Meta strength, current win rate, counters, and performance coaching are absent in V1.

Output hero, fit band (strong/good), familiar traits, new traits, plausible roles, source scores, and a deterministic short reason. Safeguards/tests cover already-played exclusion, alias mapping, three-identical-result diversity, no compatible candidates, missing taxonomy, complexity cliffs, and role-outside explanations.

## 16. Copy and Content Architecture

Store copy outside algorithms and components in versioned locale catalogs such as `services/api/app/content/free_dna/en.json`, mirrored/generated as needed for web static labels. Four layers remain separate:

- static editorial copy: intros, section transitions, privacy, Deep Dive teaser;
- parameterized evidence copy: formatter key + typed parameters from calculators;
- archetype synthesis: archetype meaning plus selected contribution clauses;
- hero pattern/recommendation reasons: taxonomy trait combination templates.

Algorithms emit copy keys and safe parameters, not English prose. The report builder resolves snapshot text for historical reproducibility while retaining keys for analytics/localization. Catalog validation checks all algorithm-emitted keys, parameter shapes, forbidden terms (`tilt`, diagnosis language), neutral states, and confidence qualifiers. Copy experiments use `copyExperiment`/variant in the report and never alter scores. Algorithm/model versions and template versions remain separate.

## 17. Report Payload API

Keep `POST /v1/analyses`, status/events, and `GET /v1/reports/{id}`. Set `report_variant: "free_dna_report"` and `schema_version: "free-dna-report-1.0.0"`; dispatch legacy/deep renderers by variant. A representative contract:

```ts
interface FreeDnaReport {
  schemaVersion: "free-dna-report-1.0.0";
  reportVariant: "free_dna_report";
  reportId: string;
  identity: { displayName: string | null; avatarUrl: string | null; accountIdMasked: string };
  metadata: {
    createdAt: string; dataFrom: string | null; dataTo: string | null;
    processedMatches: number; eligibleMatches: number; rawPayloadHash: string;
  };
  versions: {
    eligibility: string; sessions: string; features: string; dnaScoring: string;
    archetype: string; heroTaxonomy: string | null; recommendations: string | null;
    copy: string;
  };
  quality: {
    overallConfidence: "high" | "moderate" | "low";
    missingDataFlags: string[]; partial: boolean; warnings: string[];
  };
  dimensions: DimensionResult[];
  archetype: ArchetypeResult;
  heroes: HeroIdentityResult;
  pages: Array<{
    id: string; kind: string; section: "intro" | "dna" | "heroes" | "finale";
    title: string; body?: string; evidenceKeys?: string[];
  }>;
  shares: {
    dna: ShareCardContent; heroes: ShareCardContent; final: ShareCardContent;
    privacyDefaults: { showName: boolean; showAvatar: boolean; showRawId: false };
  };
  deepDive: { available: boolean; ctaLabel: string; href: string | null };
}
```

The status contract should expose real `stage`, `completedStages`, and optional known counts, never a fake percentage. Report API responses are immutable and cacheable privately/at the server; reports remain `noindex`. Do not include raw Steam ID in `shares` or page definitions.

## 18. Backend / Analysis Modules

Add domain packages without disturbing the existing paid-insight packages:

| Module | Responsibility and public API | Dependencies | Unit-test boundary |
|---|---|---|---|
| `ingestion/summary_normalize.py` | `normalize_summary_rows(raw, account_id) -> NormalizationResult` | eligibility, source schemas | field nullability, side/win, dedupe, ledgers |
| `dna/sessions.py` | `infer_sessions(matches, policy) -> SessionResult` | normalized summary model | ordering, gaps, corrupt/undated rows, sensitivity |
| `dna/features/models.py` | immutable feature/evidence contracts | normalized model | serialization and invariants |
| `dna/features/extractor.py` | `extract_dna_features(matches, sessions, config)` | feature subcalculators | exact denominators/provenance and fixture goldens |
| `dna/confidence.py` | confidence factors and labels | feature results | boundaries, hard minimums, missingness |
| `dna/dimensions/<key>.py` | `score(features, normalizer) -> DimensionResult` | confidence, baseline interface | one focused suite per dimension |
| `dna/dimensions/service.py` | orchestrate eight independent scorers and contain failures | dimension registry | partial-result behavior and stable order |
| `dna/baselines.py` | load/validate immutable normalizers | versioned baseline JSON | version/checksum and missing cohort fallback |
| `dna/archetypes/classifier.py` | `classify(dimensions, prototypes)` | prototype snapshot | prototype vectors, ties, missingness |
| `dna/archetypes/descriptors.py` | choose exactly three nonredundant descriptors | dimension metadata | diversity, low-confidence and neutral fill |
| `heroes/taxonomy.py` | load/validate factual/editorial snapshots | source-controlled JSON | completeness, trait ranges, provenance |
| `heroes/identity.py` | Signature and Comfort selection | DNA features, taxonomy | weights, smoothing, persistence, tie-breaks |
| `heroes/patterns.py` | IDF-weighted trait themes | taxonomy, copy keys | common-trait penalty, contradictions, fallback |
| `heroes/recommendations.py` | candidate ranking and diverse selection | taxonomy, player hero history | exclusions, role fit, novelty, adjacent traits |
| `content/renderer.py` | resolve typed copy keys for a report snapshot | locale catalog | key coverage, parameter validation, guardrails |
| `reports/dna_assembly.py` | `assemble_free_dna_report(...) -> FreeDnaReport` | all DNA/hero results | schema validation, privacy, ordered page contract |
| `share/service.py` | card content validation, render requests, artifact cache | report repository, image renderer | deterministic hash, privacy, failure fallback |

`AnalysisService._save_player_dna()` becomes orchestration only: update stage, call DNA analysis, assemble, validate, save, complete. Do not import web concerns or taxonomy file parsing into the service. The existing `patterns`, `hypotheses`, `selection`, `insights`, and deep `assemble_report()` remain paid-analysis modules. Shared summary primitives may be consumed by both paths, but Free DNA must not create Deep Scan hypotheses or selection candidates as part of its core report; those currently add unnecessary work and payload coupling.

## 19. Caching and Cost Control

Use three cache layers with explicit purposes:

1. **OpenDota transport:** retain profile TTL 5 minutes and history TTL 2 minutes initially; raise history to 5 minutes if rate pressure warrants. Cache key includes account ID, limit, projection. Use current single-flight coalescing. Production should move this cache to Redis or add a shared adapter so API and Celery workers do not duplicate upstream reads.
2. **Completed analysis:** key by `account_id + analysis_mode + raw-history hash/latest match ID + all analytical versions`. The current lookup uses only account/model/mode and age; extend compatibility so taxonomy/scoring changes cannot reuse an incompatible report.
3. **Share artifact:** key by `report_id + card_type + aspect_ratio + privacy_options + renderer_version + asset_manifest_hash` and store immutable output in object storage/CDN.

Default compatible report TTL remains one hour; user refresh bypasses completed-report reuse but still uses safe upstream caching unless “fetch fresh” is explicitly required. Coalesce in-flight work through the existing repository active key, expanded to all compatibility versions. Report generation is idempotent: the same data/version tuple may return an existing report.

On rate limit, surface retryable state and honor `Retry-After`; never fall back to detail endpoints. Track requested/actual history calls and assert Free mode made exactly one `/players/{account_id}/matches?limit=500` request per cache miss, zero `/matches/{match_id}`, and zero parse calls. Projection is optional: request needed summary fields when supported, but preserve full raw responses when projection reliability is uncertain. A Steam vanity-resolution call, when needed, is a separate identity cost and must be cached; it does not permit a second OpenDota history request.

## 20. Frontend Architecture

The report route remains a Next.js server component for validated fetch, metadata/noindex, and variant dispatch. A new client boundary receives the complete serialized Free DNA report:

```text
app/report/[reportId]/page.tsx              server fetch + variant switch
app/report/[reportId]/dna/report-story.tsx  client navigation/restoration/analytics
app/report/[reportId]/dna/pages.tsx         payload-to-template registry
app/components/story/                       presentation primitives
app/components/share/                       privacy sheet + native share/download
```

Reusable primitives (roughly 12) are `ReportShell`, `StoryPage`, `SectionIntro`, `DimensionPage`, `Spectrum`, `EvidenceReceipt`, `MethodologySheet`, `ArchetypeReveal`, `HeroPortraitCard`/`HeroCluster`, `RecommendationCard`, `ShareCardPreview`, `ProgressIndicator`, and `DeepDiveTeaser`. `SignatureHeroPage`, `ComfortPage`, and summaries are small compositions, not new page frameworks.

The server fetches once; no component fetches OpenDota or recalculates DNA. The client hydrates interaction only. Report loading uses route-level `loading.tsx` with a plain skeleton; API 404 and transient errors use existing `not-found.tsx`/`error.tsx` patterns with improved report-retention copy. Input, Player Found, and Analysis can be a state machine under `/` for V1; optionally use `/analyze/[jobId]` so refresh resumes a job.

Permalinks remain `/report/{opaque-report-id}`. Never put account ID/archetype in the URL. Completed immutable responses can use longer revalidation than the current 60 seconds once report persistence is verified. Use `next/image` or controlled plain images for allowlisted hero assets; do not proxy arbitrary profile URLs into share rendering.

Responsive layout: one-column portrait story from mobile through desktop, max readable content width, safe-area padding, and visual decoration outside the semantic reading order. Methodology sheets are portals/dialogs, not nested page routes. All eight dimensions always keep their story position. Strong/reliable results receive full visual emphasis and are eligible for descriptors/share cards; weak/unavailable results use a quieter “signal faint” template with the missing-data reason and can never be promoted into the highlighted fingerprint.

## 21. Scroll-Snap Story Implementation

Make the page's single scroll container the document/`main` story region—never nest a second vertical scroller around the story.

- Story container: `scroll-snap-type: y proximity` as the V1 default, `overscroll-behavior-y: contain` only if background bleed occurs, and `scroll-padding-top` for safe areas.
- Page: `min-height: 100vh; min-height: 100dvh; scroll-snap-align: start; scroll-snap-stop: normal`.
- Test `mandatory` behind a feature flag. Promote it only if desktop wheel/trackpad and zoom tests show no trapped content; `proximity` is safer for tall content and browser accessibility.
- If page content exceeds the viewport at 200% zoom or large text, allow that page to grow and disable snap for it via a measured `data-overflowing` state/CSS class. Never create an inner scroll box for normal content.
- On iOS/Safari use `100svh` as a minimum/fallback and `100dvh` enhancement; apply `env(safe-area-inset-*)`; test URL-bar expansion/collapse and landscape.
- Methodology uses an accessible modal dialog/bottom sheet with its own bounded internal scroll, `overscroll-behavior: contain`, body scroll lock that records/restores the exact page, focus trap, Escape/close, and focus return.
- Do not intercept wheel/touch to animate scroll. Keyboard handlers activate only when focus is not inside an input/button/dialog: Arrow/Page/Space navigate by `element.scrollIntoView({block:'start', behavior})`; Home/End target ends. With reduced motion, behavior is `auto`.
- Observe page intersection to update progress, dwell events, and URL hash `#breadth` using `history.replaceState`. On load/back navigation, prefer saved `sessionStorage` page ID, then valid hash, then browser restoration. Sharing must not change the active page.
- Semantic DOM order exactly matches visual/story order. Each page has a heading; the progress control is navigation with an accessible current-page label. Screen readers can read continuously without requiring scroll gestures.

Test proximity and mandatory variants on mouse wheel, high-resolution trackpad, touch, keyboard, 200/400% zoom, reduced motion, iOS Safari dynamic viewport, Android Chrome, desktop Safari/Chrome/Firefox, and Windows precision/non-precision wheels.

## 22. Analysis / Loading Experience

Map visible progress to repository events:

| Real checkpoint | User-facing copy |
|---|---|
| `validating_player` / profile resolved | “Found your player.” |
| `fetching_history` | “Finding your recent matches.” |
| `normalizing_history` | “Sorting the matches we can read.” |
| `hero_features` | “Mapping your hero habits.” |
| `role_features` | “Reading your role patterns.” |
| `session_inference` | “Rebuilding your play sessions.” |
| `dimension_scoring` | “Finding your eight DNA signals.” |
| `archetype_classification` | “Turning the patterns into an archetype.” |
| `hero_identity` | “Finding the heroes that define you.” |
| `hero_recommendations` | “Looking for heroes that fit your cast.” |
| `rendering_report` | “Building your Dota DNA.” |
| `completed` | “We found your pattern.” |

Emit stages immediately before/after real module calls. Use SSE as primary because the route now streams until terminal status; retain the existing bounded visibility-aware polling as fallback. Show completed stages or “N of 8 DNA signals read” only after scorers return; do not estimate percentages. For very fast fixture/cached runs, coalesce announcements so the UI does not flash ten lines.

If one scorer fails or lacks data, the dimension service records `unavailable` and continues. Taxonomy failure suppresses Hero Pattern/Recommendations but keeps DNA and factual Signature/Comfort. Only identity failure, no history, fewer than 30 common matches, schema validation failure, or storage failure prevents report completion. On variable API latency, hold the latest truthful message and show elapsed reassurance after thresholds, with retry only after a terminal/recoverable failure.

## 23. Wireframe UI Implementation Strategy

Use scoped design tokens—not analytics-aware components—for the temporary handwritten-paper treatment:

- semantic colors (`--paper`, `--ink`, `--marker`, `--muted`, `--receipt`), spacing, line widths, radii, and motion durations;
- local/static paper texture with a solid-color fallback and no readability-critical texture;
- a legible system/body face plus one self-hosted, licensed handwriting accent subset; share renderer uses the exact same font files;
- SVG/CSS rough borders, underlines, arrows, and tape assets with deterministic seeds/variants so screenshots do not change per render;
- hero portraits placed through a reusable image-frame primitive, not CSS tied to hero analytics;
- spectrum position driven only by numeric props, while rough stroke is decoration;
- motion tokens (`reveal`, `stamp`, `settle`) disabled/reduced under `prefers-reduced-motion`.

Keep page schema, headless interaction logic, and visual primitives separate. A future polished theme should replace CSS/assets without changing API payloads, scorers, page order, accessibility names, or analytics events.

## 24. Share Card Architecture

Use server-side HTML/CSS-to-image rendering in a dedicated API worker or rendering service (Playwright/Chromium) because the actual stack already has containerized backend/workers and requires faithful hero portraits, paper texture, and multiple cards. `satori`/SVG is an alternative if deployment cannot safely run Chromium, but it supports a narrower CSS/font surface. Avoid primary dependence on client DOM screenshot libraries: cross-origin images, font loading, mobile memory, and browser differences make them unreliable. Client canvas/DOM capture remains a downloadable fallback only.

| Card | Size/content | Renderer and tests |
|---|---|---|
| DNA | default 1080×1350 (4:5); archetype, 3 descriptors, up to 3 spectra, match count | Server render from `shares.dna`; golden pixel diff; long name/neutral/partial cases |
| Hero | 1080×1350; Signature portrait, Comfort, Pattern, one recommendation | Server render with versioned local/CDN hero assets; missing portrait fallback and crop tests |
| Final Player | 1080×1350; optional display name/avatar, archetype/descriptors, Signature, Pattern, Rhythm, one fact | Server render after privacy confirmation; most exhaustive golden/browser tests |

Optionally add 1080×1920 (9:16 story) and 1200×630 link-preview variants after the 4:5 card is stable. Card content is a strict subset of the report snapshot and contains no raw account/Steam ID. Profile name/avatar default to on only if the user sees the privacy preview; raw ID is always off and unsupported in V1 share contract.

Embed/subset fonts, wait for `document.fonts.ready` and decoded images, pin renderer/browser/asset versions, disable animation, fix locale/time zone, and hash all inputs. Proxy/copy allowed hero assets to controlled storage; do not render untrusted remote URLs. On mobile, create a `File` and call `navigator.share({files})` when supported; otherwise share permalink/text, copy link, or download PNG. Desktop gets native share if available plus copy/download. Return to the same page/focus after dismissal.

## 25. Privacy and Safety

- Analyze only public OpenDota profile/history data. The server holds the OpenDota key; browsers never receive it.
- Validate identity against the canonical account ID and use opaque report IDs. Reports stay `noindex` and expire after **30 days**. Report JSON, share artifacts, raw anonymous-analysis payloads, and compatible-cache references must share an enforceable deletion/expiry policy documented in the UI and operations runbook.
- Store raw account ID for analysis/persistence where necessary, but omit it from default story headers and all share contracts; mask it on Player Found. Never include it in URLs, analytics, filenames, or image alt text.
- Public display name/avatar may appear in the report. The first share preview offers independent name/avatar toggles. Sanitization and image allowlisting prevent content injection.
- Add a `DELETE /v1/reports/{id}` only after an ownership token mechanism exists; without auth, do not pretend anyone who knows a public link is authorized to delete. V1 can expire reports and provide refresh/reanalysis.
- Missing/private history gets a nonjudgmental error; partial history reduces confidence and is disclosed.
- Resilience copy describes observed next-game association only. Ban “tilt,” emotional diagnosis, mental strength/weakness, causation, and claims about intent.
- Activity/Orientation never imply quality; recommendations are taste adjacency, not coaching or promises of better performance.
- Log job/report IDs and coarse metrics, not player names, full identifiers, raw payloads, or share toggles tied to identity.

## 26. Analytics Instrumentation

Create a vendor-neutral `track(eventName, payload)` web adapter and server `record_metric()` seam because no analytics provider is selected. A no-op/local test adapter is the V1 default; adding a provider later must not change UI components. Event names use lowercase dot notation and a schema version, for example `analysis.started.v1`.

### Funnel

`identity.input_focused`, `identity.pasted`, `analysis.clicked`, `player.resolved`, `analysis.started`, `analysis.completed`, `analysis.failed`. Payload: anonymous session ID, input type (not value), reused/cache flag, elapsed bucket, failure code, processed/eligible count bands, report schema/model versions.

### Engagement

`report.page_viewed`, `report.page_exited`, `report.methodology_opened`, `report.methodology_closed`, `report.completed`. Payload: report-scoped random analytics ID, page/section/kind, ordinal, direction, dwell milliseconds bucket, archetype key, dimension availability/confidence, model versions, viewport class, reduced-motion flag. Do not send dimension evidence values if they make a player fingerprint unnecessarily specific.

### Sharing

`share.initiated`, `share.completed`, `share.failed`, `share.link_copied`, `share.image_saved`; payload card type, aspect ratio, channel capability (`native_files`, `native_link`, `download`, `clipboard`), renderer version, privacy booleans—not name/avatar/ID.

### Conversion

`deep_dive.teaser_viewed`, `deep_dive.cta_clicked`, and, only if checkout exists, `checkout.started`/`purchase.completed`. Preserve a privacy-safe attribution ID; never infer purchase from CTA.

Server metrics include cache outcome, OpenDota request count/status, stage latency, dimension availability, archetype distribution, taxonomy/recommendation failure, share render result. Define event schemas in source control and test required/forbidden fields. Dwell uses intersection plus visibility state and flushes on page change/pagehide; deduplicate repeated observer events.

## 27. Testing Strategy

### Unit and property tests

- Summary normalization: side/win attribution, every nullable field, invalid values, dedupe, eligibility masks.
- Session inference: ordering invariance, duration-aware gaps, midnight, 60/90/120 sensitivity, overlaps, undated rows.
- Every dimension: cases listed in Section 8, exact denominators, confidence boundaries, neutral behavior, copy-key guardrails.
- Archetype/descriptors: all prototypes, ties, missing/neutral vector, exact three, group diversity, no redundant/restated descriptors.
- Hero identity: smoothing, recency, persistence, role/semantic fallback, deterministic ties.
- Taxonomy/pattern/recommendations: schema completeness, IDF, exclusivity, candidate exclusion, diversity, reasons.
- Report builder: schema/version tuple, immutable ordering, no raw ID in shares/pages, partial fallback.
- Property tests: score bounds, input-order invariance where applicable, missing fields never raise confidence, adding identical evidence does not reverse obvious concentration, deterministic output.

### Synthetic fixture players

Add generated 500-row fixtures for focused support specialist; broad flexible player; high-activity mid; comfort-driven carry; exploratory utility; low-role-data player; 40-match player; grinder with declining endurance; short-burst resetting player. Add adversarial fixtures for duplicate/conflicting rows, all K+A zero, no timestamps, patch boundary, private profile, role-confounded adaptability, and only single-match sessions. Keep the current recorded fixture for regression but do not calibrate thresholds from one account.

### Snapshot/golden tests

Snapshot full `FreeDnaReport` JSON after removing report ID/timestamps. Any model-version change intentionally regenerates goldens with review. Golden share images use perceptual thresholds and pinned fonts/browser/assets.

### UI and E2E

Component tests cover Dimension unavailable/neutral/extremes, methodology focus management, privacy toggles, native-share capability fallbacks. Playwright covers input -> Player Found -> real staged analysis -> full 23-state story -> share -> teaser; scroll snap on wheel/touch/keyboard; backtracking/restoration; modal/snap interaction; narrow/large/zoomed/reduced-motion layouts; missing hero metadata; expired/transient report errors. Add automated axe checks plus manual VoiceOver/NVDA passes.

### Contract and cost tests

Assert Free mode calls `get_matches(limit=500)` exactly once per cache miss and never calls `get_match`/parse. Test Steam32/Steam64, numeric Steam profile URLs, OpenDota URLs, vanity resolution/cache/failure, and ensure vanity lookup never duplicates OpenDota history. Validate API payload against generated TypeScript/OpenAPI types. Test cache compatibility across every version change and privacy scanning of share contracts/artifacts.

## 28. Observability

Emit structured logs with job/report IDs, stage, duration, cache state, and error code; never raw player input or API keys. Metrics/dashboards:

- OpenDota request count/latency/status/retries/429s and response row count;
- total and per-stage report latency, queue latency, worker failures/retries;
- processed/eligible distribution and exclusion reasons;
- non-null coverage for hero, role, K/D/A, timestamp, party, patch;
- each dimension's available/limited/unavailable rate, score histogram, confidence histogram;
- session count/length and threshold sensitivity failure rate;
- archetype and descriptor distribution, top-two fit margins, fallback rate;
- Signature/Comfort concentration, no-pattern/no-recommendation rates, recommendation diversity;
- report cache/upstream cache/share artifact hit rates;
- share render latency/failures/missing assets/fonts;
- story completion, page abandonment, methodology/share/conversion funnels.

Alert on Free detail-read count >0, OpenDota 429/error spikes, >20% report schema failures, any dimension null-rate jump beyond baseline, >30% archetype fallback, one archetype >35% after adequate sample, one descriptor >60%, recommendation empty rate >10% when taxonomy is healthy, and share failure >2%. Attach all model/taxonomy versions to distribution metrics so releases are comparable.

## 29. Calibration and Validation Plan

Before describing DNA as trustworthy:

1. Build a consented/deidentified sample of at least several hundred public players spanning roles, skill bands, patches, and history sizes; reserve a holdout set.
2. Plot every raw feature and score; inspect ceiling/floor pileups, neutral rate, missingness by cohort, and temporal stability.
3. Measure Spearman correlations and mutual information among eight scores. Conceptual orthogonality does not guarantee empirical independence; flag |rho| >0.6 and inspect whether shared inputs or role confounding cause it.
4. Run archetype distribution, fit-margin, entropy, dead/overrepresented prototype, and descriptor redundancy reports.
5. Have Dota-literate reviewers independently assess blinded feature receipts, not just flattering copy. Record agreement and concrete disagreement reasons.
6. Run player feedback with “sounds like me” Likert, confidence, and a structured “wrong because…” choice (data missing, role wrong, recent change, interpretation, other).
7. Sensitivity-test session gaps, familiar-pool definitions, minimum samples, smoothing priors, baseline cells, archetype weights, and taxonomy revisions.
8. Freeze V1 thresholds/prototypes, publish a model card/known limitations, and increment versions for every calibrated change. Never silently recompute historical reports.

Acceptance targets before broad release: >=70% “mostly/very much like me” on complete reports, no archetype >25% without an explained population reason, <10% forced fallback among >=100-match public profiles, descriptor duplication <5%, and direction stability >=80% across bootstrap/adjacent windows for high-confidence dimensions. These are recommended starting gates, not validated truths.

## 30. Implementation Phases

### Max-effort Luna execution protocol

The implementation is intended to complete in one continuous working session led by **GPT Luna at max reasoning effort**. The lead agent must create and maintain milestone status, keep the repository buildable at every gate, and use additional max-effort Luna agents for bounded parallel work after the report contract is frozen. All agents share the worktree, so ownership must be non-overlapping and explicit.

Recommended orchestration:

1. **Lead Luna — integration owner:** repository re-audit, decisions/contracts, `AnalysisService`, report/API schema, version/cache compatibility, final integration, and end-to-end verification.
2. **DNA Luna — analytics owner:** normalized summary, eligibility, sessions, features, eight dimensions, confidence, archetype/descriptors, synthetic fixtures and backend goldens. It owns only `ingestion/summary_*`, `dna/`, and corresponding tests.
3. **Heroes Luna — metadata/recommendation owner:** read every file under `heroes_metadata/`, create reviewed structured factual/editorial snapshots, Signature/Comfort/Pattern/Recommendations, and taxonomy tests. It owns only `heroes/`, taxonomy data, and corresponding tests.
4. **Experience Luna — web/share owner:** story state machine, reusable pages, scroll/accessibility, report UI, share templates/fallbacks, Playwright fixtures/tests. It owns only `apps/web` and share-render presentation paths after receiving the frozen contract.

If concurrency is limited, run DNA and Heroes first while the lead freezes API contracts; start Experience against a frozen representative payload as soon as that contract exists. Agents must not edit the same file concurrently. Cross-cutting changes are requested from the lead, not made opportunistically. Every delegated task must state exact owned paths, acceptance tests, data boundary, and the rule that Free mode may not call match details or replay parsing.

Milestone gates for the single session:

- **M0 — Contract frozen:** accepted identifier forms, 500-row request, All Pick eligibility, eight always-present dimension states, report schema, 30-day expiry, and version tuple documented.
- **M1 — Analysis green (priority gate):** one 500-row history call, normalized features, sessions, eight scores/confidence, archetype/descriptors, synthetic goldens, and zero detail reads all pass. Do not let visual work weaken or bypass this gate.
- **M2 — Hero system green:** all 127 metadata files reviewed into the taxonomy; Signature/Comfort/Pattern/Recommendations and safeguards pass.
- **M3 — Live API green:** real job stages, immutable report persistence/cache compatibility, Steam identifier resolution, partial/failure behavior, and live fixture plus opt-in OpenDota smoke pass.
- **M4 — Complete story green:** all 23 states render from the same report payload with eight visible dimensions, strong-only highlighting, navigation/accessibility/restoration, and Deep Dive teaser.
- **M5 — Share/telemetry green:** three privacy-safe deterministic cards, native/copy/download fallbacks, no-op vendor-neutral analytics, and 30-day retention hooks.
- **M6 — Release gate:** lint, types, unit, contract, integration, build, browser/E2E, accessibility, privacy, cost invariant, and clean diff review pass together.

The lead should use the app's milestone/plan mechanism, post concise progress after each gate, and recruit/follow up with the Luna agents rather than serially redoing their bounded work. A failed gate is fixed before downstream integration proceeds. The session is not complete when only one of analysis, fixture story, or live vertical slice works; all three must pass M6 in the same session.

### Phase 0 — Repository alignment

- **Scope/files:** encode the decided Free/Deep boundary, ranked + unranked All Pick policy, Steam numeric/URL/vanity identifiers, 500-row history call, 30-day retention, and provider-neutral seams; update this plan/`system-behavior-baseline.md`.
- **Deliverables/dependencies:** ADRs and accepted contracts; no feature dependency.
- **Tests/DoD:** baseline commands green; fixture proves zero detail reads; owners approve taxonomy/calibration workflow.

### Phase 1 — Data foundation

- **Scope/files:** `summary_normalize.py`, expanded summary models, eligibility masks, raw metadata/cache compatibility, fixtures; production limit config.
- **Deliverables:** complete nullable normalized summary and exclusion ledger.
- **Dependencies:** Phase 0 decisions.
- **Tests/DoD:** all inventory fields covered; dedupe/side/win/partial fields tested; exactly one <=500 history call requesting 500.

### Phase 2 — Feature extraction

- **Scope/files:** `dna/features/*`, `dna/sessions.py`, versioned feature contracts.
- **Deliverables:** hero/role/combat/session feature set with evidence provenance.
- **Dependencies:** normalized matches.
- **Tests/DoD:** order invariance, gap sensitivity, exact denominators, fixture snapshots.

### Phase 3 — DNA scoring

- **Scope/files:** confidence, baseline interface, eight scorer modules and provisional V1 baseline files.
- **Deliverables:** eight available/limited/unavailable `DimensionResult`s.
- **Dependencies:** Phase 2; initial role expectations.
- **Tests/DoD:** every Section 8 case; no unqualified role-relative copy; partial report succeeds.

### Phase 4 — Archetype synthesis

- **Scope/files:** prototype JSON, classifier, descriptors, archetype copy keys.
- **Deliverables:** one versioned archetype and exactly three truthful descriptors.
- **Dependencies:** dimensions.
- **Tests/DoD:** golden prototypes, ties, neutral/missing profiles, deterministic output.

### Phase 5 — Hero identity

- **Scope/files:** factual hero map, `heroes/identity.py`, `comfort.py`.
- **Deliverables:** Signature and 3–5 Comfort results without semantic dependency.
- **Dependencies:** hero features and factual roster.
- **Tests/DoD:** smoothing/persistence/ties/low history covered; “most played” is not hard-coded.

### Phase 6 — Hero semantics and recommendations

- **Scope/files:** read all 127 `heroes_metadata/*.md` sources; produce taxonomy schema/manifest/snapshots and editorial review ledger; implement pattern/recommendation engines.
- **Deliverables:** reviewed complete V1 taxonomy, patterns, three diverse recommendations.
- **Dependencies:** explicit taxonomy build/review task; Phase 5.
- **Tests/DoD:** every metadata source is accounted for in the review ledger, roster complete, provenance/version valid, IDF/diversity safeguards pass, graceful suppression works.

### Phase 7 — Report payload

- **Scope/files:** `dna_assembly.py`, Pydantic schemas/OpenAPI/client generation, repository compatibility keys, content catalog.
- **Deliverables:** coherent immutable `free-dna-report-1.0.0`.
- **Dependencies:** Phases 3–6.
- **Tests/DoD:** contract/golden/privacy/version tests; legacy deep report still renders.

### Phase 8 — Story UI

- **Scope/files:** input/found/progress state machine, report variant dispatch, story primitives, 23 page definitions, methodology sheets, CSS theme.
- **Deliverables:** responsive accessible wireframe story.
- **Dependencies:** report contract; fixture API.
- **Tests/DoD:** wheel/touch/keyboard/zoom/reduced-motion/restoration across browser matrix.

### Phase 9 — Share cards

- **Scope/files:** share service/worker, card templates, assets/fonts, web share controls/privacy preview.
- **Deliverables:** DNA/Hero/Final PNGs and link/download fallbacks.
- **Dependencies:** report snapshot and stable assets.
- **Tests/DoD:** deterministic golden images; no raw ID; mobile/desktop fallbacks verified.

### Phase 10 — Instrumentation and validation

- **Scope/files:** event adapter/schemas, server metrics, calibration scripts/notebooks/output docs.
- **Deliverables:** funnels/distribution dashboards and first calibration report.
- **Dependencies:** end-to-end experience and sample.
- **Tests/DoD:** forbidden PII tests; event dedupe; no collapsed archetype/dimension distributions.

### Phase 11 — Release hardening

- **Scope/files:** hosted CI, load/rate-limit/cache tests, retention, accessibility/security review, deployment configs/runbooks.
- **Deliverables:** production candidate and rollback/version plan.
- **Dependencies:** all phases.
- **Tests/DoD:** all checks green; zero Free detail reads under load; SLOs/alerts/runbook live; launch gates from Section 29 met or explicitly waived.

## 31. Recommended PR Breakdown

1. **Normalized summary contract + per-dimension eligibility + fixtures.** No scoring.
2. **Versioned session inference + sensitivity tests.** Preserve current summary detector adapter.
3. **Hero/role/combat/session feature extraction.** Evidence/provenance only.
4. **Breadth, Role, Activity, Orientation scorers.** Baseline interface and confidence.
5. **Adaptability, Resilience, Endurance, Rhythm scorers.** Within-player contrasts and partial states.
6. **Archetype prototypes + classifier + descriptor engine.** No UI.
7. **Factual hero identity + Signature/Comfort.** No semantic recommendation claims.
8. **Hero taxonomy schema/editorial snapshot.** Data-only reviewable change with provenance.
9. **Hero Pattern + recommendation engine.** Deterministic copy keys and safeguards.
10. **Free DNA report schema/builder + API-client generation + versioned caching.** Preserve legacy/deep report.
11. **Input/Player Found/real progress experience.** SSE with polling fallback.
12. **Report shell + scroll-snap primitives + accessibility/restoration.** Fixture pages.
13. **Eight Dimension pages + methodology + archetype reveal.** One template.
14. **Hero pages + recommendations + partial metadata states.** Reusable hero primitives.
15. **DNA/Hero/Final summary pages + Deep Dive teaser.** No image export yet.
16. **Share renderer + privacy preview + native share/download.** Golden images.
17. **Analytics/observability + calibration harness.** No threshold tuning mixed with UI.
18. **Calibration update PR.** Explicit score/prototype/taxonomy version bumps and reviewed goldens.
19. **CI/browser matrix/release hardening.** Deployment configuration, alerts, retention/runbook.

Each PR must keep `make test`, `make typecheck`, relevant Playwright suites, and the Free zero-detail-read contract green. Algorithm changes must not be bundled with visual polish; taxonomy changes carry their own version/review.

## 32. Risks and Open Questions

| Risk/open question | Severity | Mitigation/default | Blocks V1? |
|---|---|---|---|
| Summary role hints are sparse/wrong | High | Coverage gates, confidence, factual hero priors only as support, role-relative copy guard | No; Role/adjustments can be limited/suppressed |
| No validated population baselines | High | Within-player V1 plus provisional role tables; cap confidence; calibration phase | No for prototype; yes for strong public claims |
| Familiar/off-pool selection bias | High | Time-split definition/evaluation, smoothing, role strata, minimum groups | No if low-confidence states work |
| Session inference ambiguity | High | duration-aware 90m rule, 60/120 sensitivity, versioning | No |
| Resilience interpreted psychologically | High | product/content lint, association-only evidence, forbidden terms | Yes if copy cannot be constrained |
| K/A measures are role/team-tempo biased | High | role baselines, descriptive fallback, no quality claim | No |
| Endurance late-session sample/stop bias | High | independent-session weighting, minimum late games, confounder; retain the page as weak/unavailable | No |
| Dimensions correlate strongly | High | correlation audit; change shared-input weights or taxonomy with new version | Possibly, if archetypes become redundant |
| Archetype prototypes overfit/collapse | High | fit margins, fallback, distribution alerts, calibration | Yes for public archetype launch |
| Hero taxonomy is subjective/volatile | High | factual/editorial split, two-person review, immutable snapshots | Yes for Pattern/Recommendations, not DNA |
| Third-party hero markdown provenance/licensing | High | research-only; derive structured claims from allowed factual sources/manual review | Yes if runtime copies it directly |
| Recommendation feels like coaching/meta advice | Medium | taste/trait reasons only; omit win/meta layer | No |
| OpenDota rate limits/outages | High | caches, coalescing, retries, one-request budget, retry UI | No, operational launch gate |
| Public/private profile availability | Medium | Player Found, clear unavailable/partial states | No |
| `infra/compose.yaml` currently uses history limit 50 and code caps 200 | High | raise constants, source adapters, settings validation, fixture/runtime config, and compose to an explicit maximum/default of 500 | Yes |
| Share rendering differs across browsers | Medium | server renderer, pinned assets/fonts/browser, goldens | No for report; yes for share launch |
| Remote portrait/avatar safety/availability | Medium | controlled hero assets, validated profile fallback, privacy toggle | No |
| Desktop scroll snap traps/overshoots | Medium | proximity default, overflow escape, feature test mandatory | No |
| Anonymous report expiry must cover every storage layer | Medium | enforce the decided 30-day TTL for reports, artifacts, compatible-cache links, and retained raw anonymous-analysis data through a scheduled cleanup job | Yes for production |
| Steam vanity resolution adds a non-OpenDota dependency | Medium | support numeric IDs/`profiles/{steam64}` locally; isolate and cache `/id/{vanity}` through a Steam resolver with actionable configuration/failure state | No for numeric inputs; yes for promised vanity URLs |
| No analytics provider/CI workflow | Medium | vendor-neutral adapter; add CI in hardening | Analytics/CI block broad launch, not prototype |
| Share links may be forwarded during the 30-day window | Medium | opaque report UUID + noindex + 30-day expiry; signed/expiring asset URLs; clear “anyone with link” copy | No |

## 33. Explicit Non-Goals for V1

- Replay parsing or automatic parse requests.
- Per-match detail reads for Free DNA.
- Item-timing, warding, healing, map positioning, draft, teamfight, objective, economy, or lane-performance diagnosis.
- Full coaching recommendations, improvement plans, hero meta/counter advice, or MMR prediction.
- Psychological diagnosis, “tilt,” motivation, intent, or emotional claims.
- Perfect global/cohort-normalized percentiles.
- Empirically final archetype truth or unsupervised clustering in the serving path.
- LLM-generated core scores, archetypes, evidence, patterns, recommendations, or live copy.
- Authentication, saved histories, try lists, or social graphs.
- User-editable hero taxonomy/admin UI.
- Real-time mutation of old reports after taxonomy/model changes.
- Final polished visual system, advanced animation, parallax, or confetti.
- More than the current public summary data boundary merely to fill a missing dimension.

## 34. Final Implementation Checklist

### Data

- [ ] Raw history persisted with endpoint, hash, fetch metadata, and one request for <=500 rows.
- [ ] Normalized summary contains every required nullable field and correct win/side.
- [ ] Common and per-dimension eligibility ledgers are explicit and tested.
- [ ] Duplicates, missing timestamps, short/abandoned/unusual matches degrade correctly.
- [ ] Free mode performs zero detail/parse calls.

### Analytics

- [ ] Versioned feature and session contracts implemented with provenance.
- [ ] Eight scorers meet hard sample/coverage rules and emit neutral/unavailable states.
- [ ] Confidence falls with missing/unstable data.
- [ ] Role-adjusted claims cannot appear without role support.
- [ ] V1 baseline source/limitations documented; calibration distributions reviewed.

### Archetypes

- [ ] Working prototypes live outside UI/code branches in a versioned snapshot.
- [ ] Classifier is interpretable, deterministic, tie-safe, and missingness-aware.
- [ ] Exactly three nonredundant truthful descriptors are returned.
- [ ] Neutral/low-confidence fallback is explicit.
- [ ] Distribution/dead-archetype monitoring exists.

### Heroes

- [ ] Factual and editorial taxonomy data are separate, complete, reviewed, and versioned.
- [ ] Existing scraped hero markdown is research-only, not a runtime taxonomy.
- [ ] Signature/Comfort scores use recurrence, recency, persistence, smoothing, and fit.
- [ ] Hero Pattern uses agreement + IDF and deterministic fallback.
- [ ] Recommendations enforce played-hero exclusion, role fit, adjacency, and diversity.

### API

- [ ] One coherent `free-dna-report-1.0.0` payload validates before persistence.
- [ ] All model/taxonomy/copy versions and raw hash are traceable.
- [ ] Cache compatibility includes all relevant versions.
- [ ] Real stage events and partial-analysis warnings are exposed.
- [ ] Generated/central API types are consumed by web.

### Frontend

- [ ] 23 states are composed from ~10–12 reusable primitives.
- [ ] Report UI never recalculates analytics.
- [ ] Input, Player Found, truthful progress, partial/error states work.
- [ ] Story restoration, hash/page state, responsive layout, and methodology overlays work.
- [ ] Wireframe styling can be swapped without domain changes.

### Sharing

- [ ] DNA, Hero, and Final cards render deterministically at 4:5.
- [ ] Raw Steam/account ID cannot enter any card.
- [ ] Name/avatar privacy preview works.
- [ ] Native file share, link share, copy, and download fallbacks are tested.
- [ ] Fonts, portraits, renderer, and artifact inputs are pinned/versioned.

### Accessibility

- [ ] Semantic story order/headings and progress navigation are correct.
- [ ] Keyboard, touch, wheel, focus return, Escape, Home/End, and Space work.
- [ ] Reduced motion and 200/400% zoom remain usable.
- [ ] Snap releases for overflowing content and does not trap modal scrolling.
- [ ] VoiceOver/NVDA plus automated WCAG checks pass.

### Analytics

- [ ] Funnel, page/dwell/direction, methodology, share, and conversion events validate.
- [ ] Event payloads exclude raw identifiers/names.
- [ ] Cache, latency, missingness, distribution, and renderer dashboards exist.
- [ ] Alerts detect model collapse and Free budget violations.

### QA

- [ ] Synthetic player fixtures and adversarial missing-data fixtures are committed.
- [ ] Deterministic report JSON and share-image goldens are reviewed.
- [ ] Full Steam ID -> analysis -> story -> share -> teaser E2E passes.
- [ ] Browser/device/viewport/snap matrix passes.
- [ ] Existing deep report and API contracts remain green.

### Release

- [ ] Production Free history limit/default is 500 and caches/workers/storage are configured.
- [ ] Hosted CI runs lint, typing, unit, contract, integration, build, and E2E suites.
- [ ] Calibration gates are met or explicit limitations/waivers are approved.
- [ ] Retention/privacy/runbook/rollback and version-bump process are documented.
- [ ] First shippable milestone validates story, comprehension, payoff, recommendations, and share intent before final visual polish.
