# Production Safety

Read the [root agent operating contract](../../AGENTS.md) first. This manual
is for future Luna-, Sol-, and Codex-style coding agents working on a live
production product.

## System context

Dota Report Card has a live path:

    Vercel / Next.js frontend
            ↓
    Railway / FastAPI API
            ├── PostgreSQL
            ├── Redis
            └── Celery worker

The frontend reads report data from the API. The API assembles reports from
analytical output and persists user reports. A report page can therefore read
data produced by a previous implementation long after the implementation that
created it has changed.

The current branch, local environment, or latest generated fixture is not a
substitute for production state.

## Why production state matters

Persisted reports are production data and historical API contracts. A current
TypeScript type or a newly generated payload describes what a current producer
expects; it does not prove that every stored report contains every field.

A renderer can fail even when:

- a local build passes;
- lint and TypeScript pass;
- unit tests pass;
- synthetic fixtures pass; and
- a newly generated report renders.

The missing test is often the old persisted payload. A presentation change
must consume that payload safely, or explicitly stop the release until a
versioned compatibility decision is made. Do not solve a renderer mismatch by
silently changing analytical semantics or rewriting persisted reports.

## Task-scope boundaries

Classify the task before editing:

| Task type | Default scope |
| --- | --- |
| PRESENTATION / UI | Renderer, styles, interaction, and copy only. |
| FRONTEND APPLICATION | Web application behavior and its existing API inputs. |
| BACKEND | API, report assembly, storage, or worker behavior. |
| ANALYTICAL | Estimators, thresholds, significance, qualification, or artifacts. |
| DATABASE | Schema, migrations, persistence, or data repair. |
| INFRASTRUCTURE | Runtime, deployment, environments, or service configuration. |
| RELEASE / DEPLOYMENT | Preview, merge, production, or release metadata. |
| DOCUMENTATION | Repository instructions and explanatory material only. |

UI/presentation authorization does not authorize backend, analytical, database,
infrastructure, or deployment work. If a boundary must be crossed, STOP and
report the layer, reason, in-scope alternative, and compatibility risk.

## Safe feature-branch workflow

Use this sequence for code or report-renderer work:

1. Read the root contract and the applicable directory and detail manuals.
2. Record the starting state with:

       git status --short --branch
       git rev-parse HEAD

3. Classify the task and state whether the public report contract or
   analytical semantics may change.
4. Work on a dedicated feature branch. Keep unrelated user changes intact.
5. Inspect all callers and consumers before changing a shared report boundary.
6. For report UI work, test current and historical persisted-report shapes
   before considering a producer change.
7. Run only the checks required by the task classification. Use the repository's
   existing checks such as make lint, make typecheck, make test,
   make test-contract, make test-e2e, and make docs-check where applicable.
8. Inspect scope before completion:

       git diff --name-only <task-base>...HEAD

9. For a major report UI change, deploy the branch to Vercel Preview and smoke
   test an existing persisted report.
10. Obtain owner review before merge or production release.

The agent must return the validated commit and wait when deployment was not
explicitly requested.

## Why Vercel Preview comes before production

Preview tests the assembled application, environment wiring, hydration, and
browser behavior without changing the production release. A local test can
miss deployment configuration, server-rendering differences, or the actual
API response shape. An existing persisted report exercises the compatibility
case that a newly generated fixture cannot prove.

The Preview gate is not permission to deploy production. It is evidence for
review. Production still requires explicit release authorization.

For a material report renderer change, Preview smoke must include:

- an existing persisted report;
- first-to-last and backward traversal;
- Next, Back, keyboard navigation, Evidence, Methodology, Share, End, and
  Read Again;
- 375px mobile and desktop;
- reduced motion;
- horizontal overflow checks; and
- browser pageerror, unexpected console error, and hydration error monitoring.

HTTP 200 is not a UX success criterion.

## Implementation permission is not deployment permission

Writing code, committing code, and deploying code are separate permissions.
Unless the user explicitly requests the release action, do not:

- merge main;
- deploy Vercel production;
- deploy Railway;
- alter production environment variables;
- toggle production flags; or
- change release metadata.

Do not infer permission from a task's urgency, from a green local check, or
from the fact that the branch is ready to merge.

## Rollback and forward-fix principles

Use the smallest owner-approved release action that restores a valid product:

- Roll back the application when a recent release caused the regression and
  the prior release remains a valid producer/consumer pair.
- Forward-fix the renderer when the defect is an incompatibility with valid
  historical reports and the fix can degrade or omit missing presentation
  material without changing persisted analytical meaning.
- Fix the producer only when a public contract or analytical release explicitly
  authorizes it and all consumers and historical reports have been audited.
- Never rewrite persisted reports, regenerate analytical artifacts, or make
  destructive production data edits merely to make a new renderer pass.

The coding agent may prepare a rollback or forward-fix change, but must not
execute a production rollback or forward deployment without explicit
authorization. If the safe direction is uncertain, STOP.

## Production evidence and release identity

Never fabricate production evidence. Do not claim that a Preview smoke test,
production report read, deployment, OpenDota call count, release SHA, or
environment check happened unless it actually happened and can be reported.

Do not assume the deployed code SHA is the local HEAD, the branch tip, the
commit being reviewed, or the SHA mentioned in a task. Verify deployment
metadata through an authorized read path.

Keep these identities separate:

- deployed code SHA: the code revision running in a service;
- analytical source SHA: the source revision bound to an analytical release;
- frozen artifact bundle digest: the digest of the analytical artifacts used
  by that release.

A code-only change normally changes only the deployed code SHA. It does not
automatically create a new analytical source SHA or frozen artifact bundle.
See [analytical release invariants](analytical-release-invariants.md).

## Environment variable caution

Production environment variables can select API endpoints, storage backends,
feature flags, analytical generations, release metadata, and credentials.
Never edit, rotate, expose, or “temporarily” override a production variable
without explicit authorization and an owner-approved release plan.

Do not commit secrets, access tokens, private report values, or local
environment files. A local value is not evidence of the production value.

## OpenDota cost protection

Presentation validation must use stored reports, sanitized fixtures, recorded
responses, persisted data, and existing evidence. Do not call OpenDota solely
to check:

- UI layout;
- story traversal;
- responsive behavior;
- presentation compatibility;
- release wiring; or
- a Vercel Preview renderer.

Do not regenerate a report if an existing persisted report can test the same
behavior. Report generation and analytical validation are separate operations.

## Incident pattern to avoid

UI task modifies server projection → new fixtures reflect new projection →
old persisted reports are never tested → production renderer breaks.

The safe response is to preserve scope, test a production-shaped historical
payload, and either degrade the presentation or stop for an explicit contract
decision. Do not blame a particular agent or use private report IDs in the
diagnosis.

## References

- [Persisted report compatibility](persisted-report-compatibility.md)
- [Testing and release gates](testing-and-release-gates.md)
- [Analytical release invariants](analytical-release-invariants.md)
