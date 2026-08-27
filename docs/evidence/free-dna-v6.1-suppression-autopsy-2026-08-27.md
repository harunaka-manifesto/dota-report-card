# Free DNA V6.1 Suppression Autopsy — 2026-08-27

Status: **PARTIAL** (decisive on mechanism and on the sealed-holdout ground truth; the precise per-family q-threshold sensitivity curve is BLOCKED_COMPUTE, not BLOCKED_PROVENANCE — see "What remains blocked").

Zero-new-data. No OpenDota/Steam calls. No holdout rerun. No thresholds, minimum-support rules, history windows, qualification logic, or artifacts were changed. Repo branch `codex/v61-motion-pacing`, HEAD `2ce777b84bd936a416dfdc7e8cac5d758c04ae57` (clean working tree at start). This differs from the mission's referenced analytical source SHA (`7df38e6d234ae9c4ee425490bc40b8cc92685f85`) by design — that SHA is a frozen historical reference, not the current working tree, and was not touched.

## 1. Provenance (Phase 1)

| dataset | classification | profiles | allowed use |
|---|---|---|---|
| Calibration corpus, train split (`checkpoints/thresholds-6.1.0/profile-estimates.jsonl`, `canonical-corpus-final.json`) | `TUNING_ELIGIBLE` | 791 | exploratory diagnosis, offline counterfactuals (used throughout this autopsy) |
| Calibration corpus, sealed holdout (`evaluation/holdout-evaluation-6.1.0.json(.jsonl)`) | `DESCRIPTIVE_ONLY` | 339 | summarized descriptively below; not used to pick any parameter |
| Paired V6.0 re-evaluation of the same 339 profiles | `HISTORICAL_ONLY` | 339 | descriptive before/after comparison only |
| Frozen V6.1 artifact bundle (thresholds, semantic calibration, distance calibration, session reliability, summary priors, context baseline) | `TUNING_ELIGIBLE` output, frozen for production | 791 (derivation population) | inspected only; unmodified |

Full table with digests: `.local/diagnostics/v61-suppression-autopsy/provenance.json`. Split integrity confirmed from `build-manifest-6.1.0.json`: seed 6000, 791 train / 339 holdout, **zero overlap**.

## 2. What V6.1 actually sees (Phase 2)

The production "history window" is a **365 calendar-day window**, not a match-count cap. `FREE_HISTORY_LIMIT` and `MAX_FREE_HISTORY_LIMIT` are both unset in code and `.env`, with an explicit comment: *"The Free population is a time window, not a match-count product cap... the default is deliberately unbounded so a busy account is not silently reduced to the old 500-row population."* `corpus-diagnostics.json` confirms `window_mode: "per_profile_365_day"` for the whole corpus.

Every family sees the **same raw match set**, but the *real unit of evidence* differs sharply once each family's own opportunity construction is applied:

| family | real opportunity denominator | hardcoded floor |
|---|---|---|
| pool_shape (statistical finding) | whole 365-day match history | none in the fixture path; production additionally requires `canonical_history.audit.completeness == "complete"` |
| transfer | matches that fall in the "reliable_stretch" **distance band** of the player's own hero/role portfolio | ≥12 matches AND ≥6 sessions *in that specific band* |
| post_loss_response | loss→next-match **transitions**, split by result-state, within a session | ≥12 transitions AND ≥8 sessions *per state* |
| combat_expression | context-adjusted matches (involvement, death exposure) | ≥30 matches AND ≥8 sessions AND ≥80% context coverage |
| session_drift | distinct **completed** sessions reaching a specific in-session position (g1..g5+) | ≥12 matches AND ≥8 sessions *per position*, only counting non-censored (completed) sessions |

The (Hero Portfolio / breadth / toolkit) descriptive layer that a player actually perceives as "my Pool" uses essentially the whole match history and has no p-value gate at all (see §5). This is the single most important structural fact in this autopsy.

## 3. Real unit of evidence per family — quantified (Phases 2–7, TUNING_ELIGIBLE, n=791)

From `checkpoints/thresholds-6.1.0/profile-estimates.jsonl` (the actual runtime-parity estimator output used to derive frozen thresholds — not a fixture):

| metric family | % profiles with a usable value | median usable count | median sessions used | vs. overall median (275 matches / 108 sessions) |
|---|---:|---:|---:|---|
| breadth / toolkit (Pool proxy) | 100.0% | 275 | 108 | 100% / 100% |
| involvement / death_exposure (Combat) | 99.4% | 275 | 108 | 100% / 100% |
| transfer_*_delta (coarse) | 99.0% | 103 | 108 | 37% / 100% |
| post_loss_*_delta | 73.2% | 78 | 46 | 28% / 43% |
| session_drift_*_delta | **0.0%** | 0 | 0 | 0% / 0% |

Full table: `opportunity_counts.csv`. Reason strings (`suppression_reasons.csv`) confirm: post_loss fails on `"post-loss sample/session/coverage gate failed"` for 212/791 (26.8%) profiles; session_drift fails on `"session-drift sample/session/coverage gate failed"` for all 791/791.

Aggregate corpus stats (`corpus-diagnostics.json`, n=1,130 profiles, 455,971 matches, 174,088 sessions): **mean 2.62 matches/session**. Short sessions are the norm, which structurally caps how many sessions ever reach in-session position g3/g4/g5+.

## 4. Product-level sparsity — ground truth from the sealed holdout (Phases 6, 14; DESCRIPTIVE_ONLY)

This is the most decisive evidence in the corpus, from `evaluation/holdout-evaluation-6.1.0.json` (339 sealed profiles, all successfully evaluated under the frozen artifacts):

- **`finding_distribution: {"0": 339}`** — every one of the 339 held-out profiles received **zero published Findings**, across **all five families combined**, including pool_shape's own statistical branches.
- **`family_coverage: {}`** and **`semantic_outcome_coverage: {}`** — empty. Not one family, not one semantic outcome, ever published.
- **`element_availability: {"available": 2353, "unavailable": 20}`** — 99.16% of the 7 Elements (breadth/toolkit/involvement/finishing/death_exposure/transfer/consistency) *are* available. The Elements layer is healthy.
- **Paired V6.0 comparison, same 339 people**: `v60_finding_count_distribution: {"0": 235, "1": 81, "2": 19, "3": 4}` — V6.0 published ≥1 finding for **104/339 (30.7%)** of these exact profiles. V6.1 published for **0/339 (0.0%)**.

**This reframes the mission's premise.** It is not "Pool's statistical findings survive more often than Transfer/Post-Loss/Session." The pool_shape *Finding* is exactly as dead as the others (0/339). What a player experiences as "a useful Pool" is the **Hero Portfolio** descriptive layer (`services/api/app/hero_portfolio/`) — a structurally separate code path with its own lenient `eligibility.py`, no FDR gate, and no dependency on `hierarchical_qualification` at all (confirmed by code search: zero references to `qualif`/`publish`/`hierarchical`/`family_q`/`fdr` in that module). The Findings layer — all five families — is a near-complete non-functioning system in the current frozen release, and it is a **measured regression relative to V6.0** on identical people, not a pre-existing baseline of sparsity.

## 5. Why Pool "survives" (Phase headline question)

It doesn't, at the statistical-Finding level — see §4. What survives is the always-attempted Hero Portfolio/Elements presentation, which:
- is gated by simple sample-size/session/coverage thresholds (elements.py `_status_and_limitations`), not a p-value or FDR test;
- uses close to the full match history as its denominator;
- achieved 99.16% availability in the sealed holdout.

This is a `PRESENTATION_BOTTLENECK`-adjacent finding in the sense that the product experience ("Pool is useful, everything else is empty") is being generated almost entirely by a layer the mission's framing didn't originally distinguish from the Findings layer. It is not a bug in the sense of broken code — Hero Portfolio is working as designed — but it means the "5-family Findings system" and "what users perceive as useful" are two very different things today.

## 6. Why other families disappear — family-by-family (Phase 10)

- **session_drift — `OPPORTUNITY_BOTTLENECK`, compounded by an `IMPLEMENTATION_ERROR` in the calibration tool.** 0/791 TUNING_ELIGIBLE profiles (median 275 matches, 108 sessions) ever produced a usable raw session-drift value. Root cause traced two levels deep: (a) `scripts/build_v61_calibration_artifacts.py` calls `derive_thresholds_v61(...)` without ever passing `completed_sessions_by_profile`; (b) `player_analysis_v6/session_drift.py`'s `_completed()` helper is deliberately fail-closed — "*Completion/censoring evidence is mandatory. Treating missing metadata as completed would turn an interrupted history window into a drift signal*" — so with no completion map supplied, **100% of sessions are treated as not-completed** during calibration, guaranteeing zero usable observations. That, in turn, produced a frozen sentinel in `metric-thresholds-6.1.0.json` (`min_sample: 792, min_sessions: 792` — literally one more than the 791-profile training population, i.e. mathematically unreachable by construction, `status: "suppressed_missing_training_support"`). Production's own `completed_sessions` wiring (`analysis/service.py`, built from `SessionResult.completed_sessions`) is correct and does *not* have this specific bug — but the live Finding-level gate (`relationships.py session_position_curve`, needing ≥8 completed sessions reaching a given position) is independently starved by real, short average session length (2.4–2.75 games/session), so 0% publication in the sealed holdout is consistent with genuine opportunity scarcity as well as the calibration-tooling gap. Recommend fixing the calibration wiring regardless, since a threshold artifact derived from zero real observations should never have been allowed to freeze silently.

- **post_loss_response — `OPPORTUNITY_BOTTLENECK` (real, partial).** 26.8% of profiles have zero opportunities at all (never reach a scored transition state with ≥12 transitions/≥8 sessions in any state). For the 73.2% that do, only ~28% of matches and ~43% of sessions actually contribute. This is real, structural, and would not be helped by relaxing q for the profiles that never reach the gate — only more/different sessions help, and only up to what the player's real session cadence allows.

- **transfer — mechanism unresolved (`BLOCKED_COMPUTE`), but opportunity is unlikely to be the primary driver.** The coarse transfer metric is 99.0% available (nearly Pool-level), yet the sealed holdout shows 0/339 published. The true Finding uses a narrower "reliable_stretch" distance-band subset (`estimators.py continuous_transfer`, needing ≥12 matches/≥6 sessions *in that band*) that was not separately instrumented here. Given the coarse metric's high availability, `FAMILY_Q_GATE`/`BRANCH_Q_GATE` (statistical significance, not sample size) is the more likely primary blocker, but this autopsy cannot prove that without executing the real bootstrap.

- **combat_expression — mechanism unresolved (`BLOCKED_COMPUTE`), opportunity is not the driver.** Involvement/death-exposure metrics are 99.4% available — the same denominator as Pool. 0/339 published in the sealed holdout regardless. Points to `FAMILY_Q_GATE`/`BRANCH_Q_GATE`/effect-size gates, not data scarcity.

- **pool_shape (statistical finding, distinct from Hero Portfolio) — mechanism unresolved (`BLOCKED_COMPUTE`), plus one extra disqualifier.** Even with full match-count opportunity, pool_shape's Finding is additionally suppressed whenever `canonical_history.audit.completeness != "complete"` (a data-completeness flag independent of statistics). 0/339 published either way in the sealed holdout.

## 7. A structural multiplicity cost (Phase 4/8, no new computation required)

`hierarchical_qualification` runs a joint 5-family Benjamini–Hochberg correction (`m=5`, fixed) every time, including session_drift, whose p-value is ~1.0 for effectively all profiles. Under BH, the significance bar available to the k-th ranked family is `q·k/m`. With `m=5` fixed by a family that can structurally never contribute a true discovery, the other four families get a bar of `q·k/5` instead of the `q·k/4` they would get under an m=4 correction that excluded a permanently-null family — a mechanical, avoidable **20% stricter bar** for the four potentially-live families. This is a pure property of the BH procedure, verifiable from the code alone, and does not require rerunning anything.

## 8. Is the current q-threshold the main problem?

**PARTLY, and only demonstrably for one family.**

- For **session_drift**, q-threshold relaxation is **mathematically incapable of helping**: p=1.0 for ~100% of profiles because opportunities are structurally zero (fixture path: `_bounded_p` returns exactly 1.0 whenever opportunities<12; production: bootstrap samples are empty/degenerate and `_production_p` fails closed to 1.0). No finite q change rescues a p=1.0 hypothesis.
- For **pool_shape, transfer, combat_expression**, this autopsy found **no opportunity-side explanation** (all three have 99%+ raw-metric availability, or in pool_shape's case, uses nearly the whole history) — yet the sealed holdout shows 0/339 published for all three. This is the strongest available (indirect) evidence that q-threshold and/or effect-size gates, not sample size, are the binding constraint for these three — but it is **not proof**, because the per-profile p-values themselves were not recomputed here (`BLOCKED_COMPUTE`, see below).
- For **post_loss_response**, the dominant blocker for 26.8% of profiles is opportunity, not q — those profiles have p undefined/1.0 regardless of threshold. For the remaining 73.2%, whether q is the binding constraint is unknown (`BLOCKED_COMPUTE`).
- The **5-way BH multiplicity tax** (§7) very likely worsens all of the above by ~20%, independent of the nominal 0.05 value.

## 9. Threshold vs. more history

**More calendar history cannot fix session_drift** (a completed-session-position-count problem, not a match-count problem) **and only partially helps post_loss_response** (needs more distinct multi-game sessions, which a 365-day window only grows if the player's actual queuing cadence produces them — extra days mostly add more of the same short-session distribution). It does essentially nothing for pool_shape/transfer/combat_expression, which already sit at 99–100% raw availability. A genuine `RELAXED_THRESHOLD + CURRENT_HISTORY` vs. `CURRENT_THRESHOLD + MORE_HISTORY` numeric comparison is `BLOCKED_COMPUTE` — it requires the same production bootstrap re-execution noted above.

## 10. Bugs found (Phase 11 — reproduced, not suspected)

1. **Report-assembly crash via schema drift.** 20/359 (5.6%) of holdout evaluation attempts fail with `pydantic.ValidationError` on `FreeDnaReportV61Schema`: `elements.N.interval.method — Extra inputs are not permitted` (also `.iterations`, `.usable_iterations`, `.point`, `.seed` depending on the profile — 15 profiles hit 8 such errors, 4 hit 1, 1 hit 7). `IntervalV6Schema` (consumed by `MeasurementV61Schema.interval`, `report_schemas_v61.py`) only allows `{lower, upper, level}`. The contaminating values match `production_statistics.BOOTSTRAP_VERSION = "session-cluster-bootstrap-2.0.0"` and the shape of `production_statistics.scalar_interval()`/`bootstrap_metric()` output (`lower, upper, level, iterations, usable_iterations, method[, point, seed]`) — i.e., for at least one element per affected profile, the raw bootstrap-result dict is reaching `element["interval"]` without being normalized to the 3-key contract that `dna_assembly_v61.py`'s own overwrite blocks (lines ~1150, ~1197) otherwise apply. This is a **complete report failure**, not a silent suppression, for a non-trivial minority of profiles.
2. **Calibration-tooling gap (session completion never wired into threshold derivation).** See §6 session_drift. `scripts/build_v61_calibration_artifacts.py` never supplies `completed_sessions_by_profile` to `derive_thresholds_v61`, so the derivation is silently computed on zero real session-drift observations, which then froze into an unreachable sentinel threshold. The derivation code itself behaved correctly (fail-closed, well-commented) — the caller simply never gave it the input it needed. Not a runtime/production bug per se, but a real defect in the calibration pipeline that should not have been allowed to produce a "successfully calibrated" artifact from zero support.

No other reproducible implementation bugs were found in the time available (family ID mixing, branch-grouping errors, incorrect q-denominators, V6/V6.1 mixing, and feature-flag inconsistency were checked at the code level for the five-family path and not found; a deeper audit of `legacy_adapter.py`'s 479 lines was not completed — flagged as a candidate for a follow-up pass, not a finding).

## 11. Presentation losses (Phase 12)

- `ANALYTICALLY_PUBLISHED` (finding_count ≥ 1): **0/339** in the sealed holdout. There is nothing to lose at serialization or frontend stages because nothing was published to begin with — `SERIALIZED_NOT_SURFACED` is not observed (not "zero, and healthy"; "zero, because there was never anything to drop"). The one confirmed drop-like failure is the schema crash in §10.1, which is a `REPORT_ASSEMBLY_CRASH`, not a presentation-layer drop of an otherwise-valid finding.

## 12. Suggestive-signal opportunity (Phase 13, evaluation only — not implemented)

Given zero published findings across the entire sealed holdout, a "suggestive" tier calibrated at, say, q<0.10 would still publish **nothing** for session_drift (p≈1.0 regardless) and its yield for the other four families is unknown without the same blocked bootstrap re-execution. What this autopsy *can* say: a suggestive tier is very unlikely to meaningfully reduce the Pool-only experience unless it is paired with (a) removing session_drift from the joint FDR correction when it has zero opportunities (fixing the multiplicity tax in §7), and (b) establishing whether pool_shape/transfer/combat_expression's failures are near-misses or genuinely null — which requires the same real bootstrap execution this autopsy did not perform. Recommending a specific suggestive-tier boundary now would be exactly the kind of post-hoc, ungrounded threshold pick the mission prohibits.

## 13. Root cause

**Primary blocker shares (first_blocking_reason, sums to ~100% over the 5×339 = 1,695 suppressed family-profile pairs in the sealed holdout, all of which are suppressed):**

Precise first-blocking-reason attribution *within* the FAMILY_Q_GATE/BRANCH_Q_GATE vs OPPORTUNITY split for pool_shape/transfer/combat_expression is `BLOCKED_COMPUTE` (would require the production bootstrap). What is `CONFIRMED` from stored data:

- session_drift: 100% `INSUFFICIENT_OPPORTUNITIES` (0/791 raw-metric availability; p=1.0 by construction).
- post_loss_response: ≥26.8% `INSUFFICIENT_OPPORTUNITIES` (never reach the gate); remainder unresolved between opportunity-adjacent effect limits and `FAMILY_Q_GATE`/`BRANCH_Q_GATE`.
- pool_shape, transfer, combat_expression: opportunity is `CONFIRMED NOT` the primary blocker (99–100% raw availability); the actual first blocker among `FAMILY_Q_GATE`, `BRANCH_Q_GATE`, `STABILITY_GATE`, `SEMANTIC_GATE` is `BLOCKED_COMPUTE`.

**All-blocker prevalence (need not sum to 100%):** the 5-way joint BH multiplicity tax (§7) applies to all four non-session_drift families simultaneously and is `CONFIRMED`.

## 14. Primary recommendation

**Do not touch q, minimum support, or the history window yet.** Before any parameter change: (1) fix the two reproduced bugs in §10 (the schema-drift crash, and the calibration completion-wiring gap), (2) exclude session_drift from the joint 5-family BH correction whenever a profile has zero session_drift opportunities, rather than letting a guaranteed-null hypothesis tax the other four families' significance bar, and (3) execute the real production session-cluster bootstrap (2000 iterations) against a sample of TUNING_ELIGIBLE profiles to get actual per-profile p/q-values for pool_shape, transfer, post_loss_response, and combat_expression — this is the single piece of evidence that would let anyone responsibly choose between `RELAX_FAMILY_Q`, `RELAX_BRANCH_Q`, `FIX_SPECIFIC_BUG`, or `ADD_SUGGESTIVE_TIER`. Recommending a specific threshold or tier now, without that evidence, would be exactly the "more findings = better" rationalization the product principle prohibits.

**Secondary recommendation:** separately message the Hero Portfolio layer as the "Pool" experience it already is — it is healthy (99%+ available) and is very likely what is currently reading as "useful" to players, while the Findings layer is the one that needs the engineering work above before it can be trusted to say anything at all.

## 15. Decision matrix

| option | evidence | expected coverage impact | statistical risk | recommendation |
|---|---|---|---|---|
| 1. Keep V6.1 as-is | Findings layer is a confirmed regression vs. V6.0 (0% vs 30.7% on paired profiles) and includes reproducible bugs | none | none | **NO** |
| 2. Relax family q | Would not fix session_drift (p≡1); unknown effect on the other 4 (BLOCKED_COMPUTE) | unknown, possibly none | inflates false-discovery risk without evidence it addresses the real blocker | **INVESTIGATE** (after §14 step 3) |
| 3. Relax branch q | Same as above | unknown | same | **INVESTIGATE** (after §14 step 3) |
| 4. Change minimum support / effective-N rule | Would not fix session_drift or the 26.8% opportunity-starved post_loss profiles (they're gated by session/transition count, not a single N knob) | low for those two families; unknown for others | low if scoped narrowly | **INVESTIGATE**, narrowly, only after distinguishing opportunity- vs q-limited cases |
| 5. Analyze more historical matches | Confirmed structurally weak for session_drift/post_loss (session-cadence-limited, not match-count-limited); ~99–100% already for pool/transfer/combat | low | none (no new collection needed; window is calendar-based already) | **NO** as a primary lever |
| 6. Add suggestive-signal tier | Cannot be responsibly calibrated without the blocked bootstrap; risks the "richer at all costs" failure mode | unknown | high if boundary is picked without real p-values | **INVESTIGATE**, only after §14 step 3 |
| 7. Fix specific bug | Two reproducible bugs confirmed with exact code paths (§10) | fixes the 5.6% hard-crash immediately; fixes a calibration integrity gap | none — pure correctness fix | **YES** |
| 8. Presentation-only change | Nothing valid is being suppressed at presentation (§11); the real gap is upstream | none for the Findings sparsity problem | none | **NO** as a fix for sparsity; **YES** as a near-term move to foreground Hero Portfolio/Elements as "the useful part" while Findings is repaired |

**Primary: option 7 (fix bugs) + the three-step investigation in §14.** Everything else is premature.

## 16. What would change this recommendation

If executing the real production bootstrap on a TUNING_ELIGIBLE sample showed that pool_shape/transfer/combat_expression's p-values cluster just above 0.05 (e.g., a majority within 2x of the q cutoff, or branch-level q-values in the 0.05–0.10 band for most profiles) — genuine near-misses, not p≈1 nulls — that would make **RELAX_BRANCH_Q** (not family q, since the joint procedure's real leak is at the branch level for families that already clear family-level qualification) the preferred intervention instead of pure bug-fixing. Conversely, if those p-values also cluster near 1.0 like session_drift's, that would point toward the semantic-outcome catalog or estimator definitions themselves being miscalibrated (`SEMANTIC_PUBLICATION_BOTTLENECK`) rather than the threshold being wrong.

## 17. What must NOT change yet

Thresholds, minimum-support rules, the history window, qualification/publication logic, and the frozen artifact bundle — all untouched in this pass and should stay untouched until the bootstrap re-execution in §14 produces real per-profile p/q-values.

## 18. Files created

`.local/diagnostics/v61-suppression-autopsy/`: `provenance.json`, `opportunity_counts.csv`, `suppression_reasons.csv`, `publication_coverage.csv`, `presentation_dropoff.csv`, `q_threshold_sensitivity.csv`, `history_window_sensitivity.csv`, `family_funnel.csv`, `aggregate_summary.json`. (`profile_family_trace.csv`, `calibration_evaluation.py`-level per-profile p/q traces, and a full q-threshold yield table were not produced — see BLOCKED_COMPUTE items above; producing them safely requires executing the real bootstrap, which this pass did not do in order to avoid fabricating numbers.) This report: `docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27.md`.

## 19. Final integrity verification

- Analytical source SHA referenced by the mission (`7df38e6d234ae9c4ee425490bc40b8cc92685f85`): unchanged, not touched.
- Frozen artifact bundle digest (`8e9e22a9...`): unchanged; artifact files were only read.
- Holdout: not rerun; only descriptive summarization of already-produced `evaluation/holdout-evaluation-6.1.0.json(.jsonl)`.
- OpenDota/Steam collection calls: 0.
- No deployment, no merge to main, no production/config changes.
