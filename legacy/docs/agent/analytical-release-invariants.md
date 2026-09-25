# Analytical Release Invariants

Read the [root agent operating contract](../../AGENTS.md) first. This document
defines the boundary between product/presentation work and an analytical
release.

## Current V6.1 release references

The current V6.1 analytical release references are:

- analytical source SHA:
  f85e88a277ffb365e76dd6eeac6f5009c7bd0165
- frozen artifact bundle digest:
  22206d20b84bf9ee73b93c64177443e1bb585ccdb818c188ac40d9acfcb358f9

These values document the current V6.1 analytical release. They are not
placeholders and must not be modified merely because product code, frontend
copy, or the deployed application advances. Change them only as part of an
explicitly authorized analytical release with its own evidence and review.

## Three identities that must stay separate

| Identity | Meaning | What changes it |
| --- | --- | --- |
| Deployed code SHA | The code revision running in a service or Preview. | A code deployment. |
| Analytical source SHA | The source revision bound to the analytical release. | An authorized analytical-source release. |
| Frozen artifact bundle digest | The digest of the analytical artifact set used by that release. | An authorized artifact bundle change. |

DEPLOYED CODE SHA

is not the same as

ANALYTICAL SOURCE SHA

and neither is the

FROZEN ARTIFACT BUNDLE DIGEST.

A new frontend commit does not imply a new analytical source. A new deployed
code SHA is not evidence that an analytical source or artifact bundle changed.
Do not replace one identity with another in release metadata, reports, or
completion notes.

Do not assume the deployed code SHA is local HEAD, the task base, the branch
tip, or a SHA supplied in a request. Verify deployment metadata through an
authorized read path before reporting it.

## What is frozen during presentation work

For V6.1 presentation or UI work, unless the user explicitly authorizes an
analytical release, DO NOT:

- rerun holdout;
- recalibrate;
- retrain;
- alter thresholds;
- alter estimators;
- alter significance logic;
- alter family qualification;
- alter publication logic;
- alter identity qualification;
- regenerate frozen artifacts; or
- change analytical source binding.

These prohibitions include “temporary” recalculation used only to make a UI
fixture or Preview look complete. A presentation fixture must represent the
report contract being tested; it must not become a new analytical result.

Holdout and recalibration are not UI validation mechanisms. Validate
presentation with stored reports, sanitized fixtures, recorded responses, and
existing evidence.

## What presentation work may change

Presentation work may change:

- layout;
- styles;
- copy that stays within supplied claim contracts;
- navigation;
- progressive disclosure;
- responsive behavior;
- accessibility behavior;
- conditional omission; and
- runtime normalization of payload structure.

It may not change the analytical semantics carried by a report. In particular,
the renderer must not recalculate confidence, significance, cohort membership,
identity qualification, semantic outcomes, or findings because a presentation
field is absent.

Missing presentation-only fields must degrade by omission. If the proposed UI
needs a new analytical field, classify the request as a public contract or
analytical change and STOP until explicit authorization exists.

## Authorized analytical release boundary

An analytical release is a separate change class. It must identify:

1. the intended analytical semantic change;
2. the analytical source SHA;
3. the frozen artifact bundle and its digest;
4. affected public report schema or claim contracts;
5. persisted-report compatibility impact;
6. holdout, calibration, and statistical evidence;
7. consumer and fixture updates; and
8. the authorized release and deployment path.

Do not create this evidence as part of an ordinary UI task. Do not make an
analytical release appear to be a presentation-only additive projection.

## Artifact handling

The frozen artifact bundle is a release input, not a scratch directory. During
presentation work:

- do not edit files under the V6.1 runtime artifact bundle;
- do not regenerate checksums;
- do not refresh a fixture from new analytical output;
- do not commit local or unreviewed artifacts; and
- stop if a requested UI fix appears to need artifact changes.

An artifact digest change must be explained as an authorized analytical
release. A changed digest without corresponding source, evidence, and release
identity is a blocker.

## Persisted reports and release identity

Existing persisted reports retain the analytical semantics and release
references with which they were created. A new renderer must display them
without silently upgrading them to the current analytical release. A new
frontend deployment can read an old report; that is a compatibility test, not
an analytical migration.

Use the [persisted report compatibility](persisted-report-compatibility.md)
manual for missing fields and historical fixtures. Use the repository's
[V6.1 feature graph](../architecture/free-dna-v6.1-feature-graph.md) and
[V6.1 release gates](../qa/free-dna-v6.1-release-gates.md) for product-specific
analytical context.

## Stop conditions

STOP and report the conflict when:

- a UI task would change the analytical source SHA;
- a presentation branch changes the frozen artifact bundle digest;
- a missing field can only be supplied by rerunning analysis;
- a type or fixture update changes analytical meaning;
- deployment metadata is being confused with analytical provenance; or
- release evidence would have to be fabricated.
