Read /AGENTS.md first. These instructions extend the root rules for apps/web.

# Frontend Agent Rules

These rules apply to Next.js, React, styling, report rendering, browser QA,
and frontend release work.

## Inputs and compatibility

1. Persisted reports are backward-compatible inputs, not disposable fixtures.
2. New report UI MUST work with both the current V6.1 payload and a historical
   persisted V6.1 payload.
3. Presentation-only fields are optional unless a versioned public contract
   guarantees them.
4. Do not trust TypeScript types as runtime validation. API JSON can be older,
   partial, null, or structurally different from the current type.
5. Prefer one runtime normalization / compatibility boundary before story
   composition rather than scattered unsafe assumptions.

The compatibility flow is:

    raw report JSON
        → runtime validation / normalization
        → presentation-safe model
        → story composer
        → renderer

Normalization may repair structure. It MUST NOT fabricate analytical
information. See [persisted report compatibility](../../docs/agent/persisted-report-compatibility.md).

## Scope rules

- Do not modify services/api/ merely to make a renderer easier unless the
  user explicitly authorizes an API change.
- A frontend request does not authorize a backend, analytical, database,
  infrastructure, or deployment change.
- If a renderer appears to require a schema-breaking change, STOP and report
  the required layer, reason, in-scope alternative, and compatibility risk.
- Do not spend OpenDota calls for frontend QA. Use stored reports, fixtures,
  recorded responses, or existing evidence.
- Do not deploy unless explicitly asked.

## Rendering rules

- Conditional story pages MUST disappear cleanly when their required evidence
  is unavailable.
- Progress navigation MUST recalculate after conditional page omission.
- Missing story_band means omit band-specific story UI.
- Missing chronology means omit chronology UI.
- Missing identity slots means omit Signature UI.
- Missing comparison rows means render only the evidence that exists.
- Missing optional copy or supporting evidence means omit that material.
- Never invent findings, confidence, evidence, evidence references, semantic
  outcomes, identity slots, causal explanations, cohort membership, or
  analytical classifications to keep a page populated.

## Required report QA

For a material report renderer change, use:

- one current fixture;
- one sanitized production-shaped historical fixture;
- first-to-last traversal;
- backward traversal;
- Next and Back;
- keyboard navigation;
- Evidence, Methodology, Share, End, and Read Again;
- 375px mobile and desktop;
- reduced motion;
- horizontal overflow checks;
- browser pageerror detection;
- unexpected console error detection; and
- hydration error detection.

Then validate the same behavior in a Vercel Preview using an existing
persisted report when possible. HTTP 200 alone is not a UX success criterion.

Historical fixtures are additive. Do not overwrite an old fixture when the
payload contract evolves. The recommended directory is:

    apps/web/tests/fixtures/persisted-reports/

See [testing and release gates](../../docs/agent/testing-and-release-gates.md)
and [production safety](../../docs/agent/production-safety.md) for the full
release sequence.
