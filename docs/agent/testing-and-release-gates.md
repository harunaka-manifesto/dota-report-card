# Testing and Release Gates

Read the [root agent operating contract](../../AGENTS.md) first. This document
defines the gates for frontend, API, report, analytical, and release changes.
The gates are operational requirements; they are not all currently enforced by
CI.

## Gate selection

Classify the change first. Run the smallest complete set of gates that proves
the requested behavior, then record every applicable result. A documentation-
only change does not need product tests, but it does need scope, link, and
consistency checks.

The repository already provides these general checks:

    make lint
    make typecheck
    make test
    make test-contract
    make test-e2e
    make docs-check

Use the relevant existing command rather than inventing a new test harness.
Run the application's build check when the change affects build output. Do
not claim a check passed unless it was actually run.

## Required testing levels

### 1. Static checks

Use the relevant formatter, linter, typecheck, documentation checker, and
change-scope inspection. Static checks catch syntax, imports, types, link
mistakes, and accidental file changes. They do not prove persisted-report
compatibility.

### 2. Unit tests

Test changed logic in isolation, including missing, null, empty, and malformed
optional inputs where the code parses runtime JSON. Unit tests must not replace
an historical payload test for a report renderer.

### 3. Contract tests

For API, report assembly, schema, or projection changes, test the public report
contract and its version behavior. Confirm that existing analytical fields,
private identifier protections, and compatibility behavior remain stable.

### 4. Historical payload compatibility

Every material report UI change must render:

- the newest/current report fixture; and
- at least one sanitized production-shaped persisted report from a previous
  production implementation.

Historical fixtures must preserve missing fields, nulls, nesting, arrays,
optional states, published/suppressed structure, hero portfolio structure,
identity structure, and supporting evidence structure. Sanitize private
identifiers without flattening away the structural case.

Recommended fixture directory:

    apps/web/tests/fixtures/persisted-reports/

Fixtures are additive. Do not overwrite or “refresh” an old fixture when a
contract evolves. Add a new fixture for a new payload shape.

### 5. Browser E2E

For a material report renderer change, run the browser flow against both the
current and historical fixture. Verify:

- first-to-last traversal;
- backward traversal;
- Next;
- Back;
- keyboard navigation;
- Evidence;
- Methodology;
- Share;
- End;
- Read Again;
- browser pageerror detection;
- unexpected console error detection; and
- hydration error detection.

HTTP 200 is not a UX success criterion. A page that loads but fails during
hydration, silently loses navigation, or crashes on an old payload has failed
the gate.

### 6. Responsive and accessibility checks

For the report renderer, verify at minimum:

- 375px mobile;
- desktop;
- reduced motion;
- horizontal overflow;
- focus movement after navigation;
- keyboard access to controls and dialogs; and
- meaningful empty or omitted states.

Conditional story pages must disappear cleanly, and progress indicators and
navigation bounds must recalculate after omission.

### 7. Preview deployment smoke

Major report UI changes require this sequence:

    feature branch
        → automated checks
        → Vercel Preview
        → existing persisted report smoke test
        → owner review

Use an existing persisted report when possible. Do not generate a new report
merely for UI validation, and do not make OpenDota calls solely for layout,
compatibility, or release wiring.

Preview evidence must identify what was tested. Do not infer Preview success
from a local build or an HTTP 200 response.

### 8. Production release

Production release is a separate gate and requires explicit authorization.
Confirm the reviewed commit, deployment target, environment configuration,
release identity, and owner approval through the authorized release process.

Implementation permission does not authorize:

- merging main;
- deploying Vercel production;
- deploying Railway;
- changing production environment variables;
- toggling production flags; or
- changing release metadata.

Do not deploy when the task asks only for implementation or validation.

## Change type and required gates

| CHANGE TYPE | REQUIRED GATES |
| --- | --- |
| Minor CSS-only | lint, typecheck, affected visual smoke |
| Report renderer | all frontend gates + historical payload + Preview using an existing persisted report |
| Backend presentation projection | backend tests + contract tests + old frontend compatibility consideration |
| Analytical change | analytical release process, not covered by normal UI workflow |
| Infrastructure | environment-specific deployment validation |

“All frontend gates” includes the current fixture, production-shaped
historical fixture, browser traversal, responsive/accessibility checks, error
monitoring, and applicable typecheck/lint/build checks.

## Analytical gate boundary

Normal UI workflow does not authorize analytical validation or change. During
presentation work, do not retrain, recalibrate, rerun holdout, alter
thresholds, alter estimators, alter significance logic, change family or
identity qualification, change publication logic, regenerate frozen artifacts,
or change analytical source binding.

If the change needs any of those actions, classify it as ANALYTICAL and STOP
the UI workflow until the analytical release process is explicitly authorized.

## Evidence and completion report

Report the base SHA, new SHA, changed files, compatibility result, production-
shaped fixture result, browser result, typecheck, lint, build, analytical
behavior result, holdout/recalibration status, OpenDota QA call count,
deployment status, and safe-to-merge decision. Use NOT APPLICABLE only when
the gate genuinely does not apply.

Never fabricate a Preview URL, browser result, production smoke result,
deployment SHA, or OpenDota call count.

## Recommended future enforcement

RECOMMENDED FUTURE AUTOMATION — NOT CURRENTLY ENFORCED

Future CI or release tooling could:

- require an explicit full-stack classification when a UI PR touches
  services/api/;
- require a historical compatibility test when a report renderer changes;
- fail a presentation PR that changes a frozen artifact;
- fail when a persisted compatibility fixture is removed; and
- require Preview smoke evidence before a production release.

These are recommendations only. This documentation task does not add CI
enforcement, package scripts, test infrastructure, deployment configuration,
or workflow changes.
