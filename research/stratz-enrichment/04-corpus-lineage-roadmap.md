# Research corpus protocol, analytical lineage, implementation roadmap

> **Superseding operational note — 2026-09-01:** **AUTOMATED STRATZ ACCESS
> BLOCKER = RESOLVED.** The access blocker described in this historical
> roadmap reflects 2026-08-27. The recovered specimens are not a population
> corpus, and this audit remains strictly offline with zero provider requests.

**NO CORPUS WAS COLLECTED.** This is a design. Two independent blockers stand
in front of collection and both are owner decisions, not engineering ones:

1. **Licensing.** STRATZ storage, caching, attribution and commercial terms are
   `UNKNOWN — requires owner/STRATZ confirmation`. Every artifact below assumes
   permission that does not currently exist.
2. **Access.** `api.stratz.com` returns HTTP 403 from every automated
   environment available. Manual GraphiQL paste is the only working path, and
   manual paste does not scale to a corpus at any size. **An automated-access
   agreement is a hard prerequisite** — this is not a "nice to have" and it is
   not solvable by better tooling on our side.

---

## 1. Corpus design

### 1.1 Two corpora, not one

The §0 cost cliff in `03-candidate-catalog.md` forces a split.

| | **Corpus H** (history tier) | **Corpus P** (parsed tier) |
|---|---|---|
| purpose | baselines, role calibration, Tier 1 | Tier 2 feature research |
| unit | one player-year of history | one player-year of per-match parsed |
| requests/player | ~6 | ~299 |
| target size | 1,000 players | 100 players (subset of H) |
| total requests | **~6,000** | **~29,300** |
| against 10,000/day¹ | 0.6 days | ~3 days at 100% budget; ~6 days at a sane 50% |
| gated on | licensing + automated access | the above **plus** C1 batching |

¹ The 10,000/day ceiling is quoted from the brief, **not measured by this
research** — no payload or response header in `.local/stratz-probe/` records a
rate limit. §1.4 lists capturing observed rate-limit headers for exactly this
reason.

Build H first. Build P only if a Tier 2 candidate is actually being promoted —
collecting P speculatively spends three to six days of budget on hypotheses
that Tier 1 validation may make unnecessary.

### 1.2 Cohort selection and sampling frame

The sampling frame is the hardest unsolved problem here and it deserves to be
stated as a risk rather than papered over. STRATZ has no random-player endpoint
that this research has verified. Every obvious frame is biased:

- leaderboards → high-skill bias
- "recently active" → activity bias
- our own users → our own acquisition bias
- friend graphs from seed accounts → snowball/homophily bias

**Recommendation:** seed from our own consenting user base and declare the
resulting frame explicitly as a limitation on every baseline artifact, rather
than pretending to a random sample. A baseline derived from a biased frame is
usable if the bias is named and stable; a baseline that claims to be
representative and is not, is worse than no baseline.

Stratify on, and record per player:

- **role mix** — the specimen player is 41% support in eligible matches (20/49);
  a core-heavy corpus would produce core-shaped baselines and quietly
  re-introduce the exact bias T1-A exists to remove
- **hero diversity** — Zipfian; over-sample rare-hero players deliberately
- **match depth** — ≥60 eligible matches (`NORMAL_REPORT_MATCHES`) for a player
  to be usable for calibration; ≥30 (`MIN_ELIGIBLE_MATCHES`) to be usable at all
- **patch coverage** — the specimen spans **one** `gameVersionId` in 61 days;
  a 365-day window should span roughly 6
- **rank** — as a **sampling** consideration only, so that baselines are not
  drawn from one skill stratum. Rank must be recorded at sampling time and
  then **discarded before analysis**. It must never enter a feature, a
  baseline key, or a model. `rank_or_mmr_used: False` is an audited assertion
  and this research does not touch it.

### 1.3 Privacy and eligibility

- Record `steamAccount { isAnonymous isStratzPublic }` per player at collection
  time; exclude anonymous accounts entirely.
- Persist a salted hash of `steamAccountId`, never the raw id, in any artifact
  that could leave `.local/`.
- Never persist `chatEvents`, `allTalks`, or `chatWheels`. They are
  player-authored text about identifiable people and nothing in this catalog
  needs them.
- Re-check `isStratzPublic` before any re-collection; a player who goes private
  must be dropped, not retained under the old snapshot.

### 1.4 Reproducibility artifacts

Per collection run:

- exact GraphQL operation text, verbatim, plus its sha256
- **schema snapshot** and a drift check against the previous run — note that a
  *full* introspection snapshot is impossible under the 310,000 complexity
  ceiling, so the snapshot is the narrow `A1b`/`B1` slice and drift detection is
  only as good as that slice's coverage. Record that limitation in the manifest.
- sha256 of every raw response, and byte size
- raw-response digest **and** normalized-projection digest
- normalizer version
- collection timestamp, request ledger, and observed rate-limit headers
- the resolved complexity of each operation, if STRATZ exposes it

### 1.5 Splitting

Deterministic, by salted-hash of `steamAccountId`, into
**development 60% / calibration 20% / test 20%**, with a **fresh sealed
holdout** carved from test before any modelling begins.

The existing V6.1 sealed holdout under
`.local/calibration/v61/release-recovery-7df38e6/sealed-holdout/` is OpenDota-derived
and belongs to a different provider, a different eligible population and a
different feature set. **It must not be reused as a tuning set and it must not
be used to validate STRATZ-derived work.** Existing OpenDota-derived corpora
remain OpenDota-derived and are not re-attributed.

### 1.6 Baseline cell feasibility — the number that sizes Corpus H

`BaselineCell.eligible` requires `match_count >= 200` **and**
`distinct_players >= 50`. Both conditions are computed below.

**Stated assumptions** (none of these is measured; all are inputs to the
arithmetic): 293 eligible matches per player-year; **126** heroes; **8**
hero-function labels in the editorial taxonomy; **6** distinct `gameVersionId`
values in a 365-day window (the specimen spans **1** in 61 days); and a lane
dimension of **5** if keyed on `position` or **3** if keyed on `role`. Matches
are allocated to cells **uniformly**, and distinct players per cell is estimated
as `N · (1 − e^(−293/cells))`.

Keyed on `position` (lane = 5), 6 patches:

| baseline level | cells | 1,000p matches/cell | 1,000p distinct | 5,000p matches/cell | 5,000p distinct |
|---|---|---|---|---|---|
| `patch+hero+lane` | 3,780 | **78 — fails** | 75 | 388 | 373 |
| `patch+hero` | 756 | 388 | 321 | 1,938 | 1,606 |
| `patch+hero_function+lane` | 240 | 1,221 | 705 | 6,104 | 3,525 |
| `patch+lane` | 30 | 9,767 | 1,000 | 48,833 | 5,000 |
| `patch` | 6 | 48,833 | 1,000 | 244,167 | 5,000 |

Keyed on `role` (lane = 3), `patch+hero+lane` has 2,268 cells and still fails at
1,000 players (129/cell) while passing at 5,000 (646/cell).

**Uniform allocation is optimistic.** Hero play is Zipfian, so the median cell
sits well below the mean and rare hero × lane combinations fail long before the
average does. The `distinct_players >= 50` condition binds hardest exactly
there. Treat every "pass" above as an upper bound.

The honest conclusion: a 1,000-player corpus supports
`patch+hero_function+lane`, `patch+hero`, `patch+lane` and `patch`.
**The top level of `BASELINE_HIERARCHY` — `patch+hero+lane` — is not reachable
at 1,000 players even under the optimistic uniform assumption, and is reachable
at 5,000 only on paper.** That is fine — it is still a large improvement over today, where
almost every match resolves at `overall` — but the plan must not promise
`patch+hero+lane` resolution and then quietly deliver `patch+lane`. The
fallback-level distribution must be published as evidence on every report, which
`AdjustedMetricSeries.fallback_level_counts` already supports.

---

## 2. Analytical lineage

Everything recommended here is outside V6.1. The immutable identities —
analytical source SHA `7df38e6d234ae9c4ee425490bc40b8cc92685f85` and frozen
artifact digest
`8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0` — are not
rewritten, re-attributed or regenerated by anything in this document.

Inspected `player_analysis_v61/versions.py::VERSION_SURFACES` before proposing a
name. The repository's convention is a **dotted generation with per-surface
dispositions**, not a monolithic bump. Following it, and *not* assuming "V6.2":

**Proposed: `free-dna-*-7.0.0`** — a major generation, because the data provider,
the eligible population and the meaning of role all change at once. A minor
bump would understate it.

### Surface dispositions

| surface | current | proposed | disposition | why |
|---|---|---|---|---|
| `summary_history` | `summary-history-schema-3.0.0` | `stratz-history-schema-1.0.0` | **new** | Different provider, different projection, and the one-physical-request contract is broken (~6 pages) |
| `context_baseline` | `context-baseline-3.0.0` | `context-baseline-4.0.0` | **changed** | Rebuilt from a STRATZ corpus; patch and lane become reachable for the first time |
| `elements` | `free-elements-6.1.0` | `free-elements-7.0.0` | **changed** | Same seven ordered keys; `toolkit` re-based on observed role; values move because baselines move |
| `findings` | `free-findings-6.1.0` | `free-findings-7.0.0` | **changed** | Same five roots; new branches under `pool_shape` and `transfer` |
| `semantic_outcomes` | `semantic-outcomes-1.0.0` | `semantic-outcomes-2.0.0` | **changed** | New branches; three job-based outcomes re-based on observed role |
| `supporting_signals` | `supporting-signals-1.0.0` | `supporting-signals-2.0.0` | **changed** | `X13`'s rejection reason is overturned; `M12`'s reason is overturned; the group definitions need real `source_fields` |
| `thresholds` | `metric-thresholds-6.1.0` | `metric-thresholds-7.0.0` | **changed** | Re-derived against the new baseline distribution |
| `claims` | `claim-contract-2.0.0` | — | **unchanged** | Observation / interpretation / alternatives / limits structure is provider-agnostic |
| `statistics` | `stats-cluster-bootstrap-2.0.0` | — | **unchanged** | Clustered session bootstrap is unaffected by the provider |
| `expression` | `summary-expression-multisignal-2.0.0` | — | **unchanged** | |
| `story` | `free-story-6.1.0` | — | **unchanged** | Same nine beats |
| `copy` | `free-dna-semantic-copy-6.1.0` | `...-7.0.0` | **changed** | New branches need copy; role words enter the vocabulary |
| `recommendations` | `free-dna-recommendations-6.1.0` | `...-7.0.0` | **changed** | `verify_transfer` splits with `clean_transfer` |
| `interactions` | `report-interactions-1.1.0` | `1.2.0` | **compatible** | Additive kinds; old sessions stay readable |
| `share_renderer` | `share-svg-6.1.0` | `...-7.0.0` | **changed** | New semantic cards gated separately |
| `deep_diagnostics` | `deep-diagnostics-2.1.0` | — | **unchanged** | |
| `report` | `free-dna-report-6.1.0` | `free-dna-report-7.0.0` | **changed** | |
| `model` | `free-dna-model-6.1.0` | `free-dna-model-7.0.0` | **changed** | New generation selector only |

Dispositions across all 18 surfaces: **11 `changed`, 1 `new`
(`stratz-history-schema-1.0.0`), 1 `compatible` (`interactions`), 5
`unchanged`.**

**The five `unchanged` surfaces are `claims`, `statistics`, `expression`,
`story` and `deep_diagnostics`.** That list matters as much as the changed one: **the statistical
machinery and the story architecture survive the provider change intact.** What
changes is the data, the baselines, and the vocabulary of role. Nothing about
the way this product reasons needs to be rebuilt.

### Validation path

```
STRATZ research  (this document — PARTIAL; four Tier-1 BLOCKED items remain)
  -> owner decision: licensing + automated access          [BLOCKING]
  -> Corpus H collection (1,000 players, ~6,000 requests)
  -> baseline derivation + fallback-level audit
  -> role calibration (role_effective population distribution)
  -> feature design (T1-A, T1-B)
  -> reproducibility / synthetic checks
  -> FRESH sealed holdout  (never the V6.1 holdout)
  -> product and content review + Dota-player manual review
  -> staging behind FREE_DNA_V7_ENABLED (default false)
  -> owner-authorized production
```

---

## 3. Implementation roadmap

Dependency-ordered. Owner decision points marked **[OWNER]**.

### Phase 0 — unblock (nothing else can start)

1. **[OWNER]** STRATZ licensing: storage, caching, attribution, commercial use.
2. **[OWNER]** Automated API access. Manual GraphiQL does not scale past this
   research. Without it, Phase 2 is impossible regardless of the licensing answer.
3. Run Pack B (`B1`, `B3`, `B4`) and Pack C `C1` — see
   `05-blocked-and-queries.md`. **C1 decides whether Tier 2 exists at all.**

### Phase 1 — history tier (no per-match parsed dependency)

4. STRATZ history acquisition adapter. Breaks V6.1's
   `request_count == 1` canonical contract — **new schema surface, not a patch
   to `summary-history-schema-3.0.0`.**
5. Role normalization from `position`/`role`. **Delete the lane→role-word
   mapping path entirely rather than extending it** — see the §0.1 trap in
   `02-finding-reassessment.md`. Introduce a support vocabulary.
6. Corpus H collection (~6,000 requests).
7. Baseline derivation + the fallback-level audit from §1.6.
8. Element re-derivation on new baselines. **Expect every Element value to
   move.** This is the point of highest regression risk in the whole plan.
9. T1-B (post-loss control upgrade). Ship the backstage improvement before any
   new onstage claim — it is free, it costs no multiplicity, and its backtest
   tells the owner whether currently-published post-loss findings were confounded.
10. T1-A (Role Shape). Calibration, fresh holdout, Dota-player review.
11. **[OWNER]** Ship/hold decision on the history tier.
12. T1-C and T1-D, gated on T1-A validating.

### Phase 2 — parsed tier (only if C1 is favourable)

13. Per-match parsed acquisition with a measured complexity budget.
14. Corpus P collection (~29,300 requests).
15. T2-A (Kill Participation). Replaces `involvement` — touches four semantic
    outcomes and the `combat_expression` family.
16. T2-B (Lane Outcome), including the lane→side mapping test.
17. **[OWNER]** Ship/hold on the parsed tier.

### Prerequisites that are not STRATZ work

18. **Confirm which p-value path production actually runs.** The six
    hard-wired `p = 1.0` branches live in `v61_branch_p_values` (the
    fixture/synthetic path); the production path
    `v61_production_family_branch_p_values` computes all of them. Separately,
    the `DEFAULT_THRESHOLDS` key-miss makes `post_loss_response` and
    `session_drift` unpublishable without an injected calibrated artifact.
    **Both are pre-existing and independent of this research.** But Phase 1
    step 9 is pointless if `post_loss_response` cannot fire, so establish this
    before starting it, not during.
19. `finishing` **and** `consistency` are public Elements belonging to no
    finding family's `required` tuple — measured and never tested. Decide
    whether that is intentional.
