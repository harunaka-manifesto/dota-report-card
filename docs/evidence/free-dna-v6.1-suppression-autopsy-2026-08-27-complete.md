# V6.1 Suppression Autopsy

## Status

**PASS — diagnostic complete.** The offline run evaluated all 791 tuning-eligible
profiles with zero collection calls and zero errors. This report does not
authorize V6.1 release. The current implementation has reproducible inference
and publication-path defects that must be resolved and revalidated first.

## Zero-call verification

- OpenDota collection calls: **0**.
- Steam calls: **0**.
- Holdout reruns: **0**.
- New data collected: **0**.

The autopsy used a process-level HTTP guard that hard-fails an attempted HTTPX
request. No provider client was instantiated. The replacement holdout was not
loaded by the trace run and was not used for any counterfactual.

## Data used

| dataset | profiles | history depth | classification | allowed use |
|---|---:|---|---|---|
| Replacement canonical corpus, schema `v61-calibration-corpus-2.1.0`, SHA-256 `5b80bd…` | 1,130 | per-profile 365 days; 455,971 rows | A — tuning-eligible | The 791-profile train partition was used for local reconstruction and exploratory counterfactuals; the 339-profile partition was excluded. |
| Frozen replacement train partition, split manifest SHA-256 `2aa3b4…`, train digest `2d961e…` | 791 | per-profile 365 days; 303,362 train rows | A — tuning-eligible | Offline runtime reproduction only; no parameter or artifact was changed. |
| Frozen replacement holdout output, corpus SHA `5b80bd…`, split SHA `2aa3b4…` | 339 | per-profile 365 days | B — descriptive-only | Not loaded or rerun. Existing aggregate says 337 reports had zero findings and 2 had Transfer; `holdout_passed=false`. It cannot select thresholds, windows, or minimums. |
| Historical V6.1 canonical corpora, schema `2.0.0`, including 424,066-row and 424,591-row snapshots | 1,130 | 365-day snapshots | C — historical-only | Provenance comparison only; not used for tuning. |
| Legacy V6 compact/windowed corpus and its prior holdout outputs | 1,130-class corpus; 339-profile old output | 365-day snapshots | C — historical-only | Historical comparison only; not used for tuning. |
| Tracked frozen V6.1 runtime artifact set, package digest `8e9e22…` | n/a | n/a | B — descriptive-only release input | Loaded exactly as bound by the manifest; no artifact, threshold, or calibration file was edited. |

No input used in the run was classified D (unknown/blocked). Any unbound
external source was excluded. The complete digests are recorded in the local
`provenance.json` output; abbreviated digests above are only for readability.
Exact binding: corpus `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216`,
split manifest `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231`,
train profile digest `2d961edcde679a529751c78b9129cf6d8cf0e56d32d17a226a12dd24a0c09461`,
and analytical source `7df38e6d234ae9c4ee425490bc40b8cc92685f85`.

## What V6.1 actually sees

The production contract requests summary history with `date=365` and provider
`limit=10,000`, in one physical summary-history request. V6.1 has no additional
`history_limit` cap (`None`), and it does not request match details or parses.
The current corpus maximum is 2,617 matches per profile, below the provider
limit, so provider truncation is not the observed bottleneck. All 791 train
histories were complete; raw, normalized, and eligible counts were identical,
with zero deduplicated rows.

The corpus spans 2025-08-25 through 2026-08-25. Across the train partition,
eligible matches have a median of 278 (P10 56, P25 110.5, P75 531.5, P90 842,
maximum 2,617) and sessions have a median of 108 (P10 27, P90 304, maximum
722). Every family starts from the same eligible 365-day match history, then
uses a different denominator:

| family | effective unit used by the implementation | median usable opportunities | median family units/sessions | support diagnostic pass |
|---|---|---:|---:|---:|
| Pool Shape | eligible matches | 278 | 108 | 780/791 (98.6%) |
| Transfer | reliable-stretch contrast matches | 72 | 49 | 565/791 (71.4%) |
| Post-Loss Response | same-session chronological transitions | 154 | 50 | 687/791 (86.9%) |
| Combat Expression | min(involvement matches, death-exposure matches) | 278 | 108 | 780/791 (98.6%) |
| Session Drift | covered position matches and completed sessions | 117 | 108 | 707/791 (89.4%) |

The diagnostic support contract is 30 opportunities and 12 family units. It is
not a separate V6.1 publication boolean in the current assembly. That
distinction matters: support failures are evidence of opportunity scarcity, but
they are not consistently enforced before publication.

## How sparse are reports?

The current trace does **not** reproduce the anecdotal Pool-only shape. It
produces either no published family or a Transfer-only report:

- median findings/report: **0**;
- mean findings/report: **0.0063**;
- P10/P25/P75/P90: **0 / 0 / 0 / 0**;
- 0 findings: **786/791 (99.37%)**;
- 1 finding: **5/791 (0.63%)**;
- 2 findings: **0%**;
- 3 findings: **0%**;
- 4+ findings: **0%**;
- Pool-only: **0%**;
- Pool plus exactly one other family: **0%**;
- Transfer: **5/791 (0.63%)**;
- Post-Loss, Combat, Session, and all five families: **0%**.

By available-history size:

| eligible matches | profiles | any qualified family | published Transfer | published Post-Loss | published Session |
|---|---:|---:|---:|---:|---:|
| 30–59 | 85 | 7 (8.2%) | 1 (1.18%) | 0 | 0 |
| 60–119 | 136 | 11 (8.1%) | 0 | 0 | 0 |
| 120–249 | 139 | 10 (7.2%) | 0 | 0 | 0 |
| 250–499 | 209 | 25 (12.0%) | 3 (1.44%) | 0 | 0 |
| 500+ | 222 | 17 (7.7%) | 1 (0.45%) | 0 | 0 |

There is no monotonic coverage curve inside the current 365-day corpus.

## Suppression by family

| family | publish % | dominant first blocker | % blocked there | median opportunities / family units | narrow q near-miss % |
|---|---:|---|---:|---:|---:|
| Pool Shape | 0% | Family q gate | 98.6% (780/791) | 278 / 108 | 0% |
| Transfer | 0.63% | Family q gate after support triage | 65.0% (514/791) | 72 / 49 | 5.4% of q failures (39/721) |
| Post-Loss Response | 0% | Family q gate | 86.9% (687/791) | 154 / 50 | 0% |
| Combat Expression | 0% | Family q gate | 98.6% (780/791) | 278 / 108 | 0% |
| Session Drift | 0% | Family q gate | 89.4% (707/791) | 117 / 108 | 0% |

The “first blocker” column uses a diagnostic ordering of support, family q,
branch q, and inherited V6 publication. It is exclusive. All-blocking counts
are intentionally different because multiple flags can be false: 436/3,955
family slots (11.0%) fail the 30/12 support diagnostic; 3,885/3,955 (98.2%)
fail the family q gate; 3,885 also show a false runtime branch flag because a
failed parent family forces branch q to 1; and 3,950/3,955 fail the inherited
V6 publication prerequisite. Those overlapping counts must not be added.

## The funnel

Counts are out of 791 profiles per family. “Support” and “semantic evidence”
are diagnostic availability checks where noted; they are not silently promoted
to runtime gates.

| family | eligible | support 30/12 | candidate computed | family q passed | branch q passed | inherited V6 published | final published | surfaced |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pool Shape | 791 | 780 | 791 | 0 | 0 | 0 | 0 | 0 |
| Transfer | 791 | 565 | 791 | 70 | 70 | 5 | 5 | 5 |
| Post-Loss Response | 791 | 687 | 791 | 0 | 0 | 0 | 0 | 0 |
| Combat Expression | 791 | 780 | 791 | 0 | 0 | 0 | 0 | 0 |
| Session Drift | 791 | 707 | 791 | 0 | 0 | 0 | 0 | 0 |

The actual assembly computes the V6 base finding, computes V6.1 family and
branch q-values, and then sets eligibility from the inherited V6
`finding.published` flag plus branch qualification, public-candidate status,
the three-finding cap, and the Pool completeness rule. Stability, confounder,
effect/equivalence, and semantic evidence availability are recorded but are
not separate publication booleans in this path.

## Why Pool survives

In this exact current replacement-corpus trace, Pool does **not** survive to a
published finding. It survives the data-support stage: 780/791 profiles meet
the 30-opportunity/12-session diagnostic, and its median denominator is the
full 278 eligible matches. But every Pool family q is above the release gate;
the minimum family q is about 0.490 and the minimum raw p is about 0.460.
Thus Pool is not being lost because it lacks raw matches or valid conditional
opportunities in this run. If another report shows Pool, it is from a different
payload, fixture, source revision, or publication path; this corpus does not
reproduce it.

## Why Transfer disappears

Transfer is the only family that reaches the V6.1 family gate: 70/791 profiles
(8.85%) qualify, and all 70 also pass the current runtime branch flag. Its
conditional denominator is much smaller than the raw history: median 72
reliable-stretch opportunities and 49 family sessions. 226/791 (28.6%) fail
the 30/12 support diagnostic; 59 have 20–29 opportunities and 60 have 8–11
reliable-stretch sessions, so a meaningful part of the scarcity is real
opportunity loss rather than raw history loss.

The main runtime loss is a separate coupling: only 5 of the 70 family-qualified
profiles have an inherited V6 Transfer finding with `published=true`. The
other 65 are suppressed by the V6.1 assembly’s inherited V6 prerequisite. The
five final findings are all `clean_transfer`; one of the five has only 12
opportunities and 11 sessions and lacks complete semantic bootstrap evidence,
which demonstrates that the declared support/evidence contract is not enforced
by final publication.

Transfer q-values are not uniformly near the boundary: 70 profiles are at or
below q=.05, 21 are in (.05,.07], 18 are in (.07,.10], and 682 are above .10.
The 39 narrow cases are worth later investigation after the inferential bug is
fixed, but threshold relaxation is not the current release-path fix.

## Why Post-Loss disappears

Post-Loss uses same-session chronological result-state transitions, not raw
matches. The median profile has 154 usable transitions and 50 sessions in the
largest state. 104/791 (13.1%) fail the 30/12 support diagnostic; 87 have
fewer than 30 transitions, 92 have fewer than 12 state sessions, and 75 fail
both. Every Post-Loss family q is above .10 (minimum about .490; minimum raw p
about .461), so there are no q=.05–.10 near-misses in this corpus.

The semantic bootstrap projection also maps Post-Loss to `finishing` draws
instead of the declared result-response transition evidence. That is a
confirmed implementation mismatch, not evidence that Post-Loss has no stable
behavior.

## Why Session disappears

Session Drift uses covered G1–G5+ position curves and completed sessions. Its
median denominator is 117 position matches and 108 sessions. 84/791 (10.6%)
fail the support diagnostic, all because usable position opportunities are
below 30; 12 also have fewer than 12 sessions. No Session family q passes;
the raw p minimum is .25 and the q P10 is about .502, so the failures are not
narrow q misses.

The semantic bootstrap projection maps Session Drift to `consistency` draws,
not the declared session-curve evidence. The registry and feature graph
declare direct session-position evidence, making this a second confirmed
semantic source mismatch.

## Why Combat Expression disappears

Combat has abundant raw support: its median usable denominator is 278 matches
and 108 family sessions, with only 11/791 (1.4%) failing the 30/12 diagnostic
(the failure is session-unit scarcity, not match scarcity). Nevertheless, no
family q passes; the minimum family q is about .490 and the minimum raw p is
about .378. There are no narrow q misses. Combat is therefore not primarily a
data-volume or presentation problem in this run.

## Is q=.05 actually the problem?

**NO as the primary diagnosis; PARTLY as a later, narrow Transfer question.**

Across 3,955 family slots, 3,885 fail the family q gate. Of those failures,
3,846 (99.0%) are above q=.10 and only 39 (1.0%) are in (.05,.10]. The
near-boundary cases are all Transfer. Changing the branch threshold alone
produces no additional current-gate findings, and changing the family
threshold above .05 produces no additional final findings because the
inherited V6 publication prerequisite dominates.

This conclusion is provisional in one important way: the current runtime p
construction is not a valid null-centered bootstrap p-value procedure. No q
threshold should be selected from these values until that bug is repaired and
the repaired path is independently validated.

## Threshold sensitivity

These are training-only counterfactuals. The left side is the current inherited
V6 gate; the right side intentionally ignores that gate and is **not a release
candidate**. “Findings/report” is the mean number of candidate/published
family slots per 791-profile report set. Pool-only remains zero in every row.

| family q / branch q | with inherited V6 gate: findings/report | with gate: family coverage | ignoring inherited gate: findings/report | ignoring gate: family coverage |
|---|---:|---|---:|---|
| .01 / .01 | 0.0000 | none | 0.0202 | Transfer 2.02% (16) |
| .025 / .025 | 0.0038 | Transfer 0.38% (3) | 0.0480 | Transfer 4.80% (38) |
| .05 / .05 | 0.0063 | Transfer 0.63% (5) | 0.0885 | Transfer 8.85% (70) |
| .075 / .075 | 0.0063 | Transfer 0.63% (5) | 0.1214 | Transfer 12.14% (96) |
| .10 / .10 | 0.0063 | Transfer 0.63% (5) | 0.1378 | Transfer 13.78% (109) |

At q=.05 without the inherited gate, 70 Transfer candidates appear, but only
51 meet the diagnostic support contract and 46 have complete semantic
bootstrap evidence. At q=.10, 109 candidates appear, but only 77 meet support
and 66 have complete semantic evidence. The extra yield is therefore not a
reliability result. This corpus can estimate yield under the frozen procedure;
it cannot establish the corresponding real-world false-positive rate because
it has no independent truth labels, and the protected holdout cannot be used
to choose the boundary. q=.10 is not “90% confidence.”

## History-window sensitivity

The stored corpus contains no matches beyond the current 365-day collection
window. A valid “current q + more history” experiment therefore cannot be run
without new data, which is prohibited here. The history output records:

| window | result | reason |
|---|---|---|
| >365 days | NOT POSSIBLE | maximum stored depth is 365 days |

The available history-bin curve is not evidence for a wider window: Transfer
publication is 1.18%, 0%, 0%, 1.44%, and 0.45% across the five bins, while all
other families remain at 0%. More history may increase conditional
opportunities, but this corpus cannot measure that effect.

## Threshold vs more history

The only measurable intervention is the training-only q counterfactual above;
it raises Transfer candidate yield only when the inherited V6 gate is ignored.
The more-history arm is unmeasurable because no deeper rows exist. The evidence
supports investigating conditional opportunity coverage after the publication
and inference defects are repaired, but it does not support changing the
production window or API cost now.

## Bugs found

The following are reproducible implementation defects or contract gaps. No fix
was implemented in this diagnostic.

1. **Invalid production p-value construction.**
   `services/api/app/player_analysis_v61/family_statistics.py:19-26` defines
   `observed = abs(mean(samples) - null)` and counts bootstrap draws at least
   as far from the null as that same observed bootstrap mean. A constant sample
   of 2,000 draws at 1.0 returns p=1.0; a constant sample at 0.5 also returns
   p=1.0. The procedure is not a valid null-centered test statistic and can
   suppress stable effects or produce misleading q-values.

2. **Inherited V6 publication coupling.**
   `services/api/app/reports/dna_assembly_v61.py:1256-1261` sets V6.1
   eligibility from `finding.published` and the V6.1 branch flag. In the trace,
   70 Transfer families qualify at the V6.1 family gate but only 5 inherit a
   published V6 finding. This accounts for 65/70 family-qualified Transfer
   paths disappearing before final publication.

3. **Declared support/evidence gates are not enforced at final publication.**
   The semantic registry declares minimum opportunities/sessions, effect or
   equivalence rules, and robustness checks. The assembly loop enforces the
   inherited V6 flag, branch qualification, rollout status, cap, and Pool
   completeness, but does not evaluate separate support, effect, robustness,
   stability, confounder, or semantic-evidence booleans. One of the five final
   Transfer findings has 12 opportunities, 11 sessions, and incomplete
   semantic evidence.

4. **Semantic source mismatch for Post-Loss and Session.**
   `dna_assembly_v61.py:635` projects Post-Loss from `finishing` bootstrap
   values, while the registry declares transition denominators. Line 637
   projects Session Drift from `consistency`, while the declared evidence is
   the session-position curve.

5. **Branch evidence is duplicated.**
   `dna_assembly_v61.py:639-643` copies one family bootstrap sample into every
   public branch. Branch raw p-values are therefore identical within a family,
   so branch q cannot discriminate among semantic outcomes. In the trace,
   branch qualification adds no loss beyond family qualification, and the
   apparent branch selection is not branch-specific evidence.

No family-ID or serialized-report drop was reproduced in the offline assembly
trace; browser E2E was not run for this analytical-only task. The assembly
still has a mixture of V6 and V6.1 responsibilities, so a full repair needs a
contract decision rather than a threshold tweak.

## Presentation losses

There are **5 analytically published family findings and 5 report-level surfaced
family surfaces**: published-but-hidden is 0/5 (0%). The 786 reports with no
final finding cannot be blamed on presentation because no finding reached the
report surface.

The trace reports 0 eligible standalone finding share cards. This is a separate
share contract, not a hidden finding: all five final Transfer findings are
`clean_transfer` recommendations, and the existing share builder intentionally
blocks recommendation-bearing findings from standing alone on a share card.

## Suggestive-signal opportunity

The corpus does show a possible future research pool, but it does not justify
implementing one now:

- q≤.05 yields 70 Transfer family candidates if the inherited V6 gate is
  ignored; 51 meet support and 46 have complete semantic evidence.
- The narrow band (.05,.10] contains 39 additional Transfer candidates; 26
  meet support and 20 have complete semantic evidence.
- q≤.10 would produce 109 diagnostic candidates, but only 77 meet support and
  66 have complete semantic evidence.
- These candidates would reduce zero-finding reports only in a counterfactual
  path, and they would not reduce Pool-only reports because this trace has no
  Pool findings.

A future Suggestive tier must be calibrated independently with cautious copy,
no Signature contribution, no strong share entitlement, explicit denominators,
and a new sealed validation set. It must not be defined as “q<.10” while the
current p construction and semantic evidence mapping remain unresolved.

## Root-cause classification

The percentages below are an operational attribution of the 3,950 suppressed
family slots, not a causal decomposition of true player behavior. The primary
partition gives support triage precedence, then family q, branch q, and the
inherited V6 gate.

| category | exclusive suppressed slots | percentage | interpretation |
|---|---:|---:|---|
| Expected/no-signal proxy | not exclusive | 97.2% of all family slots have q>.10 | A weak-signal proxy only; invalid p construction means this is not proof of no true effect. |
| History-window bottleneck | 0 demonstrable | 0% measured | No deeper stored history exists, so the wider-window hypothesis is untestable here. |
| Opportunity bottleneck | 435 | 11.0% | First diagnostic support failure; 436 flags overlap, including one ultimately published case. |
| Statistical q gate | 3,468 | 87.8% | First blocker after support triage; 3,885 family-q failures exist when overlaps are counted. |
| Stability gate | 0 | not enforced | Stability is recorded as a signal only. |
| Confounder gate | 0 | not enforced | No separate V6.1 selection boolean. |
| Semantic gate | 0 runtime | not enforced | 456/3,955 slots lack complete semantic bootstrap evidence, but it is not a publication gate. |
| Presentation bottleneck | 0 | 0% of published findings | All 5 published family findings surfaced. |
| Implementation bug | global, not slot-exclusive | affects the tested path | Confirmed p-value, inherited-publication, semantic-source, and branch-duplication defects. |
| Other | 0 | 0% | No additional first blocker observed. |

The q and opportunity rows overlap in the all-blocking view. The global bug
row is deliberately not converted into a fake per-profile percentage.

## Recommendation

**Primary recommendation: fix the confirmed inference and publication-contract
defects, then re-establish validity before changing thresholds, minimums, the
history window, or product tiers.**

The immediate evidence-supported sequence is:

1. repair and statistically validate the null/bootstrap p construction;
2. align Post-Loss and Session bootstrap evidence with their declared
   denominators and make branches branch-specific;
3. decide whether V6.1 should own publication or intentionally inherit V6, and
   remove the accidental coupling if V6.1 owns it;
4. enforce support, effect/equivalence, robustness, stability, confounder, and
   evidence-contract gates as actual publication decisions; then
5. recalibrate and run a new sealed validation set under owner authorization.

Until that sequence is complete, keep q=.05, the 365-day request, the minimum
support contract, frozen artifacts, and production flags unchanged. If the
repaired path still shows a large support-complete, evidence-complete body of
Transfer near-misses, threshold or a separately calibrated Suggestive tier can
be considered. That is a later release, not this diagnostic.

## Decision matrix

| option | evidence supporting it | expected useful coverage | statistical / false-positive risk | cost / complexity | recalibration / new sealed set | recommendation |
|---|---|---|---|---|---|---|
| 1. Keep V6.1 as-is | Prevents scope expansion; current final yield is 5 Transfer findings | Remains 0.63% Transfer, 0% other families | High implementation/inference risk remains; FP rate not estimable | No cost; no code | Not sufficient for release | **NO** |
| 2. Relax family q | Only 39 Transfer q failures are narrowly in (.05,.10]; q>.10 dominates | No gain with inherited gate; +39 candidates from .05→.10 only in a diagnostic gate-ignored view | Looser FDR target and invalid current p-values | Low code change, high evidence risk | **Yes / yes** | **NO now** |
| 3. Relax branch q | Branch threshold changes add no current-gate yield; branches share samples | Essentially none on this path | Multiplicity risk without branch-specific evidence | Low code change, branch repair first | **Yes / yes** | **NO now** |
| 4. Change minimum support/effective-N | 436 support flags; Transfer and Post-Loss have real opportunity loss | Could expose more conditional candidates, including 19 q-qualified Transfer support failures | Low-N and unsupported semantic evidence risk | Moderate contract change | **Yes / yes** | **INVESTIGATE later** |
| 5. Analyze more history | Conditional denominators are smaller than raw history; wider window is not measurable here | Unknown; may increase opportunities | Selection/time drift and cost must be validated | API/storage cost potentially material | **Yes / yes** | **INVESTIGATE later** |
| 6. Add Suggestive tier | 39 q-near Transfer cases; 20 are support/evidence complete | Could add cautious Transfer context, not Pool coverage | Users may read suggestive as fact; no calibrated FP rate | Moderate product and contract work | **Yes / yes** | **NO now** |
| 7. Fix specific bugs | Four reproducible defects/gaps explain q validity, 65 Transfer losses, and non-branch-specific evidence | Unknown until repaired; may recover valid rather than merely more findings | Required step to make FP/FDR assessment meaningful | Moderate engineering; no new API call | **Yes / yes** | **YES — primary** |
| 8. Presentation-only change | 5/5 published findings already surfaced; hidden loss is 0 | No analytical coverage increase | No statistical benefit; could misrepresent unsupported findings | Low UI cost | No analytical recalibration, but does not address root cause | **NO** |

## What evidence would change this recommendation?

The conclusion would change if a repaired, branch-specific, support-enforced
runtime path showed that a substantial fraction of support-complete and
evidence-complete failures remained narrowly outside q=.05—specifically, if at
least 25% of such failures were in (.05,.10]—and a newly sealed validation set
showed acceptable FDR/precision at the proposed boundary. That would support a
targeted q investigation rather than a blanket relaxation.

The history recommendation would change if a separately stored deeper corpus
showed a materially larger, stable Transfer/Post-Loss/Session opportunity pool
(for example, at least 2× the current support-complete coverage) without
degrading stability or validation performance. A published-but-hidden count
above zero would change the presentation conclusion. None of those conditions
can be established from the consumed holdout or this 365-day corpus.

## What must NOT be changed yet

Do not change q thresholds, branch correction, minimum support/effective-N
rules, the 365-day production window, model version, source binding, frozen
artifacts, semantic registry, qualification logic, production flags, database
state, or deployment. Do not add Suggestive findings. Do not rerun or tune
against the replacement holdout. Do not make OpenDota/Steam calls.

## Files created

Tracked diagnostic/report files:

- `scripts/v61_suppression_autopsy.py`
- `docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27.md`

Owner-only local output directory for the detached run:
`.local/diagnostics/v61-suppression-autopsy-2026-08-27/`
The review copy in the shared workspace is
`.local/diagnostics/v61-suppression-autopsy-complete-2026-08-27/`.

- `profile_family_trace.csv` and `profile-family-trace.jsonl`
- `suppression_reasons.csv`
- `family_funnel.csv`
- `publication_coverage.csv`
- `opportunity_counts.csv`
- `q_threshold_sensitivity.csv` and `threshold-sensitivity.json`
- `history_window_sensitivity.csv`
- `presentation_dropoff.csv`
- `aggregate_summary.json` and `summary.json`
- `provenance.json`

Profile-level files are ignored, pseudonymous, and mode `0600`; no raw account,
match, session, Steam, or report identifiers are present.

## Integrity verification

- analytical source unchanged: `7df38e6d234ae9c4ee425490bc40b8cc92685f85`.
- artifact package digest unchanged: `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0`.
- production-beta authorization checksum unchanged: `9ddde890c25a47fcabf7a5e51f22ba3a3007f79dd5e5f9c52845a2bfe4e69b2a`.
- holdout rerun: **no**.
- zero OpenDota calls: **confirmed**.
- zero Steam calls: **confirmed**.
- new external data: **none**.
- deployment: **none**.
