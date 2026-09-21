# Architecture Decision Records

**Status:** ACTIVE
**Last updated:** 2026-09-20
**Scope:** The log of architecturally significant decisions for Dota Tracker V1, and the rules governing it.

---

## What an ADR is here

A record of one architecturally significant decision: its context, the decision, and what it costs us. ADRs capture **why**. The architecture documents capture **what the system must now do**. Do not put normative system rules only in an ADR, and do not put rationale only in an architecture document.

Format follows the convention already in this repository ([`../../../docs/decisions/`](../../../docs/decisions/)): `NNNN-kebab-title.md`, with `Date`, `Status`, `## Context`, `## Decision`, `## Consequences`.

---

## The log

| # | Decision | Status | Date |
|---|---|---|---|
| [0001](0001-provider-independent-hybrid-ingestion.md) | Provider-independent hybrid ingestion, with OpenDota-first fresh routing | **Accepted** | 2026-09-20 |
| [0002](0002-match-id-as-global-unit-of-work.md) | `match_id` is the global unit of ingestion and enrichment work | **Accepted** | 2026-09-20 |
| [0003](0003-progressive-post-match-readiness.md) | Progressive post-match readiness with a single finalisation point | **Accepted** | 2026-09-20 |
| [0004](0004-entitlement-above-the-data-foundation.md) | Entitlement is applied above the data and analysis foundation | **Accepted** | 2026-09-20 |
| [0005](0005-deterministic-analysis-no-runtime-llm.md) | The post-match analysis pipeline is deterministic; no runtime LLM | **Accepted** | 2026-09-20 |

---

## Rules (normative)

1. **An accepted ADR is immutable.** Its decision is never rewritten. Correcting a typo, a broken link or a factual error *about what was decided* is fine. Changing what was decided is not.
2. **A later contradictory decision supersedes it.** Write a new ADR; mark the old one `Superseded by ADR NNNN`; leave its text intact.
3. **New evidence does not automatically change a decision.** Evidence updates change routing **policy** by default. Changing the architecture requires a new ADR. See [`../README.md`](../README.md) §6.
4. **Not every implementation detail deserves an ADR.** Reserve them for decisions that are architecturally significant: system structure, quality attributes, dependencies and coupling, published contracts, or a construction technique that is expensive to reverse.
5. **Every accepted ADR names the architecture documents it binds**, so a reader can get from *why* to *what* in one hop.
6. **Accepting an ADR obliges a propagation pass** over the feature SSOTs affected ([`../README.md`](../README.md) §4 rule 9).
