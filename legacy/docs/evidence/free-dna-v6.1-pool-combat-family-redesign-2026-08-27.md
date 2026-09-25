# V6.1 Pool Shape + Combat Family Redesign

## Status

**PASS — Pool is demoted to descriptive surfaces and Combat is reduced to one
renamed relationship family.**

## Integrity

| item | value |
| --- | --- |
| task type | PRODUCT + ANALYTICAL SPECIFICATION + DOCUMENTATION |
| base SHA | `f1e5961242f45abfcf7e2408f3815572ca02ef17` |
| branch | `research/v61-pool-combat-family-redesign` |
| origin/main observed at start | `e523d855e307f1e0202377b5269142c0e009b65a` |
| external collection calls | 0 |
| holdout reruns | 0 |
| simulations | 0 |
| thresholds calibrated | 0 |
| production changes | 0 |

The redesign used repository documentation and source code only. It did not
load the 791-profile tuning partition because product-yield inspection was not
needed to make either decision.

## Why this redesign was required

Pool Shape mixed concentration, breadth, mapped toolkit, and annual migration
under one root even though those questions already have separate descriptive
homes. Combat mixed absolute Element levels, component equivalence,
result-expression relationships, and localized variance, then projected them
from one incompatible-unit scalar. Neither root described one testable,
memorable player question.

## Product standard

A Finding must add a relationship or repeated behavioral discovery that the
Elements cannot already communicate directly. An Element owns a stable
descriptive dimension. Supporting signals explain or qualify a Finding but do
not become Findings by acquiring clever branch names. Product volume and
historical family count are not reasons to retain a weak root.

## Pool decomposition

### Candidate questions

| candidate | player question | evidence supported now | finding value | decision |
| --- | --- | --- | --- | --- |
| Concentration | Do a few heroes carry most of the year? | Effective hero count, top shares, HHI, stable core | Duplicates Breadth and the Hero Portfolio concentration story | ELEMENT |
| Functional/Role Shape | Do the heroes span actual roles? | No; summary lane/role hints are explicitly not role truth | Strong future question, unsupported in current lineage | DEFER_TO_STRATZ/V7 |
| Hero-vs-Toolkit Shape | Does hero variety translate into mapped functional variety? | Breadth, fractional taxonomy job mass, coverage/sensitivity | A useful descriptive contrast, but it is exactly the relationship between two existing Elements | ELEMENT_COMPARISON |
| Migration/Evolution | Did the pool meaningfully change over the year? | Chronological thirds and hero/job JSD | Already has Hero Portfolio Evolution and Stability ownership; role migration would be a future temporal hypothesis | DEFER_FUTURE_HYPOTHESIS |
| Hidden Center | Do many names reduce to one repeated pattern? | Concentration plus mapped toolkit descriptors | Memorable copy, but no distinct construct beyond Breadth/Toolkit/Common Thread | DETERMINISTIC_DESCRIPTION |

### Evidence overlap

Breadth already owns hero-distribution width. Toolkit already owns mapped-job
width. Hero Portfolio owns Common Thread, Exception, concentration storytelling,
and Pool Evolution. A Pool Finding made from the same annual estimates would
double-count descriptive evidence rather than discover a new conditional
relationship. Chronological migration is a separate temporal question, not a
branch of static pool shape.

### Finding vs Element

Concentration, hero breadth, mapped toolkit breadth, stable core, and a plain
Breadth-versus-Toolkit comparison remain descriptive. The report may say, for
example, that the supported hero pool is broad while the mapped toolkit is
narrow, but it must present the two owned Element estimates and taxonomy limit;
it must not promote the juxtaposition to a statistically qualified Finding.

### Decision

`DEMOTE_TO_ELEMENTS`.

```text
PRIMARY PLAYER-FACING QUESTION:
How wide is your hero pool, and how wide is the mapped toolkit beneath it?

PRIMARY BEHAVIORAL CLAIM:
None as a Finding; Breadth and Toolkit describe the two supported dimensions.

WHAT COUNTS AS EVIDENCE:
Effective hero distribution, top shares, effective mapped-job distribution,
taxonomy coverage, and taxonomy sensitivity under their separate Element gates.

WHAT DOES NOT COUNT AS EVIDENCE:
Actual role, intent, comfort, mastery, outcome, chronology, or a zone-label
comparison treated as a new hypothesis.

SUPPORTING SIGNALS:
Stable core, HHI, top-1/top-3/top-5 shares, job redundancy, and portfolio rows.

ALTERNATIVE EXPLANATIONS:
Hero availability, patches, editorial taxonomy, actual role selection, draft,
and the bounded annual window.

DEFERRED OLD BRANCHES:
hidden_center -> descriptive; names_wide_jobs_narrow and
names_narrow_jobs_wide -> Element comparison; names_changed_jobs_held -> future
registered migration hypothesis.

ELEMENTS THAT REMAIN DESCRIPTIVE:
Breadth and Toolkit.

CANDIDATE FAMILY NAME:
NONE.
```

### Final family contract

```text
FAMILY_ID: pool_shape (historical root only)
DISPLAY_NAME: Breadth + Toolkit
STATUS: DEMOTED_TO_ELEMENTS

PLAYER_FACING_QUESTION:
How wide is your hero pool, and how wide is the mapped toolkit beneath it?

BEHAVIORAL_CONSTRUCT:
Two descriptive distributions: observed hero choice and editorially mapped
hero functions.

ONE-SENTENCE CLAIM TYPE:
No Finding claim; show the two Element estimates side by side.

IN_SCOPE MEASUREMENTS:
Effective hero count, concentration/top shares, effective mapped-job count,
taxonomy coverage, taxonomy sensitivity.

OUT_OF_SCOPE MEASUREMENTS:
Chronological migration, actual role, outcome, intent, mastery, transfer, and
causal explanations.

STRUCTURAL ELIGIBILITY CONCEPT:
Each Element keeps its own match and coverage gate; there is no shared family
eligibility gate.

EVIDENCE NEEDED:
Element estimates, denominators, intervals/status, taxonomy provenance, and
limitations.

SUPPORTING SIGNALS:
Stable core, HHI, job redundancy, top shares, and Hero Portfolio evidence.

COMPETING EXPLANATIONS:
Patch/hero availability, taxonomy coarsening, actual role choice, draft, and
history-window composition.

FORBIDDEN INTERPRETATIONS:
Role truth, flexibility, mastery, comfort, intent, personality, or skill.

DETERMINISTIC LABELS ALLOWED:
Descriptive Breadth/Toolkit juxtaposition only; no semantic outcome or Finding.

DISTINCT HYPOTHESES DEFERRED:
Actual Role Shape, Role Migration, hero lifecycle, and annual identity eras.

ELEMENT RELATIONSHIP:
Breadth and Toolkit remain separate first-class Elements.

STRATZ/V7 RELATIONSHIP:
Real role/position data could support a future Role Shape or Role Migration
family; it should not retrofit the V6 taxonomy proxy.

NEXT STATISTICAL QUESTION:
None for Pool as a Finding; any future Role Shape or Migration hypothesis must
be separately registered in a later lineage.
```

## Combat decomposition

### Candidate questions

| candidate claim | player question | raw evidence | construct | Finding? | recommendation |
| --- | --- | --- | --- | --- | --- |
| Involvement holds / exposure moves | Does one annual Element move while another stays typical? | Two absolute annual estimates | Element-level contrast plus equivalence | NO | Retire old branch; it does not measure co-movement. |
| Exposure holds / involvement moves | Same inverse annual-zone question | Two absolute annual estimates | Element-level contrast plus equivalence | NO | Retire old branch. |
| Presence–Exposure Link | When scoreboard involvement rises, what happens to death exposure? | Paired context-adjusted per-match rates with session IDs | Within-player signed co-movement | YES | Retain as the sole renamed Combat replacement. |
| Same expression / different results | Do results differ while expression is similar? | Expression vector plus result distribution | Equivalence plus outcome difference | NOT NOW | Future registered hypothesis only; high outcome/confounder risk. |
| Different expression / same results | Does expression differ while results are similar? | Expression vector plus result distribution | Outcome equivalence plus expression difference | NOT NOW | Future registered hypothesis only. |
| Finishing/conversion | How much credited action becomes kills? | Kill share among kills+assists | Stable descriptive dimension | NO | Finishing Element. |
| Exposure style | Is the absolute profile more present or exposed? | Annual involvement/death-exposure estimates | Descriptive two-Element profile | NO | Elements only. |
| Localized variance | Is one context unusually volatile? | Conditional variance decomposition | Context localization | NO | Backstage supporting signal. |

The two old “holds/moves” branches are not directions of a relationship: they
compare annual levels to practical bands. The replacement instead pairs both
measurements within matches/sessions and asks one signed association question.
Outcome, finishing, and variance are excluded rather than hidden as labels.

### Evidence overlap

Involvement and Death Exposure remain descriptive Elements. The new Finding
adds only their within-player co-movement across covered observations. Transfer
may use the same component measurements but asks whether they change across
hero-distance bands; Session Drift asks whether they change with session
position. Shared measurements are acceptable only because the comparison axes
are different and must be declared in later dependence work.

### Finding vs Element

Absolute involvement, finishing, and death exposure belong to Elements. The
signed relationship between paired adjusted involvement and exposure is
Finding-worthy because neither Element alone can say whether they move
together. A neutral or unsupported relationship is not a Finding. Localized
variance is evidence-only, and result-expression comparisons remain separate
future hypotheses.

### Decision

`RENAME_AND_REDEFINE` as **Presence & Exposure**.

```text
PRIMARY PLAYER-FACING QUESTION:
When your scoreboard involvement rises, what happens to your death exposure?

PRIMARY BEHAVIORAL CLAIM:
Across covered matches, higher involvement tends to coincide with higher or
lower death exposure.

EXACT CONSTRUCTS INCLUDED:
Paired context-adjusted involvement per minute and death exposure per ten
minutes, with session structure and duration normalization.

EXACT CONSTRUCTS EXCLUDED:
Finishing, result/win rate, absolute Element zones, localized variance, hero
transfer, intent, aggression, positioning, death quality, and causality.

SUPPORTING SIGNALS:
The two Element estimates, paired-observation coverage, session distribution,
duration/context audit, and hero/function/role sensitivity.

ALTERNATIVE EXPLANATIONS:
Hero choice, sparse role hints, team tempo, match state, draft/opponents,
duration, and unobserved inside-game events.

DEFERRED CLAIMS:
Expression-versus-result relationships and context-localized variance.

CANDIDATE FAMILY NAME:
Presence & Exposure.
```

### Final family contract

```text
FAMILY_ID: presence_exposure_link
DISPLAY_NAME: Presence & Exposure
STATUS: READY_FOR_FAMILY_INFERENCE_DESIGN

PLAYER_FACING_QUESTION:
When your scoreboard involvement rises, what happens to your death exposure?

BEHAVIORAL_CONSTRUCT:
Within-player signed co-movement of paired context-adjusted involvement and
death-exposure rates across covered matches, respecting sessions.

ONE-SENTENCE CLAIM TYPE:
Higher scoreboard involvement is associated with higher or lower death
exposure in the covered sample.

IN_SCOPE MEASUREMENTS:
Per-match adjusted kills-plus-assists per minute, adjusted deaths per ten
minutes, duration, context-resolution audit, and session membership.

OUT_OF_SCOPE MEASUREMENTS:
Finishing, outcome, absolute annual Element zones, variance localization,
actual fights, intent, aggression, positioning, death quality, and causality.

STRUCTURAL ELIGIBILITY CONCEPT:
Enough paired context-resolved observations, independent sessions, component
variation, and context coverage chosen before association strength is inspected.

EVIDENCE NEEDED:
Paired adjusted measurements, signed relationship estimate and uncertainty,
denominators, sessions, coverage, stability, and context-sensitivity evidence.

SUPPORTING SIGNALS:
Involvement and Death Exposure Elements, duration audit, hero/function/role mix,
and session contribution diagnostics.

COMPETING EXPLANATIONS:
Hero and role choice, team tempo, match state, draft/opponents, duration, and
unobserved inside-game events.

FORBIDDEN INTERPRETATIONS:
Aggression, safety, positioning, good/bad deaths, efficiency, skill, intent,
causality, or a complete combat model.

DETERMINISTIC LABELS ALLOWED:
Positive link and inverse link as directions of the same qualified signed
relationship. Neutral/unsupported is abstention, not an equivalence Finding.

DISTINCT HYPOTHESES DEFERRED:
Expression-versus-result, result-versus-expression, localized variance, and
finishing conversion.

ELEMENT RELATIONSHIP:
Involvement and Death Exposure remain independent descriptive Elements;
Finishing remains separate and is not family evidence.

STRATZ/V7 RELATIONSHIP:
Current V6 inputs are sufficient for a bounded summary-rate association.
STRATZ role, kill-participation, lane, and richer event context would enhance
or eventually replace the proxies, but are not prerequisites for this contract.

NEXT STATISTICAL QUESTION:
Define and validate one signed, session-aware, context-adjusted association
estimand for paired involvement and death exposure, including its null and
known-truth calibration scenarios.
```

### User-value test

Scores use 1–5; confounder risk and complexity use 5 as highest.

| candidate | user value | Dota legibility | Wrapped value | coherence | distinct from Elements | confounder risk | complexity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Presence–Exposure Link | 5 | 5 | 5 | 4 | 4 | 4 | 3 |
| Expression vs Result | 3 | 4 | 3 | 2 | 3 | 5 | 4 |
| Finishing/Conversion | 3 | 5 | 3 | 4 | 1 | 4 | 2 |
| Exposure Style | 3 | 5 | 3 | 3 | 1 | 4 | 1 |
| Localized Variance | 2 | 2 | 2 | 3 | 3 | 5 | 5 |

Presence–Exposure is memorable, specific to observable play, and cannot be
shown by either Element alone. A false positive would be misleading, so the
next phase must validate context and session dependence before publication.
All other candidates are communicated better as Elements/supporting evidence
or require separately registered future hypotheses.

## Cross-family coherence

### Pool/replacement

No Finding root. Breadth and Toolkit ask: **How wide are the observed hero and
mapped-toolkit distributions?**

### Transfer

**What survives when the hero changes from core to supported stretch choices?**

### Post-Loss

**How does the next same-session hero choice move after supported result states?**

### Combat/replacement

**When scoreboard involvement rises, what happens to death exposure?**

### Session Drift

**Within eligible completed sessions, what changes from early to late?**

No two retained Findings use the same comparison axis: hero-distance,
result-state transition, paired expression co-movement, and session chronology
are distinct. Transfer and Presence & Exposure share involvement/exposure
measurements but not the estimand. Outcome remains a Transfer component and a
Post-Loss state descriptor; it is explicitly excluded from Presence & Exposure.
The major missing dimension is actual role/lane/objective behavior, which waits
for richer V7 inputs rather than being inferred from sparse hints.

## Do we still need five families?

**NO — recommend 4 inferential families.** Pool belongs in Elements/Hero
Portfolio. The retained conceptual roots are Transfer, Post-Loss Response,
Presence & Exposure, and Session Drift. The product may still show at most
three qualified Findings; this task does not alter multiplicity rules.

## STRATZ/V7 implications

| contract | current V6 inputs sufficient? | STRATZ would enhance? | STRATZ would replace? | wait for V7? |
| --- | --- | --- | --- | --- |
| Breadth + Toolkit description | YES, with taxonomy wording | YES | Actual Role Shape would replace the role interpretation, not the descriptive hero taxonomy | NO for Elements; YES for a Role Shape Finding |
| Presence & Exposure | YES for bounded summary-rate association | YES: role, kill participation, lane, richer events | MAYBE for eventual construct precision | NO, provided V6 inference validates |

V6 taxonomy labels remain editorial hero-function descriptors. They are not
promoted to actual role evidence. Role Shape, Role/Hero Transfer Split, and
Role Migration remain future registered V7 candidates.

## Deferred hypotheses

| hypothesis | disposition | reason |
| --- | --- | --- |
| Actual Role Shape | `FUTURE_REGISTERED_HYPOTHESIS` | Needs real role/position evidence. |
| Role Migration | `FUTURE_REGISTERED_HYPOTHESIS` | Temporal role change is distinct from static Pool description. |
| Annual hero/toolkit migration | `FUTURE_REGISTERED_HYPOTHESIS` | Duplicates current Evolution descriptively; inference needs its own temporal contract. |
| Hero lifecycle / identity eras | SHADOW_ONLY | Left truncation and chapter-selection risks remain. |
| Same expression / different results | `FUTURE_REGISTERED_HYPOTHESIS` | Distinct outcome-equivalence question with high confounding risk. |
| Different expression / same results | `FUTURE_REGISTERED_HYPOTHESIS` | Distinct inverse composite question. |
| Localized combat variance | SUPPORTING_ONLY | Too abstract and context-confounded for onstage copy. |
| Finishing conversion relationship | ELEMENT_ONLY | Finishing already owns the supported descriptive construct. |

## Recommended next statistical task

Freeze the four-family contracts, then define exact estimands/nulls/statistics
for Transfer, Post-Loss Response, Presence & Exposure, and Session Drift and
run family-specific known-truth null validation. Pool receives no family test.

## What must NOT change yet

- production family IDs, semantic outcomes, copy, Elements, or report contracts;
- current V6.1 estimators, inference, thresholds, qualification, or publication;
- frozen V6.1 artifacts or analytical source binding;
- tuning/holdout membership or the revealed holdout;
- multiplicity rules or the three-Finding display cap; and
- provider collection, deployment, flags, database, Redis, or infrastructure.

## Files created

Tracked:

- `docs/evidence/free-dna-v6.1-pool-combat-family-redesign-2026-08-27.md`
- updated `docs/prompts/v61-findings-recovery-implementation.md`

Local-only under `.local/diagnostics/v61-pool-combat-redesign/`:

- `pool_candidate_matrix.csv`
- `combat_candidate_matrix.csv`
- `pool_family_contract.json`
- `combat_family_contract.json`
- `cross_family_coherence.json`
- `deferred_hypotheses.json`
- `element_vs_finding_map.csv`
- `aggregate_summary.json`

## Integrity verification

- external collection calls: **0**;
- holdout reruns: **0**;
- simulations: **0**;
- thresholds calibrated: **0**;
- frozen artifacts changed: **no**;
- production changed: **no**;
- deployment or merge: **none**.
