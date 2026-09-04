# V7 research line — independent red-team audit — 2026-09-04

An adversarial audit of the whole V7 post-corpus research line: the handoff, the
capability atlas, the discovery screen, the statistical tournament, the
qualification ceiling and the portfolio coverage analysis. The brief was to
attack the work, not to confirm it. Nothing below is taken on a document's word
where it could be recomputed on DISCOVERY.

```text
PHASE: V7_RED_TEAM_AUDIT
STATUS: COMPLETE
SPLIT USED: DISCOVERY only
CANDIDATE_TEST READ: NO
CALIBRATION_RESERVED / SEALED_VALIDATION TOUCHED: NO
NEW STRATZ CALLS: 0    PLAYBACK: 0    OPENDOTA: 0    NETWORK: none
RAW DATA COMMITTED: NO
PUBLICATION THRESHOLDS CHOSEN: NO
IDENTIFIERS IN THIS DOCUMENT: none — aggregate statistics only
```

Base SHA `5cad68c`, branch `v7/luna-e-red-team`. New checks live in
`scripts/v7_research/redteam.py` with unit tests in
`tests/unit/test_v7_research_redteam.py`.

## 0. Headline

The corpus, the semantics, the split hygiene and the statistical machinery are
sound, and I could not break any of them. Every headline number I attempted to
reproduce reproduced, most of them to the last published digit.

Three things are wrong, and one of them is load-bearing:

1. **The one-pass guarantee on `CANDIDATE_TEST` is not provable and is not
   literally true.** The capability atlas reads both research splits, the
   access ledger is written after the analysis rather than before it, and the
   single ledger line was appended by hand. The leak is aggregate-only and I
   show it changed no decision — but the control does not do what three
   documents say it does.
2. **The mode-split probe that demoted `duration_tempo` to C was run on one
   family.** Run on all of them, it is *worse* for `post_loss_hero_switch` (A)
   and `transfer_risk` (B) than for the candidate it demoted.
3. **The portfolio coverage table labelled "all twelve" is nine.**

None of this changes the programme's central conclusion. The target is
unreachable under a significance gate, and the audit makes that conclusion
stronger, not weaker.

## 1. Disposition table

| # | severity | issue | disposition |
|---|:--:|---|---|
| C1 | **critical** | `CANDIDATE_TEST` was read outside the ledger, and the ledger cannot prove a read count | **MITIGATED** — leak quantified as decision-neutral; control must be rebuilt before the next confirmation pass |
| M1 | major | the mode-split probe was applied to one family and used to demote it; applied uniformly it is worse for two A/B candidates | **REJECTS GRADE** — `post_loss_hero_switch` A→B, `transfer_risk` B→C |
| M2 | major | the portfolio "all twelve" coverage table and the 37.6%-uncovered claim are computed over nine candidates | **RESOLVED** — corrected figures below |
| M3 | major | no multiplicity correction is computed anywhere in the line | **RESOLVED** — corrected coverage computed below |
| M4 | major | report-time economic feasibility is asserted, never measured | **CARRIED AS OWNER TRADEOFF** — per-report acquisition cost quantified below |
| M5 | major | six estimand constants are asserted "chosen once, never tuned" with no artefact | **CARRIED AS OWNER TRADEOFF** |
| M6 | major | the negative control is an outcome family, and every outcome family collapsed | **CARRIED AS OWNER TRADEOFF** |
| M7 | major | the discovery document's stated code SHA does not contain the code it documents | **RESOLVED** — correct SHA identified |
| m1 | minor | `lead_retention`'s response is `is_victory`; the screen's own outcome-pruning rule was applied by family name, not by response | MITIGATED — it graded D regardless |
| m2 | minor | cross-player overlap is quoted at the match level (0.85% on DISCOVERY) and never at the account level (69% of accounts) | MITIGATED — effect on `tau` is negligible |
| m3 | minor | `hero_novelty` carries a smaller context set than every other history family; `duration_tempo` uniquely projects out the match result | MITIGATED — disclosed here |
| m4 | minor | `--acknowledge-repeat` reopens the confirmation split from the CLI and is documented nowhere | MITIGATED — disclosed here |
| m5 | minor | `structural_eligible` is `null` in every canonical row | MITIGATED — dead field, no consumer |
| R1–R9 | — | nine substantive claims I attacked and could not break | **RESOLVED** — §5 |

## 2. The critical finding: the one-pass guarantee

Three documents state that `CANDIDATE_TEST` was read exactly once and that the
count is "a fact on disk rather than a claim in prose". It is a claim in prose.

**The ledger line was written by hand.** Its own `note` field says so: the
writer hit a relative-path bug *after* the analysis completed, so the run that
read the split wrote its output and then failed to ledger it. A human appended
the line afterwards.

**The ledger is appended after the read, not before it.** In
`scripts/v7_statistical_tournament.py::stage_candidate_test` the split is
loaded, the full evaluation runs, the output file is written, and only then is
the ledger line appended. Any read that crashes, is interrupted, or is aborted
by the analyst leaves the data seen and the ledger clean. The failure mode is
not hypothetical; it is the one that actually happened. A ledger that records
intent *before* the read and outcome after it is the only version of this
control that can be trusted.

**Ordinary research code can read the split without touching the ledger.**
`corpus.iter_players` fails closed on `CALIBRATION_RESERVED` and
`SEALED_VALIDATION` — verified, and there is no canonical document for either
partition on disk at all — but its default `splits` argument is
`RESEARCH_SPLITS`, which is `DISCOVERY | CANDIDATE_TEST`. One script exercises
that default: `scripts/v7_capability_atlas.py` calls `iter_players(paths,
"history")` and `iter_players(paths, "parsed")` with no split argument. The
capability atlas is therefore computed over all 900 research accounts, which
the atlas document states plainly ("players 900", "distribution over all 900
sampled accounts") without noting that 300 of them are the confirmation split.

That matters because the atlas is not inert: its §5.1 is handed to candidate
design as a hard requirement ("pool Turbo with standard modes using mode as
context, or accept that the portfolio target is unreachable").

**Quantifying the leak.** I recomputed the atlas's decision-relevant support
shares on DISCOVERY alone:

| support share | DISCOVERY only | as published (900) | delta |
|---|---:|---:|---:|
| product-context ≥30 | 0.897 | 0.902 | 0.005 |
| product-context ≥100 | 0.843 | 0.853 | 0.010 |
| standard-mode ≥30 | 0.593 | 0.601 | 0.008 |
| standard-mode ≥100 | 0.447 | 0.450 | 0.003 |
| Turbo ≥30 | 0.777 | 0.782 | 0.005 |

Nothing moves by more than one point, and the 60%-versus-90% gap that drives
the pooling requirement is identical on either split. **No design decision in
this line depended on having seen `CANDIDATE_TEST`**, and the confirmation pass
itself was a genuine single pass on per-player statistics.

Disposition **MITIGATED**, severity **critical**, because the guarantee — not
the science — is what fails, and the guarantee is what the next phase would
lean on. Required before any further confirmation read: ledger-before-read,
`iter_players` defaulting to `DISCOVERY` with `CANDIDATE_TEST` requiring an
explicit ledgered call, and the atlas re-run on DISCOVERY.

## 3. The mode-split probe, applied to everything

Tournament §4.1 demoted `duration_tempo` to C on one measurement: per-player
estimates computed on Turbo matches alone and on standard matches alone agree
at only Spearman **+0.495** over 168 players. The probe was run on no other
family.

I reproduced that number exactly (+0.495, 168 players, `tau` 0.145 Turbo versus
0.085 standard) and then ran the identical probe, with the same descriptive
block geometry, over the other five high-grade families. Raw agreement is not
comparable across families of different reliability, so each row is also
divided by its own within-mode split-half reliability
(`redteam.disattenuated_agreement`).

| family | grade | cross-mode ρ | rel. Turbo | rel. standard | **disattenuated** | n |
|---|:--:|---:|---:|---:|---:|---:|
| post_loss_requeue_latency | B | +0.502 | 0.698 | 0.658 | **+0.741** | 115 |
| post_loss_session_continuation | **A** | +0.482 | 0.650 | 0.658 | **+0.738** | 168 |
| duration_tempo | **C** | +0.495 | 0.981 | 0.901 | **+0.526** | 168 |
| hero_novelty | C | +0.458 | 0.948 | 0.901 | **+0.495** | 162 |
| post_loss_hero_switch | **A** | +0.309 | 0.860 | 0.585 | **+0.436** | 115 |
| transfer_risk | **B** | +0.229 | 0.652 | 0.574 | **+0.374** | 151 |

Two of the grades are vindicated: `post_loss_session_continuation` and
`post_loss_requeue_latency` are the *most* mode-portable families in the set,
and their A/B grades survive this attack cleanly.

Two are not. `post_loss_hero_switch` — the second A, the one graded "best
heterogeneity-to-noise among the calibrated families" — is measurably *more*
mode-specific than the candidate that was demoted to C for exactly this
property, and its between-player spread is twice as large inside Turbo as
inside standard (`tau` 0.119 versus 0.058). Independently, its per-player
estimate correlates **−0.452** with the player's own Turbo share, the largest
such coupling of any of the twelve; `duration_tempo`'s is +0.248.
`transfer_risk` is the worst in the set at +0.374.

The tournament's own words about `duration_tempo` — "about half one personal
tempo and half a mode-mix artefact" — apply with more force to a candidate it
graded A.

**Disposition: REJECTS GRADE.** I downgrade `post_loss_hero_switch` A→B and
`transfer_risk` B→C. The correct process fix is that a probe capable of
demoting a candidate is run on every candidate before any grade is written, and
disattenuated before families are compared.

## 4. Corrected owner-facing numbers

### 4.1 The "all twelve" coverage table is nine

`scripts/v7_portfolio_analysis.py` builds `coverage_counts` and
`never_qualified` over `selectable` — the nine A/B/C candidates — not over
`families`. The document presents that histogram under "across **all twelve**
candidates" and draws the "37.6% of information-eligible accounts qualify for
nothing across all twelve candidates" conclusion from it.

| at provisional 0.01, of 527 | published as "all twelve" (really nine) | **actually all twelve** |
|---|---:|---:|
| qualify for nothing | 198 (37.6%) | **188 (35.7%)** |
| ≥1 | 62.4% | **64.3%** |
| ≥2 | 35.3% | **37.0%** |
| ≥3 | 19.2% | **20.5%** |

The corrected all-twelve figures agree with the tournament's own DISCOVERY
portfolio section (339/600 at ≥1, 108/600 at ≥3), which the portfolio document
therefore silently contradicts. Direction of the error is conservative — the
published table understates coverage and overstates the uncovered share — so no
conclusion reverses. It is still a wrong number in the section an owner will
read most closely.

### 4.2 Multiplicity was never priced

Every phase declares that no multiplicity correction is applied and that the
numbers are optimistic. None of them says by how much. Twelve families were
tested per player. Bonferroni is one line:

| level | option A | option B | option C | option D | all twelve ≥3 | all twelve ≥1 |
|---|---:|---:|---:|---:|---:|---:|
| 0.05 | 0.277 | 0.152 | 0.135 | 0.230 | 0.380 | 0.824 |
| 0.01 (as published) | **0.154** | 0.072 | 0.066 | 0.131 | 0.205 | 0.643 |
| 0.01 / 5 | 0.078 | 0.034 | 0.030 | 0.059 | 0.095 | 0.490 |
| 0.01 / 12 | **0.057** | 0.032 | 0.023 | 0.044 | 0.072 | 0.416 |

The best five-Finding portfolio the corpus supports delivers ≥3 qualified
Findings to **5.7%** of information-eligible accounts once the twelve tested
families are paid for, against the 15.4% the portfolio document quotes and the
80–90% target. Every option A–D reproduced exactly at 0.01 and 0.05, and option
A is confirmed as the argmax over all 126 combinations at both corrected and
uncorrected levels.

### 4.3 Report-time economics were asserted, not measured

The tournament's A/B decision table gives every history-only candidate
"report-time cost: history only; one linear pass, milliseconds" and
`purchase_tempo` "parsed detail; one sort per match, moderate". That is compute
cost. The cost of a report is dominated by acquisition, which is nowhere
estimated. From the corpus request ledger (23,023 rows):

| operation | requests | accounts served | **requests per account** |
|---|---:|---:|---:|
| `GetPlayerHistoryPage` | 6,289 | 900 | **7.0** |
| `GetParsedAcquisitionBatch` | 16,734 | 235 | **71.2** |

A history-only Finding needs the player's 365-day history: about seven
paginated provider calls for the median account, not milliseconds. A
parsed-dependent Finding needs roughly **ten times** that. `purchase_tempo`
appears in owner options B and C; on this evidence it is the single most
expensive candidate in the set per report, and it also has the lowest reach of
any A/B candidate (68/600 sampled = 11.3%). No document puts those two facts
next to each other. **Carried as an owner tradeoff** — the numbers above are
per-collection and a live report may page less deeply, but no phase has
measured that either.

### 4.4 The estimand constants are not reconstructible

Six constants define the frozen twelve: the 3-hour session gap, `NOVELTY_DAYS`
30, `COMFORT_POOL_SIZE` 5, `PURCHASE_LANDMARK` 8, `STATE_LEAD_GOLD` 5,000, and
the 30/50-match warm-ups. Each is documented as chosen once and never tuned
against an outcome. Only the session gap was actually swept afterwards, and it
held (ρ ≥ +0.973 over 2 h–6 h, which I did not re-run but which is internally
consistent). For the other five there is no artefact recording what else was
tried. A registered analysis is reconstructible from this repository at the
level of *code*, and not at the level of *choices*. That is an honesty limit on
the multiplicity accounting, not evidence that tuning occurred.

### 4.5 The negative control is an outcome family

`side_sensitivity`'s response is `is_victory`. So is `lead_retention`'s, and so
was every family the screen killed under "match outcomes are not a personal
trait" — a result the screen states as its most useful finding. The control
therefore shares the property that made four other families collapse, and
"`sigma_between` = 0, the method does not manufacture individuality" cannot be
separated from "outcome responses have no individual variance" by this control
alone.

Two things save it. Its *Type-I* evidence is unaffected: it is a binary
within-player contrast, structurally the same test as
`post_loss_session_continuation` and `post_loss_hero_switch`, and its measured
0.0500/0.0103 is directly comparable. And the permutation nulls are themselves
behaviour-valued placebos on the real families. But the tournament's negative
control band — the −0.073/+0.218 pair that set the "below +0.25 is not
stability" rule and demoted `transfer_activity` to D — rests on two
observations from a family of a different response type. The tournament flags
the thinness of two points; it does not flag the type mismatch. A
behaviour-valued placebo (a randomly relabelled arm on a behavioural response)
should be added before that band is used again.

## 5. What I attacked and could not break

Nine claims, all recomputed from the corpus on DISCOVERY, independently of the
scripts that produced them where the brief asked for it.

**R1 — split and cohort integrity. RESOLVED.** 900 canonical history documents
(600 DISCOVERY, 300 `CANDIDATE_TEST`), 235 parsed (116/119), 1,200 frozen
members, identity overlap across splits **0**. No canonical document exists for
`CALIBRATION_RESERVED` or `SEALED_VALIDATION` at all, so the fail-closed reader
is a second line of defence rather than the only one. Truncation counts match
(8 DISCOVERY, 1 `CANDIDATE_TEST`).

**R2 — the forbidden-surface gate. RESOLVED.** `forbidden_fields_in` over all
1,135 canonical documents returns the empty set. No rank, MMR, bracket,
leaderboard, IMP, behaviour, smurf, award, prediction or playback field name
appears anywhere.

**R3 — hidden skill proxies. RESOLVED, with one qualification.** I correlated
every candidate's per-player estimate against per-player win rate,
(kills+assists)/10 min, deaths/10 min, KDA, log match volume, Turbo share and
ranked share on DISCOVERY. **No candidate correlates with win rate beyond
|0.18|** (largest: `duration_tempo` −0.178, `hero_novelty` +0.154). My prime
suspect was `purchase_tempo` — progress at the 8th item purchase is the closest
thing in this corpus to the `networthPerMinute` the collection deliberately did
not acquire — and it does not behave like one: ρ +0.060 with win rate, −0.247
with (K+A)/10 min. The qualification: with no rank field and no farm field in
the corpus, win rate and KDA are the only skill proxies available to test
against, and they are weak ones. I can say no candidate is a *naked* rank
proxy. I cannot certify that none is a subtle one.

The two genuine performance-valued families, `risk_appetite` (deaths/10 min)
and `involvement_level` ((K+A)/10 min), were pruned by the screen for exactly
this reason. `transfer_risk` and `transfer_activity` reuse those responses but
only as within-player contrasts, which differences the level out; that is a
defensible distinction, provided no report ever renders the per-arm levels.

**R4 — hidden parsed conditioning. RESOLVED, claim verified.** The atlas claims
`enum_failure` is a disguised parsed filter and that it was removed. Over the
full corpus the joint distribution is (`enum_failure`, `is_parsed`): (false,
true) 443,670 rows, (true, false) 122,079, (true, true) 14,574 — **there is no
row with `enum_failure = false` and `is_parsed = false`**, exactly as claimed.
The corrected structural gate reproduces at 580,323 structurally observable and
562,250 product-context rows. The atlas's role-known figure of 429,549 differs
from the 429,800 the naive gate produces by precisely the 251 product-context
rows whose lane is `UNKNOWN`; both numbers are right for their own definition.
No surviving candidate reintroduces the conditioning: the parsed-dependent five
declare it, and `position_flexibility` additionally conditions on two
*consecutive* parsed matches, which its 37/600 information reach already
reflects.

**R5 — trajectory semantics and the Dire sign flip. RESOLVED, claim verified.**
Array length equals `ceil(duration/60) + 1` for **122,449** of 124,535 rows and
is one greater for **2,086** — the atlas's figures to the row — with **zero**
rows where the three arrays disagree in length. `radiant_networth_leads` is a
cumulative level, not an increment: the sign of the final element predicts the
Radiant win in **96.6%** of rows, against **86.9%** for the sign of the
cumulative sum. `player_networth_lead()` performs the Dire negation and clips
to `min(len, ceil(duration/60)+1)`; every consumer of a trajectory in
`features.py` goes through it.

**R6 — the null models. RESOLVED; the fixed-projection approximation is free.**
The tournament's own judgement call 5 flags that Type-I was measured with the
context projection held fixed. I re-implemented the contrast null with the
projection *recomputed inside every replicate* — permute arms, re-encode,
re-project, re-infer — over 40 replicates on three families:

| family | fixed projection 0.05 / 0.01 | **re-projected** 0.05 / 0.01 | published |
|---|---|---|---|
| post_loss_session_continuation | 0.0502 / 0.0101 | 0.0487 / 0.0105 | 0.0508 / 0.0099 |
| post_loss_hero_switch | 0.0500 / 0.0089 | 0.0509 / 0.0095 | 0.0500 / 0.0091 |
| transfer_risk | 0.0492 / 0.0081 | 0.0489 / 0.0084 | 0.0488 / 0.0082 |

The approximation costs **at most 0.0015 at nominal 0.05**, inside Monte-Carlo
error, and my fixed-projection reproduction matches the published values. The
"all seven contrast families are calibrated" claim survives the strongest
attack I could mount on it. I did not attempt to rescue the level families;
their anticonservatism is the tournament's own finding and it is against their
interest, which is the direction of error that needs no audit.

**R7 — declared but unprojected confounders. RESOLVED.** The A/B table names
time of day and accumulated session length as the main confounders of the
post-loss families, and `base_ctx` carries neither (only
`post_loss_session_continuation` carries an hour bucket). I rebuilt all three
post-loss families with hour-of-day and within-session position added as
context factors:

| family | `tau` before → after | qualified 0.01 before → after | ρ between the two views |
|---|---|---|---:|
| post_loss_session_continuation | 0.0977 → 0.0976 | 145 → 143 | **+1.000** |
| post_loss_requeue_latency | 0.2193 → 0.2182 | 114 → 113 | **+0.999** |
| post_loss_hero_switch | 0.1068 → 0.1068 | 103 → 105 | **+1.000** |

My hypothesis — that losses cluster late in sessions and that per-player
variation in *when* losses happen masquerades as variation in *response* to
them — is not supported. A player × session-position interaction remains
untested, but the first-order confound is absent.

**R8 — the qualification ceiling. RESOLVED; the conclusion is sound and the
diagnosis of its own optimism is right.** The closed form is correct:
`delta_hat - mu` is marginally `N(0, tau^2 + SE^2)`, so `q(z,r) = 2 Phi(-z /
sqrt(1+r^2))`, and I reproduce the required-ratio table (4.54 at 0.05 for a
three-of-five 80% target; 7.67 for a single candidate at 80%). Two attacks:

*Does evaluating at the median standard error flatter it?* No.
`redteam.expected_qualified_share` averages the per-player probability over the
actual per-player standard errors; the two agree closely for every family
(`duration_tempo` 0.759 averaged versus 0.791 at the median;
`post_loss_session_continuation` 0.352 versus 0.354). Standard-error
heterogeneity does not explain the predicted-versus-observed gap.

*Is `tau` real, or an outlier artefact that would make every `tau/SE` argument
unsound?* Real. `redteam.marginal_variance_ratio` compares the realised
`Var(delta_hat - mu)` with the model's `tau^2 + E[SE^2]`; the ratio is
**0.87–1.21 across all thirteen families**, so the variance components describe
the data they were fitted to.

Having ruled both out, the ceiling document's own reading 3 — that the residual
optimism is non-normality of the true effects — is the surviving explanation,
and the direction is the honest one: the closed form over-predicts, so the
ceiling is an upper bound on an upper bound, and the conclusion that an 80–90%
three-of-five portfolio is unreachable under a significance gate is
**strengthened** by the failure of the normality assumption, not threatened by
it. If normality fails, reach falls further.

**R9 — provenance and reproducibility. RESOLVED apart from M7.** Recomputed
from the checked-in code: frozen serious-candidate digest
`f9f5af78…5086c`, full 36-family registry digest `24de598a…d0164`, inference
design digest `4b702dc2…4573f3`, and both corpus manifest digests
(`256676ab…` raw, `d45bf9a0…` canonical) — all match every document that quotes
them. Two headline numbers reproduced end to end from the corpus:

- **All thirteen families' information-eligible counts, τ, and qualified-at-0.01
  counts reproduce exactly** — 527/511/511/355/495/495/372/37/67/68/109/113/527
  eligible and 145/103/114/109/39/30/120/13/16/35/5/4/5 qualified, τ to four
  decimals. So does `hero_novelty`'s published −0.526 volume correlation and
  `duration_tempo`'s +0.495 cross-mode agreement.
- **All four owner portfolio options reproduce exactly**: P(≥3) at 0.01 of
  0.154 / 0.072 / 0.066 / 0.131 and at 0.05 of 0.277 / 0.152 / 0.135 / 0.230,
  over an independently recomputed 527-account information-eligible population,
  and option A is confirmed the argmax of all 126 combinations.

The one provenance defect (M7): the discovery document records "code SHA
`dd0930269fcd324b56d230f11d83ffddcd0aaf9c`". That commit is the *capability
atlas* commit and contains none of `scripts/v7_discovery_screen.py`,
`features.py`, `registry.py` or `screen.py`, so the reproduce command in that
document cannot be run at the SHA the document names. The code is at `db45c1b`.
The tournament document's "base SHA" is honestly labelled as a branch base and
is not the same defect.

Also worth recording, in the programme's favour: the portfolio coverage
histogram is an **empirical joint count over real players**, not a binomial
independence assumption. Only the ceiling document uses independence, and it
says so and explains why the convenient assumption is the conservative choice
for its argument.

## 6. Smaller findings

- **`lead_retention` is an outcome family that escaped the outcome rule.** Its
  response is `1.0 if row["is_victory"]`. The screen killed
  `post_loss_next_outcome`, `transfer_outcome`, `session_drift_outcome` and
  `lane_recovery_outcome` under "whether you win the next game is not who you
  are", and `lead_retention` was carried into the frozen twelve anyway. It
  graded D at the null rate, so nothing downstream is affected — but the
  pruning rule was applied by family name rather than by response variable, and
  a rule applied by name is not a rule.
- **Cross-player overlap is quoted only in its flattering framing.** 1.4%
  corpus-wide and 0.85% on DISCOVERY is the *match*-level share. At the account
  level, **417 of 600 DISCOVERY accounts (69%)** share at least one match with
  another sampled account. The estimand is within-player and each affected
  account shares on the order of eight matches out of a median 526, so the
  effect on `tau` and on the per-player standard errors is negligible — but the
  account-level number is the one a reader would want and it appears nowhere.
- **Inconsistent context sets.** `hero_novelty` projects out only mode, patch
  and lobby — no hero, duration or side — while every other history family uses
  the full `base_ctx`. `duration_tempo` uniquely adds the match `result` to its
  context, so it is the only family that conditions on the outcome. Neither is
  disclosed, and both are defensible; the point is that "the same context
  adjustment across families" is not what the code does.
- **`--acknowledge-repeat`.** `stage_candidate_test` accepts a flag that
  overrides the one-pass refusal. It is a reasonable escape hatch and it is
  documented in no evidence file.
- **`structural_eligible` is `null` in every canonical history row.** A dead
  field bearing the name of the exact concept the atlas had to correct. It
  should be dropped rather than left for a future reader to gate on.

## 7. Candidate dispositions

| candidate | tournament grade | **red-team grade** | reason |
|---|:--:|:--:|---|
| post_loss_session_continuation | A | **A** | survives every attack; the most mode-portable family in the set (disattenuated +0.738), confounders tested and absent, null calibrated under re-projection |
| post_loss_requeue_latency | B | **B** | as sound as the A above (+0.741) and the demotion is portfolio reasoning, which I agree with |
| post_loss_hero_switch | A | **B — downgraded** | disattenuated cross-mode agreement +0.436, below the +0.526 that demoted `duration_tempo`; ρ −0.452 with the player's Turbo share, the largest in the set; `tau` twice as large in Turbo as in standard |
| transfer_risk | B | **C — downgraded** | least mode-portable family measured (+0.374); already the weakest A/B on reach (≈8% qualify) with an unsettled hero-in-projection estimand |
| purchase_tempo | B | **B, with a cost flag** | statistically the strongest heterogeneity in the set and not a farm proxy on the evidence available; but ~71 provider calls per report against ~7, 11.3% reach of sampled, an unverified item vocabulary, and a level family whose p-value the tournament could not certify |
| duration_tempo, hero_novelty, position_flexibility, fight_timing_centroid | C | **C** | no change; `duration_tempo` is partly rehabilitated *relative to* `post_loss_hero_switch`, but its uncertifiable null stands on its own |
| transfer_activity, lead_retention, lane_recovery_participation | D | **D** | no change; `transfer_activity`'s D rests on a two-point control band of the wrong response type and should be read as "unproven", not "disproven" |

## 8. Verdict

```text
research line sound enough for a five-Finding owner selection: YES, with
                                                               conditions
unresolved critical findings: 0 (C1 mitigated, remediation specified)
candidates downgraded: 2   candidates rejected: 0
headline numbers independently reproduced: 4 of 4 attempted, all matched
```

The science is honest and it is unusually well documented against its own
interest: the phases that could have flattered themselves — the level families'
Type-I, the shrinkage inflation, the chronological split-half correction, the
18% portfolio shortfall — all report the number that hurts. I went looking for
a hidden skill proxy, a reintroduced parsed conditioning, an uncalibrated null
sold as calibrated, and an inflated `tau`, and found none of them.

What an owner must be told before selecting:

1. the one-pass guarantee on `CANDIDATE_TEST` is not currently provable (§2),
   and the control must be rebuilt before any further confirmation read;
2. `post_loss_hero_switch` is not an A and `transfer_risk` is not a B (§3), so
   the "only all-A/B option" framing of portfolio option B no longer holds;
3. the corrected all-twelve coverage figures, and the multiplicity-corrected
   coverage — the best portfolio reaches **5.7%**, not 15.4%, once twelve
   tested families are paid for (§4.1–4.2);
4. that report-time cost has never been measured, and that the cheapest-looking
   candidate on the compute axis is the most expensive on the acquisition axis
   (§4.3).

None of those reverses the programme's central conclusion, which the audit
confirms and sharpens: **under a significance gate against the population
average, this corpus cannot deliver three Findings to 80–90% of users, and the
failure of the ceiling's normality assumption makes the shortfall larger rather
than smaller.** The decision in front of the owner is the qualification
concept, not the candidate list.

## Validation

```text
uv run ruff check scripts tests: PASS
uv run pytest -q tests/unit:     784 passed
splits read:                     DISCOVERY only
new provider calls:              0
identifiers in committed files:  none
```
