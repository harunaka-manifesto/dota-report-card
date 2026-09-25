# Agent Documentation

Start with the [repository agent operating contract](../../AGENTS.md).
It is mandatory before making changes; it wins if a detailed document
accidentally conflicts with it.

Use the detailed manuals by task:

- [Production Safety](production-safety.md) — live architecture, scope
  boundaries, Preview, release identity, deployment permission, rollback, and
  OpenDota cost protection.
- [Persisted Report Compatibility](persisted-report-compatibility.md) —
  historical API contracts, runtime normalization, optional fields,
  production-shaped fixtures, and safe degradation.
- [Testing and Release Gates](testing-and-release-gates.md) — static, unit,
  contract, historical payload, browser, responsive/accessibility, Preview,
  and production gates.
- [Analytical Release Invariants](analytical-release-invariants.md) — the
  V6.1 analytical source SHA, frozen artifact bundle digest, identity
  separation, and the presentation/analytical boundary.
- [Analytical Learnings and Gotchas](analytical-learnings-and-gotchas.md) —
  mandatory statistical, provider, product, and release lessons for V7 work.

Directory extensions apply to their subtree:

- [Frontend rules](../../apps/web/AGENTS.md)
- [API/backend rules](../../services/api/AGENTS.md)
