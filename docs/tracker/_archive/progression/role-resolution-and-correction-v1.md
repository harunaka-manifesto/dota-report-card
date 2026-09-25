> **Superseded.** Current rules are in [App Foundation](../../app_foundation/SSOT.md); this document is historical evidence only.

# Role Resolution & Correction V1

Status: **SUPERSEDED**
Scope: Role Resolution & Correction for V1 progression
Audience: Product, design, backend, mobile, QA, and coding agents

## 1. Purpose

This document defines how a retained Dota match receives its canonical
`effective_role`, how confidence affects user prompting, how explicit user
role assertions take precedence, and how a correction rebuilds role-dependent
progression.

This is a product contract. It does not prescribe implementation architecture,
storage schema, classifier calibration, or metric formulas.

The [Role Metrics & Personal Baselines V1](role-metrics-and-baselines-v1.md)
SSOT defines the role-specific metric and baseline consequences. This document
defines which role a match belongs to and how that membership can change.

## 2. Scope

In scope:

- the four V1 progression roles;
- classifier-first role resolution;
- product-level confidence semantics;
- low-confidence confirmation/correction prompting;
- persistent role editing for retained matches;
- user-assertion precedence;
- deterministic correction recalculation;
- role provenance; and
- the boundary between role classification and Match Lifecycle failure.

The role contract applies to all retained matches for which the necessary
underlying data remains available. It does not create a separate role system
for old matches, high-confidence matches, or low-confidence matches.

## 3. Canonical terminology

| Term | Meaning |
|---|---|
| `classifier_detected_role` | The classifier's best V1 role for a successfully classified match. |
| `classifier_confidence` | The product-level confidence bucket stored with the detected role: high or low. |
| `latest_user_role_assertion` | The newest explicit user confirmation or correction for the match. A confirmation of the suggested role is still an assertion. |
| `effective_role` | The single role used by progression for the match. |
| Retained match | A match whose required underlying data is still retained well enough for the applicable product actions. |
| Structurally unprocessable match | A match for which role classification cannot meaningfully run because required identity or classification inputs are invalid or unavailable. |
| Role provenance | The retained facts needed to distinguish classifier output, confidence, relevant classifier metadata, user assertion, and current effective role. |

## 4. V1 role set

Every successfully classified V1 match resolves to exactly one of:

- Carry
- Mid
- Offlane
- Support

Position 4 and Position 5 normalize to the single `Support` progression role.

The following are not progression roles and must not be created:

- Unknown;
- Unresolved;
- Flex;
- Roamer;
- Position 4; or
- Position 5.

## 5. Effective-role resolution contract

Role resolution is classifier-first:

1. A successfully classified match receives the classifier's best role
   immediately.
2. That role is used to process role-dependent progression without waiting
   for user confirmation.
3. With no user assertion, `effective_role` equals the classifier's detected
   role.
4. With a user assertion, the latest assertion is authoritative.
5. A low-confidence result is still a real role and is used immediately; it is
   not held in an unresolved state.

The classifier answers:

> What role did this player actually play?

It does not answer whether the player performed well. Role classification must
not use win/loss, KDA, performance quality, match outcome, or downstream
progression score as role evidence.

## 6. Classifier evidence hierarchy

The classifier scores exactly Carry, Mid, Offlane, and Support. Evidence is
behavior-first and hero identity is never the primary role signal.

| Priority | Evidence | Contract |
|---|---|---|
| Primary | Lane and early-map position | Early lane/map location is a strong signal. Solo-mid behavior supports Mid; safe-lane/offlane context helps establish core/support pairing. Roaming, swaps, unusual lanes, and unclear position should reduce confidence rather than force false certainty. |
| Primary | Farm priority | Relative Last Hits around minute 10, relative Net Worth around minute 10, and resource priority relative to teammates—especially lane partners—help distinguish farming cores from enabling players. |
| Primary | Lane relationship | Solo versus paired lane, lane partner, and core-versus-enabler behavior within a duo are role evidence. |
| Supporting | Support behavior | Vision activity, camps stacked, support consumables, and other validated enabling actions strengthen Support. They must not independently override strong contradictory lane plus farm evidence. |
| Weak | Hero identity | Hero identity may be a weak prior or tiebreaker only. It must never be the primary reason for assigning a role. |

Unusual hero/role combinations are valid when behavior supports them. For
example, Phantom Assassin may be Support and Chen may be Carry; a traditionally
support hero may be Mid or Offlane.

## 7. Confidence semantics

Confidence is stored with the detected role and has product-level meaning only:

- **High confidence:** primary evidence is sufficiently available and broadly
  agrees.
- **Low confidence:** important evidence conflicts, is missing, is sparse, or
  leaves multiple roles similarly plausible.

Low confidence does not mean that no role exists. If classification can run,
the classifier returns its best role immediately.

This SSOT does not define confidence percentages, scoring weights, numeric
thresholds, or calibration methodology. Those belong to classifier
implementation, calibration, and versioning contracts.

## 8. Low-confidence prompt behavior

The application proactively asks the player to confirm or correct a role only
when classifier confidence is low.

- The prompt is corrective, not a prerequisite for finalization.
- The match has already processed with the classifier role before the prompt
  appears.
- Role-dependent progression may already reflect that role.
- High-confidence matches receive no routine proactive confirmation prompt.
- The low-confidence prompt is a shortcut into the same underlying correction
  flow exposed by Edit Role; it is not a second correction system.

If a user has already handled the role, the prompt must not supersede that
later user handling.

## 9. User assertion precedence

The canonical precedence is:

```text
latest_user_role_assertion > classifier_output
```

This applies equally when the user confirms the classifier's suggestion and
when the user selects a different role. Therefore:

- a user confirmation of Offlane is authoritative even if the classifier also
  detected Offlane;
- a later correction to Carry makes Carry authoritative; and
- a later assertion replaces the prior assertion.

Classifier reruns may update the stored detected role, confidence, and relevant
classifier/version metadata for QA, calibration, and error analysis. A rerun
must never overwrite an existing user-asserted `effective_role`.

When no user assertion exists, classifier output remains the source of
`effective_role` under the normal precedence rule. If a rerun changes that
role, the changed effective role follows the correction recalculation contract.

## 10. Persistent correction access

Every retained match exposes a persistent **Edit Role** action on Match Detail.
This applies to:

- low-confidence matches;
- high-confidence matches;
- old retained matches; and
- recently played matches.

Correction availability follows retained match data. It is not limited to the
latest match, the last N matches, low-confidence matches, or an arbitrary
recent time window.

The Edit Role action accepts only the four V1 progression roles. A
low-confidence confirmation prompt enters this same action and contract.

## 11. Correction recalculation contract

Changing `effective_role` changes which isolated role progression track owns
the match. The system must rebuild the affected derived state; changing only a
displayed role label is insufficient.

Conceptually, a rebuild must:

1. remove applicable observations from the old role history;
2. re-evaluate the match using the corrected role's metric set;
3. add valid observations to the corrected role history;
4. recalculate affected role baselines;
5. recalculate affected Personal Bests and downstream role-specific
   progression; and
6. leave unrelated role histories and unrelated matches unchanged.

The rebuild is deterministic, reproducible, and idempotent. Rebuilding the
same corrected match set twice produces the same result.

The existing progression metric and baseline contract determines the exact
metric observations and chronology used by the rebuild. This document does
not redesign that system.

### Missing corrected-role telemetry

A correction changes the interpretation of available telemetry; it does not
invent telemetry.

If a metric required by the corrected role cannot be calculated from retained
match data:

- that metric is N/A;
- no value is fabricated;
- no other metric is substituted; and
- missing data is not converted to zero.

A legitimate measured zero remains zero.

## 12. Classification failure boundary

Classification may fail only when the match is structurally unprocessable—for
example, because player identity is missing or invalid, required minimum role
classification inputs are unavailable, or malformed data prevents the
classifier from running meaningfully.

Such a match is a **Match Lifecycle** failure. Role Resolution & Correction
must identify that classification did not successfully complete and defer the
failure to the Match Lifecycle contract.

It must not create an Unknown role, an Unresolved role, or a placeholder
progression role. This document does not expand Match Lifecycle rules.

## 13. Role provenance requirements

Retain enough provenance to distinguish, at minimum:

- the classifier-detected role;
- classifier confidence;
- classifier/version metadata where relevant;
- the latest user role assertion, if any; and
- the current effective role.

The original classifier output must remain available after a user correction
for QA, classifier calibration, error analysis, and future classifier
improvement. A correction must not erase what the classifier originally
predicted.

## 14. State and precedence table

| Situation | `effective_role` | Prompt | Authority and progression consequence |
|---|---|---|---|
| High-confidence result, no user assertion | Classifier result immediately | No proactive confirmation | Classifier output drives processing. |
| Low-confidence result, no user assertion | Classifier result immediately | Ask user to confirm/correct | Processing is already complete enough to use the detected role; prompt is non-blocking. |
| Low-confidence result, user confirms suggested role | Confirmed role | Prompt is handled | User assertion is authoritative, even though the role value is unchanged. |
| User corrects the role | Latest selected role | Prompt is handled | Latest user assertion is authoritative; if the effective role changes, rebuild affected progression. |
| Classifier reruns after user confirmation | User-confirmed role | No classifier rerun may replace the assertion | Classifier metadata may change; effective role and progression must not be overwritten. |
| User corrects the same match again | Newest assertion's role | Use the same Edit Role flow | Newest assertion wins; rebuild again when the effective role changes. |
| Sparse but usable evidence | Best classifier role, with low confidence | Ask user to confirm/correct | No Unknown role; use the best role immediately. |
| Structurally unprocessable match | No role assigned by this feature | No role correction flow from a successful classification | Match Lifecycle owns the failure; no placeholder progression role. |

## 15. Edge-case contract

| Edge case | Required behavior |
|---|---|
| Position 4 versus Position 5 | Both normalize to Support. They never become separate progression roles. |
| Nontraditional hero in an unusual role | Permit the role when lane, farm, and relationship behavior supports it. Hero identity is only a weak prior/tiebreaker. |
| Lane swap or unusual lane behavior | Treat ambiguity or conflict as a reason for low confidence. Do not force certainty from a conventional lane or hero expectation. |
| Weak or missing evidence | If classification remains usable, return the best role with low confidence. If it cannot run meaningfully, defer to Match Lifecycle. Never create Unknown or Unresolved. |
| Classifier disagreement after rerun | Without a user assertion, the current classifier output remains the role source and any effective-role change follows deterministic rebuild. With a user assertion, retain the user role and update classifier metadata only. |
| Repeated user corrections | The newest assertion wins. Every effective-role change applies the same deterministic, idempotent rebuild contract. |
| Old retained match correction | Edit Role remains available while required underlying data is retained; age alone is not a restriction. |
| Corrected role lacks required metric telemetry | Mark only that metric N/A; do not fabricate, substitute, or coerce to zero. |
| Unrelated histories and matches | Do not alter them. Rebuild only the affected role-dependent state and downstream records. |

## 16. Hard invariants

- V1 has exactly four progression roles: Carry, Mid, Offlane, and Support.
- Position 4 and Position 5 share Support.
- Every successfully classified match has exactly one classifier-detected role.
- A successful classification never produces Unknown, Unresolved, Flex,
  Roamer, Position 4, or Position 5.
- Classifier-first processing does not wait for user confirmation.
- Low confidence changes prompting, not whether a role exists.
- High-confidence matches receive no routine proactive confirmation prompt.
- The latest explicit user assertion outranks classifier output.
- A classifier rerun never overwrites a user-asserted effective role.
- Every retained match has the same persistent Edit Role contract.
- Correction availability follows retained data, not an arbitrary age or
  recency window.
- A changed effective role rebuilds affected role histories, baselines,
  Personal Bests, and downstream role-specific progression deterministically.
- Rebuilding the same corrected match set is idempotent.
- Correction never invents telemetry; N/A remains N/A and a measured zero
  remains zero.
- Original classifier provenance survives user correction.
- Structurally unprocessable matches defer to Match Lifecycle and create no
  placeholder role.
- Role classification does not use outcome, KDA, performance quality, or
  progression score as evidence.
- Unrelated role histories and unrelated matches remain unchanged.

## 17. Explicitly out of scope

This SSOT does not define:

- UI layout, visual styling, or copy beyond the role-confirmation behavior;
- backend architecture, API shape, database schema, or event model;
- classifier scoring weights, percentages, thresholds, calibration, or model
  training;
- metric definitions, formulas, eligibility windows, or baseline statistics;
- a redesign of role-specific progression or Personal Best semantics;
- Match Lifecycle failure rules beyond the classification boundary above;
- additional progression roles or a flex-role system; or
- analytical outcomes, quality judgments, or causal claims about performance.

## 18. Acceptance criteria / testable contract

An implementation satisfies this SSOT only if tests demonstrate that:

1. The only successful V1 role outputs are Carry, Mid, Offlane, and Support;
   Position 4 and Position 5 both resolve to Support.
2. A high-confidence classification immediately processes progression and does
   not create a proactive confirmation prompt.
3. A low-confidence but usable classification immediately processes with the
   classifier role and surfaces a non-blocking confirmation/correction prompt.
4. Lane/early-map position, farm priority, and lane relationship are treated
   as primary evidence; support behavior is supporting evidence; hero identity
   is never the primary reason for a role.
5. Outcome, KDA, performance quality, match result, and progression score do
   not determine role.
6. Sparse but usable evidence returns a best role with low confidence rather
   than Unknown or Unresolved.
7. A user confirmation is authoritative even when it matches the classifier,
   and a later correction replaces it.
8. Edit Role is available for every retained match regardless of confidence or
   age, subject only to retained underlying data.
9. A changed effective role removes old-role observations, evaluates the
   corrected role's metrics, recalculates affected downstream state, and leaves
   unrelated histories unchanged.
10. Repeating the same rebuild is deterministic and idempotent.
11. Missing corrected-role telemetry produces N/A, never a fabricated value,
    substituted metric, or coerced zero; legitimate zero remains zero.
12. Classifier reruns preserve a user-asserted effective role while retaining
    updated classifier metadata and the original classifier output.
13. A structurally unprocessable match delegates failure to Match Lifecycle and
    creates no placeholder role or progression record.
14. The state table and all edge cases in this document are covered without
    requiring a second correction system.

## 19. Final canonical pseudocode

The following expresses product precedence, not exact implementation
architecture:

```text
if role_classification_cannot_run:
    defer_to_match_lifecycle_failure
else:
    detected_role = classifier.best_role
    detected_confidence = classifier.confidence

    if latest_user_role_assertion exists:
        effective_role = latest_user_role_assertion
    else:
        effective_role = detected_role

    if detected_confidence is low
       and no later user handling has superseded the need:
        surface_role_confirmation_or_correction_prompt
```

When a user assertion or classifier rerun changes `effective_role`, apply the
correction recalculation contract. When classification cannot run, no role is
created by this feature and Match Lifecycle owns the failure.
