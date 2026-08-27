# STRATZ parsed-data enrichment research

Brief: `docs/prompts/stratz/02-opus5-enrichment-research.md`
Date: 2026-08-27 · Evidence: `.local/stratz-probe/enrichment/`
Reproduce every number: `python3 .local/stratz-probe/enrichment/analyze.py`

| | |
|---|---|
| `01-field-inventory.md` | verified paths, coverage, semantics, rejected fields |
| `02-finding-reassessment.md` | every Element, family and semantic outcome |
| `03-candidate-catalog.md` | 52 raw ideas → 12 clusters → ranked tiers |
| `04-corpus-lineage-roadmap.md` | corpus design, version surfaces, roadmap |
| `05-blocked-and-queries.md` | BLOCKED list with the query that resolves each |

---

## Research status

**PARTIAL.**

Live parsed payloads were captured and analysed (7 successful operations of 8
attempted, one core match,
one support match, one unparsed match, ten-player context, and a playback
sample), so the core semantics questions are **resolved from data, not
inferred**. Three things keep this from PASS: Pack B and Pack C are written but
not yet run, so roughly a third of the parsed surface remains un-queryable;
STRATZ licensing is still `UNKNOWN`; and automated API access does not work at
all, which blocks any corpus independently of licensing.

---

## Headline conclusion

STRATZ's most valuable contribution is not the replay detail the brief was
commissioned to explore — it is `position` at 91% and `role` at 93% coverage, which
arrive **free inside the history pull** and let Dota Report say something it
currently cannot say at all: that a player plays support. Everything genuinely
parsed — trajectories, event timing, items, wards — sits behind a **~300× request
cost cliff** and should be treated as a second, separately justified investment.
The first STRATZ-native analytical generation should be built almost entirely
from the history tier.

---

## Verified capability summary

In behavioural terms, STRATZ adds four things, in descending order of value.

**1. Role becomes observable.** `position` (91%) and `role` (93%) versus
OpenDota's ~2.5% lane proxy. This is not an accuracy improvement — it is a
vocabulary that did not exist. `ROLE_HINTS` is `{carry, mid, offlane, jungle,
roamer}`. `roamer` is the only support-adjacent token, it is reachable only via
OpenDota's `is_roaming` flag, **STRATZ `MatchLaneType` has no roaming value at
all**, and it cannot split `POSITION_4` from `POSITION_5`. On the specimen, 20
of 49 eligible matches (41%) are supports and **all 25 parsed support rows map
onto a word V6.1 treats as a core role**.

**2. Context adjustment starts working.** `gameVersionId` is 100% covered versus
~2.5% on OpenDota. `patch` is a dimension in five of the six
`BASELINE_HIERARCHY` levels, so today almost every match falls through to the
`overall` cell — meaning "context-adjusted" currently means "global mean
subtracted". Patch and role together make the top of the hierarchy reachable
for the first time.

**3. Game state over time, at match level, for free.** `radiantKills`,
`direKills`, `radiantNetworthLeads` and `radiantExperienceLeads` are per-minute
integer arrays on `MatchType` — no per-player parsed dependency, no playback.
Plus `bottomLaneOutcome` / `midLaneOutcome` / `topLaneOutcome`, which are direct
measurements of something V6.1 has zero access to.

**4. Within-match structure.** Event timestamps (kills, deaths, assists, item
purchases, wards, runes, level-ups), per-minute economy series, and full
playback. Real, and expensive.

### What the payloads corrected in the brief

- **The array-length mystery is solved.** Per-minute arrays are
  `floor(duration/60)`; `networthPerMinute` is `+1` (it carries a t=0 sample);
  match-level arrays are `+2`. The brief's unexplained "26 vs 25" is exactly this.
- **But the arrays do not share a semantics** — a problem the brief did not
  reach. Verified by summing each against its scalar: `lastHitsPerMinute`,
  `deniesPerMinute`, `towerDamagePerMinute`, `healPerMinute` and
  `heroDamagePerMinute` are per-minute **deltas**; `experiencePerMinute` is XP
  gained in that minute (not a rate); `goldPerMinute` is a **running average**;
  `networthPerMinute` and `heroDamageReceivedPerMinute` are **cumulative levels**.
  Four meanings, one naming convention, all typed `[Int]` of plausible length.
- **`stats.level` is confirmed level-up timestamps.**
- **`roleBasic` is rejected twice over**, not once: it defaults to `CORE` on
  unparsed matches *and* reports `LIGHT_SUPPORT` for both `HARD_SUPPORT` players
  on a fully parsed one.
- **`radiantKills`/`direKills` count opposing hero *deaths*, not scoreboard
  kills** — verified against the ten-player scoreboard (68 vs 67 on the Dire
  side; one radiant death credited to no player). Getting this backwards
  silently corrupts any participation denominator.
- **Unparsed `stats` is an object of nulls**, not null.
- **Parsed availability is a milder confounder than assumed**: Turbo 86% parsed,
  ranked 96% — not "unparsed = Turbo".
- **New operational limit:** query complexity is capped at **310,000**. Full
  introspection costs 6,159,595 and is rejected outright.
- **`campStack` cannot be classified** from these payloads — it sums to 0 and is
  monotonic in both samples, so delta and cumulative are indistinguishable.
- **The 128-feature supporting-signal catalog is generated, not designed.**
  `_catalog()` is `8 groups × range(1, 17)`; within a group every entry is
  identical. The brief's instruction to map candidates onto existing slots
  cannot be followed because the slots are not individuated. Its eight
  `_REJECTED` entries *are* real; parsed data touches four and overturns the
  stated *reason* for two (`X13` role, `M12` item build).

---

## Existing finding reassessment

Full reasoning in `02-finding-reassessment.md`. Nothing is retired.

**Elements:** `breadth` KEEP · `toolkit` **B. REPLACE_PROXY** · `involvement`
**B. REPLACE_PROXY** · `finishing` A. ENHANCE · `death_exposure` A. ENHANCE ·
`transfer` KEEP (family splits) · `consistency` **E. BACKSTAGE_EVIDENCE_ONLY**.

**Families:** `pool_shape` **C. NEW_SUBFINDING** · `transfer`
**C. NEW_SUBFINDING** · `post_loss_response` **A. ENHANCE_EXISTING** ·
`combat_expression` **B. REPLACE_PROXY** · `session_drift` **G. REJECT for now**.

**28 semantic outcomes:** 7 ENHANCE · 6 REPLACE_PROXY · 2 NEW_SUBFINDING ·
7 BACKSTAGE_EVIDENCE_ONLY · 3 REJECT-for-now · 3 KEEP-shadow. (Sums to 28.)

Two findings that fall out of reading the code rather than the data, and that
the owner needs regardless of STRATZ:

- **Six of the 25 public branches are hard-coded to `p = 1.0`** in
  `v61_branch_p_values` — the fixture/synthetic path. The production path
  computes all of them, so this is a fixture-path defect, not a permanent one;
  which path production runs needs confirming. Separately, the `*_delta`
  threshold keys the pipeline requests are absent from `DEFAULT_THRESHOLDS`,
  which makes `post_loss_response` and `session_drift` unpublishable without an
  injected calibrated artifact.
- **`finishing` and `consistency` are public Elements belonging to no finding
  family** — measured and never tested.

---

## Tier 1 recommendations

Both are `[H]` — computable from the history pull at **zero marginal request
cost**.

**T1-A · Role Shape** — `C. NEW_SUBFINDING` under `pool_shape`. Score 96.8/100,
the highest in the catalog. Role-mix entropy plus hero-pool/role-pool overlap.
The only candidate with **no role-fairness exposure at all**, because role is
the measurement. On the specimen, only 2 of 18 eligible-set heroes are played in
both a core and a support role — a strongly role-partitioned pool, and the copy
must read that direction as readily as the opposite one. Answers "do I play one role or several, and does my hero pool
agree?" — the most-discussed, least-measured thing in Dota self-description.

**T1-B · Post-loss control matching upgrade** — `A. ENHANCE_EXISTING`. Score
77.6, ranked fifth, and Tier 1 anyway because it is the **only candidate that
costs zero multiplicity budget**: no new hypothesis, branch, copy or family.
`post_loss.py`'s four-level context backoff currently matches on
`patch+lane_context+hero_function` where both keys are ~2.5% populated, so it
degrades to "anything" on essentially every transition. With patch at 100% and
role at 93%, level-0 matching becomes real for the first time. Its backtest
tells the owner whether currently-published post-loss findings were confounded.

**Held back deliberately:** Role/Hero Transfer Split (87.2) and Role Migration
(85.0) both outrank T1-B and are both free. They are Tier 1-adjacent, gated on
T1-A validating, because all three are functions of the same `role` field —
shipping them together would triple the role multiplicity for one discovery and
make the onstage story repetitive.

---

## Tier 2 recommendations

Both need per-match parsed queries and sit behind the cost cliff.

**T2-A · Kill Participation Share** — `B. REPLACE_PROXY` for `involvement`.
Verified computable: 43 participation instants ÷ 68 team kills = 63.2% on the
sampled match. `involvement` is `(K+A)/minute`, a rate with no denominator,
confounded by team tempo and duration. Participation share removes both.
Promote when batching (C1) resolves favourably **and** it proves role-fairer on
the corpus.

**T2-B · Lane Outcome Record** — `C. NEW_SUBFINDING`. The publishable form is
the *disagreement* between lane outcome and match outcome, not the win rate —
"you win your lane 60% of the time" reduces to "you won more" and is rejected
on the brief's own rule. Blocked additionally on the lane→side mapping, where a
sign error would invert the finding invisibly. May be **core-only**; if so it
must say so.

---

## Experimental

XP Timing Curve · Item Signature · Vision Behaviour · Death Structure ·
Adaptation. Details and the specific question each answers are in
`03-candidate-catalog.md` §6. Two notes worth surfacing: Vision Behaviour is
verified **role-conditional** (1 ward for the core, 27 for the support in the
sampled matches), so any cross-role comparison is meaningless; and Death
Structure sits one inference away from `death quality`, which is banned.

---

## Rejected

`roleBasic` · all proprietary scores (`imp`, `award`, `behavior`,
`streakPrediction`, `averageImp`) · all model outputs (`analysisOutcome`,
`predictedOutcomeWeight`, `winRates`, `predictedWinRates`) · all rank/MMR
surfaces · `intentionalFeeding` · solo-vs-party (`partyId` 8%, null semantics
unestablished) · local-time inference · patch causality · item-build identity
from final inventory · Roshan participation (field returned empty on a
3586-second game) · map movement at product tier · chat behaviour · a sixth
finding family for role · any within-match breakpoint search · Turbo inclusion
to raise sample size. Reasons in `03-candidate-catalog.md` §7.

`analysisOutcome` deserves its own line: it returned `"COMEBACK"` on a match
whose net worth lead swings from −6023 to +13944 in the final two minutes. The
classification is defensible — and reconstructible from the raw lead curve we
already have. That is the argument for rejecting it. Using theirs buys nothing
and costs provenance.

---

## Statistical risks introduced

1. **The role vocabulary activation trap.** Mapping STRATZ `lane` onto
   `ROLE_HINTS` at 93% coverage would activate a broken vocabulary at scale —
   turning a latent misclassification into an active one across ~27% of parsed
   rows. **The sibling migration document must not do this.** This is the one
   cross-document warning in this research.
2. **Every Element value moves.** Patch and role coverage change which baseline
   cell each match resolves against, with no formula edit. Separately, admitting
   Turbo would swing `breadth` by **+1.75 effective heroes** on the specimen
   (10.60 over the 49 eligible matches vs 12.35 over all 100). This is the
   highest regression risk in the plan.
3. **Array-semantics heterogeneity.** Four different meanings under one naming
   convention, all typed `[Int]`. A trajectory feature that treats them
   uniformly is wrong and the error is invisible.
4. **Wrong participation denominators.** `radiantKills`/`direKills` count
   opposing deaths, not scoreboard kills. The gap varies by match, so the bias
   is not a constant that cancels.
5. **Within-match dependence.** Forty-three participation instants in one match
   are one observation. Every candidate declares its clustering level
   (event → match → session → player) and resampling stays at complete sessions.
6. **Multiplicity.** 52 raw ideas collapse to **12 hypotheses** after
   correlation clustering. Twelve is the number that enters the FDR structure,
   not 52. No sixth family is proposed — that would expand the BH denominator
   from 5 to 6 and dilute every existing family.
7. **Correlated candidates rank adjacently.** The top three all read the same
   field. The ranking model cannot see this; the tiering overrides it explicitly.
8. **Time series invite spurious structure.** A 59-element series has ample
   degrees of freedom to yield a breakpoint in noise. No within-match breakpoint
   search is proposed.
9. **Opportunity counts, not match counts.** Every candidate carries its own
   denominator. The sampled support placed 27 wards; the core placed 1.
10. **Parsed availability as selection.** Milder than the brief assumed (Turbo
    86%, ranked 96%) but real, and `isParsed` makes it a trap — filtering at
    acquisition time silently conditions everything downstream.
11. **Baseline cells will be sparser than hoped.** `patch+hero+lane` fails the
    `match_count >= 200` condition at 1,000 players even under an optimistic
    uniform allocation, and hero play is Zipfian. The plan must not promise it
    and deliver `patch+lane`.
13. **The eligible population itself is not yet settled.** The
    `LeaverStatusEnum` mapping is BLOCKED and its two readings differ by 4
    matches on the specimen — which moves the support share (41% vs 44%), the
    yearly opportunity count (293 vs 269) and every cost figure derived from
    them.
12. **Tighter control matching shrinks the control pool.** T1-B's own risk is
    the inverse of the problem it solves; the fallback-level distribution must
    be published as evidence.

---

## Analytical lineage recommendation

Proposed **`free-dna-*-7.0.0`** — a major generation, because provider,
eligible population and the meaning of role all change at once. Inspected
`versions.py::VERSION_SURFACES` before naming; the repository's convention is
per-surface dispositions, not a monolithic bump. Full table in
`04-corpus-lineage-roadmap.md` §2.

Across all 18 surfaces: **11 `changed`, 1 `new` (`stratz-history-schema-1.0.0`),
1 `compatible` (`interactions`, additive minor), and 5 `unchanged`** —
`claims`, `statistics`, `expression`, `story`, `deep_diagnostics`. That
unchanged list is the important one: **the statistical machinery and the
nine-beat story architecture survive the provider change intact.** What changes
is the data, the baselines, and the vocabulary of role.

V6.1's immutable identities — source SHA `7df38e6d…` and artifact digest
`8e9e22a9…` — are not rewritten, re-attributed or regenerated by anything here.

---

## Research corpus plan

**No corpus was collected and none is authorized.** Design in
`04-corpus-lineage-roadmap.md` §1.

Two corpora, forced apart by the cost cliff: **Corpus H** (1,000 players,
history tier, **~6,000 requests** — 0.6 days of the 10,000/day ceiling) and
**Corpus P** (100 players, parsed tier, **~29,300 requests** — ~3 days at 100%
budget, ~6 at a sane 50%). The 10,000/day ceiling is **quoted from the brief,
not measured by this research**; the ratio between the two tiers is measured,
the absolute days are not. Build H first; build P only when a Tier 2 candidate
is actually being promoted.

Stratify on role mix above all — a core-heavy corpus produces core-shaped
baselines and re-introduces the exact bias T1-A exists to remove. Rank is
recorded at sampling time for stratification only and **discarded before
analysis**; `rank_or_mmr_used: False` is untouched.

The sampling frame is the weakest part of the design and is stated as such:
STRATZ exposes no verified random-player endpoint, and every available frame is
biased. The recommendation is to seed from consenting users and **declare the
frame as a limitation on every baseline artifact** rather than claim
representativeness.

A **fresh** sealed holdout is required. The existing V6.1 holdout under
`.local/calibration/v61/release-recovery-7df38e6/sealed-holdout/` is
OpenDota-derived, belongs to a different provider and a different eligible
population, and must not be reused as a tuning set or as validation for this
work.

---

## Implementation roadmap

Full version in `04-corpus-lineage-roadmap.md` §3.

**Phase 0 — unblock.** [OWNER] STRATZ licensing. [OWNER] automated API access —
manual GraphiQL does not scale past this research. Run Pack B and Pack C; **C1
decides whether Tier 2 exists at all.**

**Phase 1 — history tier.** History adapter (breaks the `request_count == 1`
canonical contract → new schema surface). Role normalization from
`position`/`role`, **deleting the lane→role-word path rather than extending it**.
Corpus H. Baseline derivation + fallback-level audit. Element re-derivation
(highest regression risk). T1-B, then T1-A. [OWNER] ship/hold. Then T1-C and
T1-D if T1-A validated.

**Phase 2 — parsed tier**, only if C1 is favourable: parsed acquisition with a
measured complexity budget, Corpus P, T2-A, T2-B, [OWNER] ship/hold.

**Prerequisites that are not STRATZ work:** confirm which p-value path
production runs (the six hard-wired `p = 1.0` branches are on the fixture path
only), and the `DEFAULT_THRESHOLDS` key-miss. Phase 1's T1-B is pointless if
`post_loss_response` cannot fire. Establish before, not during.

Also open: `finishing` and `consistency` belong to no finding family.

---

## Blocked / unresolved

Full list with the resolving query in `05-blocked-and-queries.md`.

**Tier 0 — decides whether the parsed tier exists:** C1 parsed batching against
the 310,000 complexity ceiling; C2 `matchesGroupBy` aggregates.
**Tier 1 — blocks Tier 1 implementation:** B1 sub-type shapes (~14 stats fields
and 4 match fields are currently *un-queryable*, not merely unfetched); B3 the
`stats.level` length rule; B4 parsed coverage over a full year; the
`LeaverStatusEnum` → V6.1 integer mapping, which changes the eligible
population and therefore every Element value.
**Tier 2:** the lane→side mapping (needs a labelled corpus, not a query);
`laneReport` richness.
**Tier 3 — semantics unestablished:** `invisibleSeconds`, `partyId` nulls,
`isStats`, `variant`, `wards.type` and grid, `RuneTypeEnum`, negative
`firstBloodTime`, `roshanEvents` reliability, `abilities(gameVerionId:)`.

---

## Verification pass

These documents were put through an adversarial fact-check that re-derived every
quantitative claim from the payloads and re-read every code claim from source.
It found **34 defects, nine of them fabrications**, all of which are corrected
above. Recording what was wrong, because the same mistakes are the ones a reader
should probe first:

- **The eligible population was computed with the wrong rule.** The first pass
  excluded `leaverStatus: DISCONNECTED`; V6.1 excludes only
  `_MATERIAL_ABANDON_STATUSES = {2,3,4,5}`. This silently resolved, in one
  direction, the very `LeaverStatusEnum` question the document declares BLOCKED.
  Now both readings are computed and the dependency is stated wherever a derived
  figure appears (49/293 vs 45/269).
- **Four invented "observed" values**: a ward coordinate range of 64–192 (real:
  x ∈ [70,170], y ∈ [68,172]); "your five most-played heroes appear in both"
  roles (real: 2 of 18); "the top three heroes appear across roles" (real: the
  top hero is core-only); "both players reached level 30" (A3 never returned the
  scalar). The last three were in *example copy* and *candidate justifications* —
  the places where a fabrication is most likely to survive review because it
  reads as illustration.
- **"Six branches can never fire"** was wrong: they are dead on the
  fixture/synthetic path; the production path computes all of them. It had been
  carried into the roadmap as a blocking prerequisite.
- **"No support word in the vocabulary"** overstated it — `roamer` exists. The
  finding survives for a different and narrower reason (STRATZ `MatchLaneType`
  has no roaming value, and `roamer` cannot split `POSITION_4` from
  `POSITION_5`), which is now what the document says.
- **Two tallies did not sum**: the semantic-outcome dispositions summed to 31 of
  28, and the version-surface dispositions to 20 of 18.
- **The playback cost was presented as the cost** when it is a floor from 7 of
  25 fields.
- **The 10,000/day ceiling is the brief's number, not a measurement** — nothing
  in the captured payloads records a rate limit. Now attributed everywhere it
  is used.
- **"52 raw → 12 hypotheses"** dropped 16 candidates silently. The remainder is
  now itemised and the live-hypothesis count corrected to 20.
- **The baseline-cell table** rested on three unstated constants and checked
  only `match_count`, never `distinct_players >= 50` — the condition the
  surrounding prose called the binding one. Both are now computed, with the
  uniform-allocation assumption stated.
- Also corrected: `win_streak` does exist in `relationships.py`; `consistency`
  is a second untested public Element alongside `finishing`; `campStack` cannot
  be classified from these payloads; two more rune values were observed;
  `FORBIDDEN_ANALYTICAL_FIELDS` does not literally contain the STRATZ rank
  field names; `seasonRank` is not a field in any introspected type.

`analyze.py` was rewritten so that every number above is reproducible, including
the two eligibility readings side by side.

## Production safety

| | |
|---|---|
| production code changed | **NO** |
| deployment | **NO** |
| configuration changed | **NO** |
| database touched | **NO** |
| analytical artifacts changed or regenerated | **NO** |
| V6.1 source SHA or artifact digest altered | **NO** |
| sealed holdout read, used or mutated | **NO** |
| OpenDota calls made | **NO** |
| corpus collected | **NO** |
| thresholds, estimators, significance or publication logic altered | **NO** |
| analytical production implementation | **NO** |

Files created by this research, all research-only:

- `research/stratz-enrichment/00-…` through `05-…` (this set)
- `.local/stratz-probe/enrichment/pack-{a,b,c}.graphql` (gitignored)
- `.local/stratz-probe/enrichment/analyze.py` (gitignored, read-only analysis)
- `.local/stratz-probe/enrichment/A{1,1b,2,3,4,5,6,7}.json` — payloads captured
  manually by the owner and stored in gitignored `.local/` under the owner's
  explicit instruction to save sanitized fixtures

`git status --porcelain` also lists `docs/prompts/stratz/` and `docs/evidence/`
as untracked. **Those predate this research and were not created by it**; they
are the originating briefs and prior work.

STRATZ requests attributable to this research: **8 manual GraphiQL operations**
executed by the owner — `A1` (rejected on complexity), `A1b`, `A2`, `A3`, `A4`,
`A5`, `A6`, `A7`; 7 succeeded. Plus **2 automated reachability checks** by this
session (one from the cloud sandbox, one from the device shell), both HTTP 403.
No other automated requests were made or attempted. The 8 HTTP 403 requests
recorded in `.local/stratz-probe/runs/193875165-20260827T011356Z/` predate this
research.
