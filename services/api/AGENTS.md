Read /AGENTS.md first. These instructions extend the root rules for services/api.

# API and Backend Agent Rules

These rules apply to FastAPI routes, report assembly, public schemas,
analytical services, storage, workers, and backend release work.

Before designing or changing a Finding, read the repository's
[analytical learnings and gotchas](../../docs/agent/analytical-learnings-and-gotchas.md).
V7 work must remain STRATZ-native and must not inherit V6/V6.1 analytical
meaning without a new, explicitly versioned release decision.

## Classify every report assembly change

Every report assembly change MUST classify itself as exactly one of:

| Category | Required treatment |
| --- | --- |
| ANALYTICAL SEMANTIC CHANGE | Requires explicit analytical-release authorization. |
| PUBLIC CONTRACT CHANGE | Requires backward compatibility analysis and a consumer audit. |
| PRESENTATION-ONLY ADDITIVE PROJECTION | Must preserve existing analytical fields and old persisted report readability. |
| INTERNAL IMPLEMENTATION CHANGE | Must prove public output semantics remain stable. |

The classification belongs in the change description and completion report.
“Presentation-only” does not mean “safe by default”; it still changes a
public report shape if the projection is persisted or consumed by the web app.

## Scope and analytical meaning

- A frontend UI request does not authorize an API change.
- Never overwrite persisted analytical meaning for presentation convenience.
- Preserve existing analytical fields when adding presentation-only data.
- Do not move thresholds, estimators, significance logic, qualification,
  publication, identity, or cohort decisions into a presentation projection.
- A presentation change MUST NOT require report regeneration.
- If the requested behavior needs new analytical output, STOP and request
  explicit analytical-release authorization.

The public report contract is what persisted reports and frontend consumers can
actually read, not only what the current Pydantic or TypeScript models describe.
When an old payload lacks an additive presentation-only field, keep it readable
and let the frontend omit the dependent presentation.

## Privacy and protected identifiers

Never expose private identifiers through public report projections. Exact match
IDs, session IDs, account or Steam IDs, access tokens, and protected cohort
references must remain protected. Public deep handoffs must use the repository's
approved opaque reference form; do not substitute raw database or user
identifiers for convenience.

Sanitized production-shaped fixtures must preserve structural absence, nulls,
nested objects, and array shapes without preserving private values.

## Required validation

A report projection change requires relevant backend tests and contract tests,
relevant presentation tests where applicable, and consideration of compatibility
with the old frontend and persisted reports. At minimum, inspect:

- the public schema and version routing;
- report assembly and persistence paths;
- current and historical frontend consumers;
- relevant contract or presentation tests; and
- protected identifier handling.

Do not treat a newly generated report as proof that an old persisted report is
readable. Do not use a holdout rerun or recalibration as UI validation.

## Frozen V6.1 boundary

During UI or presentation work, frozen analytical artifacts and analytical
source binding cannot change. No retraining, recalibration, holdout rerun,
threshold change, estimator change, significance change, qualification change,
publication change, identity qualification change, or artifact regeneration is
allowed without explicit analytical-release authorization.

The current V6.1 analytical source SHA and frozen artifact bundle digest are
recorded in [analytical release invariants](../../docs/agent/analytical-release-invariants.md).
A deployed code SHA is a separate identity and must not be substituted for
either reference.

## Deployment

Implementation permission is not deployment permission. Unless explicitly
requested, do not merge main, deploy Vercel production, deploy Railway, modify
production environment variables, toggle production flags, or change release
metadata. Return a validated commit and wait.

See [production safety](../../docs/agent/production-safety.md) and
[testing and release gates](../../docs/agent/testing-and-release-gates.md).
